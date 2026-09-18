"""
core/master.py — Мастер-рассказчик.

Получает:
    - CharacterState (состояние персонажа)
    - ParsedCommand (что игрок делает)
    - RollResult (результат броска, опционально)
    - историю последних ходов

Возвращает:
    - художественный текст от Мастера

ВАЖНО: Мастер не выполняет правил. Броски, изменения состояния, инвентарь —
всё это уже сделано Python-ядром. Мастер только озвучивает результат.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from core.analyst import ParsedCommand
from core.config import Config
from core.llm_client import LLMClient
from core.roll_engine import RollResult
from core.state import CharacterState
from core.variants import ensure_action_variants


class MasterError(Exception):
    """Ошибка Мастера."""


# ============================================================
# История ходов
# ============================================================

@dataclass
class Turn:
    """Один ход: что сказал игрок, что ответил Мастер."""
    player: str
    master: str

    def to_dict(self) -> dict:
        return {"player": self.player, "master": self.master}


# ============================================================
# Мастер
# ============================================================

class Master:
    """
    Обёртка над LLM для генерации художественного текста.
    Промт собирается из prompts/master_core.txt + prompts/lore_reference.txt.
    """

    def __init__(
        self,
        config: Config,
        *,
        role: str = "master",
        core_prompt_path: Optional[Path] = None,
        lore_prompt_path: Optional[Path] = None,
        history_limit: int = 6,
    ):
        self.config = config
        self.role = role
        self.history_limit = history_limit

        root = Path(__file__).resolve().parents[1]
        if core_prompt_path is None:
            core_prompt_path = root / "prompts" / "master_core.txt"
        if lore_prompt_path is None:
            lore_prompt_path = root / "prompts" / "lore_reference.txt"

        self.core_prompt_path = Path(core_prompt_path)
        self.lore_prompt_path = Path(lore_prompt_path)

        if not self.core_prompt_path.exists():
            raise MasterError(f"Не найден промт: {self.core_prompt_path}")
        if not self.lore_prompt_path.exists():
            raise MasterError(f"Не найден лор-справочник: {self.lore_prompt_path}")

        core_text = self.core_prompt_path.read_text(encoding="utf-8")
        lore_text = self.lore_prompt_path.read_text(encoding="utf-8")
        self.system_prompt = (
            core_text
            + "\n\n=== СПРАВКА: ТЕРМИНОЛОГИЯ И ИМЕНА ===\n\n"
            + lore_text
        )

        self.model = config.role_model(role)
        self.provider = config.provider(self.model.provider)
        self.api_key = config.provider_key(self.model.provider)
        self.base_url = self.provider.base_url

        retries = config.retries()
        self.llm = LLMClient(
            self._do_request,
            max_retries=retries.get("max_retries", 3),
            base_delay=retries.get("base_delay", 1.0),
            max_delay=retries.get("max_delay", 30.0),
        )

    # ---------- Основной метод ----------

    def narrate(
        self,
        state: CharacterState,
        command: ParsedCommand,
        *,
        roll: Optional[RollResult] = None,
        history: Optional[list[Turn]] = None,
        extra_context: str = "",
    ) -> str:
        """
        Сгенерировать текст хода.

        Аргументы:
            state         — текущее состояние персонажа
            command       — распарсенная команда игрока
            roll          — результат броска (если был)
            history       — последние ходы (для контекста)
            extra_context — дополнительный контекст от системы
        """
        user_message = self._build_user_message(
            state, command, roll, history or [], extra_context
        )

        defaults = self.config.role_defaults()
        response = self.llm.call(
            system_prompt=self.system_prompt,
            user_message=user_message,
            model=self.model.id,
            temperature=defaults.get("temperature", 0.8),
            max_tokens=defaults.get("max_tokens", 1024),
        )

        text = self._extract_text(response).strip()
        if not text:
            raise MasterError("Модель вернула пустой текст")
        # Гарантия блока 'Варианты действий' (flash-модели его теряют).
        text = ensure_action_variants(text)
        return text

    # ---------- Сборка сообщения ----------

    def _build_user_message(
        self,
        state: CharacterState,
        command: ParsedCommand,
        roll: Optional[RollResult],
        history: list[Turn],
        extra_context: str,
    ) -> str:
        parts: list[str] = []

        # 1. Сводка персонажа
        parts.append("=== ЛИСТ ПЕРСОНАЖА ===")
        parts.append(state.get_summary())
        parts.append("")

        # 2. История последних ходов
        if history:
            parts.append("=== ПОСЛЕДНИЕ ХОДЫ ===")
            for turn in history[-self.history_limit:]:
                parts.append(f"Игрок: {turn.player}")
                parts.append(f"Мастер: {turn.master}")
                parts.append("")

        # 3. Действие игрока
        parts.append("=== ХОД ИГРОКА ===")
        parts.append(f"Фраза игрока: {command.raw}")
        parts.append(f"Распознанное действие: {command.action}")
        if command.target:
            parts.append(f"Цель: {command.target}")
        if command.roll_needed and command.skill:
            parts.append(f"Требуется проверка: {command.skill}")
        parts.append("")

        # 4. Результат броска
        if roll is not None:
            parts.append("=== РЕЗУЛЬТАТ БРОСКА (ОТ СИСТЕМЫ) ===")
            parts.append(roll.format_short())
            if roll.crit_success:
                parts.append("Особый статус: КРИТИЧЕСКИЙ УСПЕХ")
            elif roll.crit_fail:
                parts.append("Особый статус: КРИТИЧЕСКИЙ ПРОВАЛ")
            parts.append("")
            parts.append(
                "Твой текст ОБЯЗАН соответствовать результату броска: "
                "успех — заявка удалась, провал — не удалась."
            )
        elif command.roll_needed:
            parts.append("=== ВНИМАНИЕ ===")
            parts.append("Бросок требовался, но система его не передала. "
                         "Опиши сцену нейтрально, без явного успеха/провала.")
        parts.append("")

        # 5. Доп. контекст (RAG, триггеры, события)
        if extra_context:
            parts.append("=== ДОПОЛНИТЕЛЬНЫЙ КОНТЕКСТ ===")
            parts.append(extra_context)
            parts.append("")

        # 6. Запрос
        parts.append("=== ЗАДАЧА ===")
        parts.append(
            "Опиши реакцию мира на действие игрока. "
            "3–5 абзацев, grimdark, сенсорно, с живыми NPC. "
            "В конце — короткий вопрос «Что делаешь?» или его вариант. "
            "НЕ пиши формулы, кубики, [STATE], key=value — только текст."
        )

        return "\n".join(parts)

    # ---------- LLM-запрос ----------

    def _do_request(
        self,
        *,
        system_prompt: str,
        user_message: str,
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> Any:
        try:
            from openai import OpenAI
        except ImportError as e:
            raise MasterError("Не установлен пакет openai: pip install openai") from e

        client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        return client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )

    @staticmethod
    def _extract_text(response: Any) -> str:
        try:
            return response.choices[0].message.content or ""
        except (AttributeError, IndexError) as e:
            raise MasterError(f"Неожиданный формат ответа: {response}") from e
