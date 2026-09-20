"""services/moderator.py — regex-слой + LLM-слой для спорных случаев.

Принцип: 80–90% фраз проходят без вызова GigaChat.
LLM вызывается только если ни один regex-паттерн не сработал.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from core.config import Config
from core.llm_client import LLMClient
from core.llm_factory import make_client

ROOT_DIR = Path(__file__).resolve().parents[1]


class ModeratorError(Exception):
    """Ошибка модератора."""


# ---------- Regex-слой ----------

META_PATTERNS = [
    r"\bты\s+(бот|нейросеть|нейронка|ии|ai|gpt|чатбот|программа|модель)\b",
    r"\bкакая\s+ты\s+модель\b",
    r"\bкто\s+ты\s+(такой|по\s+модели)\b",
    r"\bпокажи\s+(промт|prompt|инструкции|system)\b",
    r"\bигнорируй\s+(инструкции|правила|вс[её])\b",
    r"\bзабудь\s+(вс[её]|инструкции|правила)\b",
    r"\bрежим\s+разработчика\b",
    r"\bsystem\s+prompt\b",
    r"\bрасскажи\s+свой\s+промт\b",
]

OFFTOPIC_PATTERNS = [
    r"\bанекдот\b",
    r"\bрасскажи\s+(шутку|анекдот|стих)\b",
    r"\bкак\s+дела\b",
    r"\bсколько\s+(времени|сейчас)\b",
    r"\bкакая\s+погода\b",
    r"\bчто\s+нового\b",
    r"\bпривет\s+как\b",
]

ACTION_PATTERNS = [
    r"\b(атак|бью|удар|стрел|выстрел|руб|режу|колю)\w*",
    r"\b(осмотр|огляд|прислуш|принюх|всматрива)\w*",
    r"\b(ищу|искать|обыск|обшар|проверя)\w*",
    r"\b(говор|спрашива|отвеча|зов|обраща|шепч)\w*",
    r"\b(иду|бегу|шага|вход|выход|прыг|подход)\w*",
    r"\b(прячусь|краду|подкрад|скрыва|тихоньк)\w*",
    r"\b(беру|подбира|подним|забира|хвата|выпуск)\w*",
    r"\b(кладу|броса|выброс|отпуска|отдаю)\w*",
    r"\b(надева|снима|экипиру|переодев|натяг)\w*",
    r"\b(жду|отдых|привал|сижу|стою|медлю)\w*",
    r"\b(убежда|уговар|льщу|прошу)\w*",
    r"\b(обман|вру|совра|блефу)\w*",
    r"\b(запугива|угрожа|давлю|пугаю)\w*",
    r"\b(защища|блок|уклон|париру|прикрыва)\w*",
    r"\b(использ|применя|активиру|жму|нажима)\w*",
    r"\b(пси|психич|варп|колду)\w*",
    r"\b(лечу|перевяз|бинту|мажу|капаю)\w*",
]

_META_RE = re.compile("|".join(META_PATTERNS), re.IGNORECASE)
_OFFTOPIC_RE = re.compile("|".join(OFFTOPIC_PATTERNS), re.IGNORECASE)
_ACTION_RE = re.compile("|".join(ACTION_PATTERNS), re.IGNORECASE)


@dataclass
class ModerationResult:
    verdict: str  # ALLOW | RESHAPE | REJECT
    reason: str
    redirect: str = ""
    matched_rule: str = ""


class Moderator:
    def __init__(self, config: Config, *, role: str = "moderator",
                 prompt_path: Optional[Path] = None):
        self.config = config
        self.role = role

        if prompt_path is None:
            prompt_path = ROOT_DIR / "prompts" / "moderator.txt"
        self.prompt_path = Path(prompt_path)
        self.system_prompt = (
            self.prompt_path.read_text(encoding="utf-8")
            if self.prompt_path.exists() else ""
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

    def check(self, player_input: str) -> ModerationResult:
        if not player_input or not player_input.strip():
            return ModerationResult("REJECT", "Пустой ввод", matched_rule="empty")

        text = player_input.strip()

        if _META_RE.search(text):
            return ModerationResult(
                "RESHAPE", "Мета-запрос",
                redirect="Ты моргаешь, и наваждение рассеивается — вокруг снова "
                         "холодный полумрак и шёпот Паутины. Что делаешь?",
                matched_rule="meta",
            )

        if _OFFTOPIC_RE.search(text):
            return ModerationResult(
                "RESHAPE", "Оффтоп",
                redirect="Здесь не до пустых разговоров. Мир ждёт твоего решения.",
                matched_rule="offtopic",
            )

        if _ACTION_RE.search(text):
            return ModerationResult("ALLOW", "Игровое действие", matched_rule="action")

        if len(text.split()) <= 2:
            return ModerationResult("ALLOW", "Короткий ввод", matched_rule="short")

        return self._llm_moderate(text)

    # ---------- LLM ----------

    def _llm_moderate(self, text: str) -> ModerationResult:
        try:
            response = self.llm.call(
                system_prompt=self.system_prompt,
                user_message=text,
                model=self.model.id,
                temperature=0.0,
                max_tokens=200,
            )
            raw = self._extract_text(response)
            data = self._extract_json(raw)
        except Exception as e:
            print(f"[moderator] fallback ALLOW: {type(e).__name__}: {e}")
            return ModerationResult("ALLOW", "LLM недоступен", matched_rule="llm_fail")

        verdict = str(data.get("verdict", "ALLOW")).upper()
        if verdict not in ("ALLOW", "RESHAPE", "REJECT"):
            verdict = "ALLOW"
        return ModerationResult(
            verdict=verdict, reason="LLM",
            redirect=str(data.get("redirect", "") or ""),
            matched_rule="llm",
        )

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
            raise ModeratorError(f"формат: {response!r}") from e

    @staticmethod
    def _extract_json(text: str) -> dict:
        text = text.strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.lower().startswith("json"):
                text = text[4:]
            text = text.strip()
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if not m:
            raise ModeratorError(f"JSON не найден: {text[:120]!r}")
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError as e:
            raise ModeratorError(f"битый JSON: {e}") from e
