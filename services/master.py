"""services/master.py — Мастер (ГМ): сцена от LLM."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from core.config import Config
from core.llm_client import LLMClient
from core.llm_factory import make_client

ROOT_DIR = Path(__file__).resolve().parents[1]


class MasterError(Exception):
    """Ошибка Мастера."""


class Master:
    def __init__(self, config: Config, *, role: str = "master",
                 core_prompt: Optional[Path] = None,
                 lore_prompt: Optional[Path] = None):
        self.config = config
        self.role = role

        core_prompt = core_prompt or (ROOT_DIR / "prompts" / "master_core.txt")
        lore_prompt = lore_prompt or (ROOT_DIR / "prompts" / "lore_reference.txt")

        core_text = Path(core_prompt).read_text(encoding="utf-8") if Path(core_prompt).exists() else ""
        lore_text = Path(lore_prompt).read_text(encoding="utf-8") if Path(lore_prompt).exists() else ""
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

    def narrate(self, state: Any, command: Any, *, roll: Any = None,
                history: Optional[list] = None,
                extra_context: str = "") -> str:
        """Собрать сообщение и получить текст сцены."""
        user_message = self._build_message(
            state=state, command=command, roll=roll,
            history=history or [], extra_context=extra_context,
        )
        try:
            response = self.llm.call(
                system_prompt=self.system_prompt,
                user_message=user_message,
                model=self.model.id,
                temperature=0.85,
                max_tokens=700,
            )
            return self._extract_text(response)
        except Exception as e:
            print(f"[master] fallback: {type(e).__name__}: {e}")
            return ("[fallback-мастер] Что-то пошло не так. "
                    "Попробуй переформулировать ход.")

    @staticmethod
    def _build_message(*, state: Any, command: Any, roll: Any,
                       history: list, extra_context: str) -> str:
        parts = []

        # Состояние персонажа
        summary = ""
        if hasattr(state, "get_summary"):
            try:
                summary = state.get_summary()
            except Exception:
                summary = ""
        if summary:
            parts.append(f"=== СОСТОЯНИЕ ПЕРСОНАЖА ===\n{summary}")

        # История
        if history:
            hist_lines = ["=== ПОСЛЕДНИЕ ХОДЫ ==="]
            for t in history[-6:]:
                if hasattr(t, "player_input"):
                    hist_lines.append(f"> {t.player_input}")
                if hasattr(t, "narrative") and t.narrative:
                    hist_lines.append(t.narrative[:400])
            parts.append("\n".join(hist_lines))

        # Действие игрока
        action = getattr(command, "action", "?")
        target = getattr(command, "target", None)
        raw = getattr(command, "raw", "")
        parts.append(f"=== ДЕЙСТВИЕ ИГРОКА ===\nТип: {action}"
                     + (f"\nЦель: {target}" if target else "")
                     + f"\nФраза: {raw!r}")

        # Результат броска
        if roll is not None:
            res = "УСПЕХ" if roll.success else "ПРОВАЛ"
            crit = getattr(roll, "critical", None)
            crit_str = ""
            if crit == "success":
                crit_str = " (критический успех!)"
            elif crit == "fail":
                crit_str = " (критический провал!)"
            parts.append(
                f"=== РЕЗУЛЬТАТ БРОСКА ===\n"
                f"{res}{crit_str}\n"
                f"Бросок: {roll.roll} против {roll.target} "
                f"(сложность {roll.difficulty or '—'})"
            )
        else:
            parts.append("=== БРОСОК ===\nНе требовался.")

        # RAG-контекст
        if extra_context:
            parts.append(extra_context)

        parts.append("=== ЗАДАЧА ===\nОпиши сцену и предложи 2–4 варианта действий.")
        parts.append(
            "=== ИНСТРУКЦИЯ ПО ОПЫТУ (XP) ===\n"
            "Если игрок победил врага в бою (убил, обратил в бегство, "
            "обезвредил), добавь в [STATE] строку:\n"
            "  xp=+10  за мелкого врага\n"
            "  xp=+25  за среднего\n"
            "  xp=+35  за крупного\n"
            "  xp=+50  за великого (демон, лорд Хаоса)\n"
            "В остальных случаях XP НЕ выдавай."
        )
        return "\n\n".join(parts)

    def _do_request(self, *, system_prompt: str, user_message: str,
                    model: str, temperature: float, max_tokens: int) -> Any:
        client = make_client(
            provider_key=self.model.provider,
            api_key=self.api_key,
            base_url=self.base_url,
        )
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
            raise MasterError(f"формат: {response!r}") from e
