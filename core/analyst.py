"""
core/analyst.py — Аналитик команд.

Превращает свободную фразу игрока в структурированный JSON.
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Optional

from core.config import Config
from core.llm_client import LLMClient


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
            return False, f"Неизвестный action: {self.action!r}"
        if self.difficulty not in VALID_DIFFICULTIES:
            return False, f"Неизвестная difficulty: {self.difficulty!r}"
        if not isinstance(self.roll_needed, bool):
            return False, f"roll_needed должен быть bool"
        return True, ""


class Analyst:
    def __init__(
        self,
        config: Config,
        *,
        role: str = "analyst",
        prompt_path: Optional[Path] = None,
    ):
        self.config = config
        self.role = role

        if prompt_path is None:
            root = Path(__file__).resolve().parents[1]
            prompt_path = root / "prompts" / "analyst.txt"
        self.prompt_path = Path(prompt_path)
        if not self.prompt_path.exists():
            raise AnalystError(f"Не найден промт: {self.prompt_path}")
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

        response = self.llm.call(
            system_prompt=self.system_prompt,
            user_message=player_input.strip(),
            model=self.model.id,
            temperature=0.1,
            max_tokens=300,
        )

        text = self._extract_text(response)
        raw_json = self._extract_json(text)
        parsed = self._to_command(raw_json, original=player_input)

        valid, reason = parsed.is_valid()
        if not valid:
            raise AnalystError(f"Некорректный JSON: {reason}\nБыло: {raw_json}")

        return parsed

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
            raise AnalystError("Не установлен пакет openai: pip install openai") from e

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
            raise AnalystError(f"Неожиданный формат ответа: {response}") from e

    @staticmethod
    def _extract_json(text: str) -> dict:
        text = text.strip()
        text = re.sub(r"^```(?:json)?\\s*", "", text)
        text = re.sub(r"\\s*```$", "", text)

        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise AnalystError(f"В ответе модели нет JSON-объекта:\n{text!r}")

        candidate = text[start : end + 1]
        try:
            data = json.loads(candidate)
        except json.JSONDecodeError as e:
            raise AnalystError(f"Не удалось распарсить JSON: {e}\nБыло:\n{candidate!r}") from e

        if not isinstance(data, dict):
            raise AnalystError(f"Ожидался JSON-объект, получено: {type(data).__name__}")
        return data

    @staticmethod
    def _to_command(data: dict, original: str) -> ParsedCommand:
        return ParsedCommand(
            action=str(data.get("action", "other")).strip(),
            target=(str(data["target"]).strip() if data.get("target") else None),
            skill=(str(data["skill"]).strip() if data.get("skill") else None),
            roll_needed=bool(data.get("roll_needed", False)),
            difficulty=str(data.get("difficulty", "Ordinary")).strip(),
            raw=original,
        )


def parse_command(player_input: str, config: Optional[Config] = None) -> ParsedCommand:
    if config is None:
        config = Config.load()
    return Analyst(config).parse(player_input)
