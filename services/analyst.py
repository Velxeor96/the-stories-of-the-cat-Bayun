# PATCH_18 — analyst с расширенными эвристиками
"""services/analyst.py — фраза игрока → строгий JSON (ParsedCommand)."""
from __future__ import annotations

# PATCH_70: refusal detect (analyst)
def _analyst_is_refusal(text: str) -> bool:
    """True, если GigaChat вернул отписку вместо JSON."""
    if not text:
        return False
    low = str(text).lower()
    for m in (
        "не обладает собственным мнением",
        "не транслирует мнение",
        "как и любая языковая модель",
        "иногда генеративные языковые модели",
        "generative language model",
        "обобщением информации",
    ):
        if m.lower() in low:
            return True
    return False
# /PATCH_70

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Optional

from core.config import Config
from core.llm_client import LLMClient
from core.llm_factory import make_client

ROOT_DIR = Path(__file__).resolve().parents[1]


class AnalystError(Exception):
    """Ошибка Аналитика."""


VALID_ACTIONS = {
    "observe", "search", "move",
    "attack_melee", "attack_ranged", "defend",
    "persuade", "deceive", "intimidate",
    "stealth", "use_psychic",
    "take", "drop", "equip",
    "talk", "wait", "other",
}

VALID_SKILLS = {"WS", "BS", "S", "T", "Ag", "Int", "Per", "WP", "Fel"}

VALID_DIFFICULTIES = {
    "Trivial", "Easy", "Routine", "Ordinary", "Challenging",
    "Difficult", "Hard", "Very Hard", "Hellish",
}

_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)

_HEURISTIC_RULES: list[tuple[re.Pattern, dict]] = [
    (re.compile(r"пси|психич|варп[- ]маг|колдую|варп[- ]выстрел|психосил",
                re.IGNORECASE),
     {"action": "use_psychic", "skill": "WP", "roll_needed": True,
      "difficulty": "Ordinary"}),
    (re.compile(r"всматрива|вглядыва|оглядыва|осматрива|осмотр|прислушива|"
                r"слуша|слыш|искать|ищу|ищешь|поиск|замеча|наблюда|высматрива",
                re.IGNORECASE),
     {"action": "observe", "skill": "Per", "roll_needed": True,
      "difficulty": "Ordinary"}),
    (re.compile(r"крадусь|скрыва|подкрадыва|прячусь|незаметно|бесшумно",
                re.IGNORECASE),
     {"action": "stealth", "skill": "Ag", "roll_needed": True,
      "difficulty": "Challenging"}),
    (re.compile(r"стреля|выстрел|палю|жму\s+курок|открываю\s+огонь",
                re.IGNORECASE),
     {"action": "attack_ranged", "skill": "BS", "roll_needed": True,
      "difficulty": "Ordinary"}),
    (re.compile(r"атакую|ударяю|бью|рублю|колю|режу|машу|замахива",
                re.IGNORECASE),
     {"action": "attack_melee", "skill": "WS", "roll_needed": True,
      "difficulty": "Ordinary"}),
    (re.compile(r"защища|блокиру|париру|уворачива", re.IGNORECASE),
     {"action": "defend", "skill": "WS", "roll_needed": True,
      "difficulty": "Ordinary"}),
    (re.compile(r"убежда|уговарива|договарива|склоня|прошу", re.IGNORECASE),
     {"action": "persuade", "skill": "Fel", "roll_needed": True,
      "difficulty": "Ordinary"}),
    (re.compile(r"запугива|угрожа|пуга|страща", re.IGNORECASE),
     {"action": "intimidate", "skill": "S", "roll_needed": True,
      "difficulty": "Ordinary"}),
    (re.compile(r"обманыва|блефу|вру|лгу|лгать|хитрю", re.IGNORECASE),
     {"action": "deceive", "skill": "Fel", "roll_needed": True,
      "difficulty": "Ordinary"}),
]


@dataclass
class ParsedCommand:
    action: str
    target: Optional[str]
    skill: Optional[str]
    roll_needed: bool
    difficulty: str
    raw: str

    def to_dict(self) -> dict:
        return asdict(self)

    def is_valid(self) -> tuple:
        if self.action not in VALID_ACTIONS:
            return False, "action: " + repr(self.action)
        if self.difficulty not in VALID_DIFFICULTIES:
            return False, "difficulty: " + repr(self.difficulty)
        if not isinstance(self.roll_needed, bool):
            return False, "roll_needed должен быть bool"
        if self.skill is not None and self.skill not in VALID_SKILLS:
            return False, "skill: " + repr(self.skill)
        return True, ""


class Analyst:
    def __init__(self, config: Config, *, role: str = "analyst",
                 prompt_path: Optional[Path] = None):
        self.config = config
        self.role = role
        if prompt_path is None:
            prompt_path = ROOT_DIR / "prompts" / "analyst.txt"
        self.prompt_path = Path(prompt_path)
        if not self.prompt_path.exists():
            raise AnalystError("Нет промпта: " + str(self.prompt_path))
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

    def parse(self, player_input: str) -> ParsedCommand:
        if not player_input or not player_input.strip():
            raise AnalystError("Пустая фраза игрока")
        text = player_input.strip()

        heuristic = self._heuristic_parse(text)
        if heuristic is not None:
            print("[analyst] heuristic -> action=" + heuristic.action
                  + " skill=" + str(heuristic.skill)
                  + " roll=" + str(heuristic.roll_needed))
            return heuristic

        try:
            response = self.llm.call(
                system_prompt=self.system_prompt,
                user_message=text,
                model=self.model.id,
                temperature=0.1,
                max_tokens=300,
            )
            raw_text = self._extract_text(response)
            raw_json = self._extract_json(raw_text)
            parsed = self._to_command(raw_json, original=player_input)
            valid, reason = parsed.is_valid()
            if not valid:
                raise AnalystError("некорректный JSON: " + reason)
            print("[analyst] llm -> action=" + parsed.action
                  + " skill=" + str(parsed.skill)
                  + " roll=" + str(parsed.roll_needed))
            return parsed
        except Exception as e:
            print("[analyst] fallback (LLM): " + type(e).__name__ + ": " + str(e))
            return ParsedCommand(
                action="other", target=None, skill=None,
                roll_needed=False, difficulty="Ordinary", raw=player_input,
            )

    @staticmethod
    def _heuristic_parse(text: str) -> Optional[ParsedCommand]:
        for rx, spec in _HEURISTIC_RULES:
            if rx.search(text):
                return ParsedCommand(
                    action=spec["action"],
                    target=None,
                    skill=spec["skill"],
                    roll_needed=spec["roll_needed"],
                    difficulty=spec["difficulty"],
                    raw=text,
                )
        return None

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
            raise AnalystError("формат ответа: " + repr(response)) from e

    @staticmethod
    def _extract_json(text: str) -> dict:
        text = text.strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.lower().startswith("json"):
                text = text[4:]
            text = text.strip()
        m = _JSON_RE.search(text)
        if not m:
            if _analyst_is_refusal(text):
                raise AnalystError("GigaChat refused")
            raise AnalystError("не найден JSON: " + repr(text[:120]))
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError as e:
            raise AnalystError("битый JSON: " + str(e)) from e

    @staticmethod
    def _to_command(data: dict, original: str) -> ParsedCommand:
        return ParsedCommand(
            action=str(data.get("action", "other")),
            target=data.get("target") or None,
            skill=data.get("skill") or None,
            roll_needed=bool(data.get("roll_needed", False)),
            difficulty=str(data.get("difficulty", "Ordinary")),
            raw=original,
        )
