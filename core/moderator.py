"""Модератор сцены: regex-слой + LLM-слой.

Задача — защитить сцену от мета-запросов, не ломая игру. По умолчанию
всё, что похоже на действие, пропускается. RESHAPE — вежливый перевод
в сюжет. REJECT — только для пустого ввода или явной атаки на систему.

Стратегия:
    1. Пустой ввод → REJECT.
    2. Regex: явные триггеры мета/выхода из роли → RESHAPE (без LLM).
    3. Regex: явные игровые действия → ALLOW (без LLM).
    4. Всё остальное → LLM-модерация.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Optional

from core.config import Config
from core.llm_client import LLMClient

Verdict = Literal["ALLOW", "RESHAPE", "REJECT"]


class ModeratorError(Exception):
    """Ошибка Модератора."""


@dataclass
class ModerationResult:
    verdict: Verdict
    reason: str = ""
    redirect: str = ""
    matched_rule: str = ""

    @property
    def allowed(self) -> bool:
        return self.verdict == "ALLOW"


# ---------- Regex-правила ----------

# Явные мета-запросы: выйти из роли, спросить про систему.
# ВАЖНО: матчим только если фраза короткая или явно про систему,
# чтобы не сработать на "кто ты по профессии" (это игровой вопрос).
META_PATTERNS = [
    r"\bигнорир\w*\s+(все\s+)?инструкц",
    r"\bзабудь\s+(всё|все)",
    r"\bsystem\s*prompt\b",
    r"\bсистем\w*\s*пром(т|пт)\w*",
    r"\bпокажи\s+(свой\s+)?пром(т|пт)\w*",
    r"\bрежим\s+разработчик\w*",
    r"\bdeveloper\s*mode\b",
    r"\bты\s+(бот\w*|нейросет\w*|ии|ai|модель\w*)\b",
    r"\bкака\w+\s+ты\s+(модель|верси)",
    r"\bвыйди\s+из\s+роли",
    r"\bты\s+не\s+мастер\b",
    r"\bпредставь,?\s+что\s+ты\s+не\b",
    r"<\|.*?\|>",  # спец-токены prompt injection
]

# Явный оффтоп — тоже RESHAPE.
OFFTOPIC_PATTERNS = [
    r"^\s*расскажи\s+анекдот",
    r"^\s*как\s+дела\??\s*$",
    r"^\s*сколько\s+(времени|сейчас)\??\s*$",
    r"^\s*какой\s+сегодня\s+день",
]

# Явные игровые действия — ALLOW без LLM (быстрый путь).
ACTION_PATTERNS = [
    r"\b(атак|удар|стреля|бью|руб|кол)\w*",
    r"\b(осмотр|ищу|обыск|проверя)\w*",
    r"\b(иду|пойду|шага|двига|бегу|подход)\w*",
    r"\b(говор|скаж|спрош|отвеч|крич|шепч)\w*",
    r"\b(беру|кладу|взял|полож|экипир)\w*",
    r"\b(прячусь|скрыва|крад)\w*",
    r"\b(использ|примен|пью|ем|лечу)\w*",
    r"\b(жду|стою|сижу|молчу|думаю)\w*",
]


def _match_any(text: str, patterns: list[str]) -> Optional[str]:
    low = text.lower()
    for p in patterns:
        if re.search(p, low):
            return p
    return None


class Moderator:
    """Regex + LLM модерация. Не меняет состояние, только вердикт."""

    def __init__(
        self,
        config: Config,
        *,
        role: str = "master",  # используем ту же модель, что Master
        prompt_path: Optional[Path] = None,
        use_llm: bool = True,
    ):
        self.config = config
        self.use_llm = use_llm

        if prompt_path is None:
            root = Path(__file__).resolve().parents[1]
            prompt_path = root / "prompts" / "moderator.txt"
        self.prompt_path = Path(prompt_path)
        if not self.prompt_path.exists():
            raise ModeratorError(f"Не найден промт: {self.prompt_path}")
        self.system_prompt = self.prompt_path.read_text(encoding="utf-8")

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

    def check(self, player_input: str) -> ModerationResult:
        if not player_input or not player_input.strip():
            return ModerationResult(
                verdict="REJECT", reason="Пустой ввод", matched_rule="empty"
            )

        text = player_input.strip()

        # 1. Явные мета-запросы → RESHAPE без LLM
        meta = _match_any(text, META_PATTERNS)
        if meta:
            return ModerationResult(
                verdict="RESHAPE",
                reason="Мета-запрос",
                redirect="Ты моргаешь, и наваждение рассеивается — вокруг снова "
                         "холодный полумрак и шёпот Паутины. Что делаешь?",
                matched_rule=f"meta:{meta}",
            )

        # 2. Явный оффтоп → RESHAPE
        off = _match_any(text, OFFTOPIC_PATTERNS)
        if off:
            return ModerationResult(
                verdict="RESHAPE",
                reason="Оффтоп",
                redirect="Здесь не до пустых разговоров. Мир ждёт твоего решения.",
                matched_rule=f"offtopic:{off}",
            )

        # 3. Явное игровое действие → ALLOW без LLM
        act = _match_any(text, ACTION_PATTERNS)
        if act:
            return ModerationResult(
                verdict="ALLOW", reason="Игровое действие", matched_rule=f"action:{act}"
            )

        # 4. Короткая фраза без признаков действия — тоже ALLOW (обычный ввод)
        if len(text.split()) <= 2:
            return ModerationResult(
                verdict="ALLOW", reason="Короткий ввод", matched_rule="short"
            )

        # 5. Спорный случай → LLM
        if not self.use_llm:
            return ModerationResult(
                verdict="ALLOW", reason="LLM отключён", matched_rule="llm_disabled"
            )

        return self._llm_moderate(text)

    # ---------- LLM ----------

    def _llm_moderate(self, text: str) -> ModerationResult:
        response = self.llm.call(
            system_prompt=self.system_prompt,
            user_message=text,
            model=self.model.id,
            temperature=0.0,
            max_tokens=200,
        )
        raw = self._extract_text(response)
        try:
            data = self._extract_json(raw)
        except ModeratorError as e:
            # Модель не дала JSON — считаем ALLOW, не ломаем игру
            return ModerationResult(
                verdict="ALLOW",
                reason=f"JSON не распознан: {e}",
                matched_rule="llm_parse_fail",
            )

        verdict = str(data.get("verdict", "ALLOW")).upper()
        if verdict not in ("ALLOW", "RESHAPE", "REJECT"):
            verdict = "ALLOW"
        return ModerationResult(
            verdict=verdict,  # type: ignore[arg-type]
            reason="LLM",
            redirect=str(data.get("redirect", "") or ""),
            matched_rule="llm",
        )

    def _do_request(
        self,
        *,
        system_prompt: str,
        user_message: str,
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> Any:
        from openai import OpenAI

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
            raise ModeratorError(f"Неожиданный формат ответа: {response}") from e

    @staticmethod
    def _extract_json(text: str) -> dict:
        text = text.strip()
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ModeratorError(f"Нет JSON в ответе: {text!r}")
        try:
            data = json.loads(text[start:end + 1])
        except json.JSONDecodeError as e:
            raise ModeratorError(f"JSON сломан: {e}") from e
        if not isinstance(data, dict):
            raise ModeratorError(f"Ожидался объект, а не {type(data).__name__}")
        return data
