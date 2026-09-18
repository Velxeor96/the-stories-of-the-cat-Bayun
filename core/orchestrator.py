"""Оркестратор хода: Moderator → Analyst → roll → triggers → Master.

Принцип: состояние и правила — в Python. ИИ только читает/озвучивает.

Полный цикл хода:
    input
      → Moderator.check()
         ├── RESHAPE / REJECT → redirect + варианты, стоп (нет вызовов LLM)
         └── ALLOW
      → Analyst.parse()
      → если roll_needed: state.get(skill) → roll_engine.check()
      → trigger_engine.fire(roll_success | roll_failure)
      → Master.narrate()
      → ensure_action_variants()
      → TurnResult
"""
from __future__ import annotations

import re

from dataclasses import dataclass, field
from typing import Any, Optional

from core.analyst import Analyst, ParsedCommand
from core.config import Config
from core.master import Master, Turn
from core.moderator import ModerationResult, Moderator
from core.roll_engine import RollResult, check
from core.trigger_engine import TriggerEngine, TriggerResult
from core.variants import ensure_action_variants

DEFAULT_SKILL_VALUE = 45

# Служебные сообщения от интерфейса (кнопки проверок, quick actions).
_SERVICE_CHECK_RE = re.compile(r"^\[\u041f\u0420\u041e\u0412\u0415\u0420\u041a\u0410\]", re.IGNORECASE)
_SERVICE_ACTION_RE = re.compile(
    r"^\[(\u0414\u0415\u0419\u0421\u0422\u0412\u0418\u0415|\u041f\u0421\u0418|"
    r"\u0420\u0410\u0423\u041d\u0414|\u0422\u0410\u041b\u0410\u041d\u0422|"
    r"\u0417\u0410\u0414\u0410\u041d\u0418\u0415|\u041f\u0420\u0415\u0414\u041c\u0415\u0422|"
    r"\u041e\u0427\u041a\u0418 \u0421\u0423\u0414\u042c\u0411\u042b|\u042d\u041a\u0418\u041f\u0418\u0420\u041e\u0412\u041a\u0410)\]",
    re.IGNORECASE,
)


def _detect_service_command(text):
    """Возвращает 'check' | 'action' | None."""
    if not text:
        return None
    if _SERVICE_CHECK_RE.match(text):
        return "check"
    if _SERVICE_ACTION_RE.match(text):
        return "action"
    return None


_SKILL_RE = re.compile(r"\u0425\u0430\u0440\u0430\u043a\u0442\u0435\u0440\u0438\u0441\u0442\u0438\u043a\u0430:\s*([\w\s\-]+?)(?:\s*\(|\u00b7|$)")
_EFF_RE = re.compile(r"\u042d\u0444\u0444\u0435\u043a\u0442\u0438\u0432\u043d\u043e\u0435 \u0437\u043d\u0430\u0447\u0435\u043d\u0438\u0435:\s*(\d+)")
_BASE_RE = re.compile(r"\u0411\u0430\u0437\u0430:\s*(\d+)")


@dataclass
class TurnResult:
    """Итог одного хода. Всё, что нужно UI и логам."""
    player_input: str
    moderation: ModerationResult
    command: Optional[ParsedCommand] = None
    roll: Optional[RollResult] = None
    triggers: list[TriggerResult] = field(default_factory=list)
    narrative: str = ""

    @property
    def blocked(self) -> bool:
        """Ход перехвачен модератором (RESHAPE или REJECT)."""
        return self.moderation.verdict != "ALLOW"

    def to_dict(self) -> dict:
        return {
            "player_input": self.player_input,
            "moderation": {
                "verdict": self.moderation.verdict,
                "reason": self.moderation.reason,
                "matched_rule": self.moderation.matched_rule,
            },
            "command": self.command.to_dict() if self.command else None,
            "roll": self.roll.to_dict() if self.roll else None,
            "triggers": [t.to_dict() for t in self.triggers],
            "narrative": self.narrative,
            "blocked": self.blocked,
        }


class OrchestratorError(Exception):
    """Ошибка оркестратора."""


class Orchestrator:
    """Связка всех модулей в один ход."""

    def __init__(
        self,
        *,
        master: Master,
        moderator: Moderator,
        analyst: Analyst,
        trigger_engine: TriggerEngine,
        rng: Any = None,
    ):
        self.master = master
        self.moderator = moderator
        self.analyst = analyst
        self.trigger_engine = trigger_engine
        self.rng = rng

    @classmethod
    def from_config(cls, config: Config, *, rng: Any = None) -> "Orchestrator":
        return cls(
            master=Master(config),
            moderator=Moderator(config),
            analyst=Analyst(config),
            trigger_engine=TriggerEngine.load_default(),
            rng=rng,
        )

    # ---------- Основной метод ----------

    def process_turn(
        self,
        player_input: str,
        state: Any,
        *,
        history: Optional[list[Turn]] = None,
        extra_context: str = "",
    ) -> TurnResult:
        # 1. Модерация
        mod = self.moderator.check(player_input)
        if mod.verdict != "ALLOW":
            redirect = (mod.redirect or "").strip() or "Ты возвращаешься к сцене."
            narrative = ensure_action_variants(redirect)
            return TurnResult(
                player_input=player_input,
                moderation=mod,
                narrative=narrative,
            )

        # 1.5. Служебные сообщения от UI — парсим без Analyst
        service = _detect_service_command(player_input)
        if service == "check":
            return self._handle_service_check(player_input, state, history)
        if service == "action":
            return self._handle_service_action(player_input, state, history)

        # 2. Разбор команды
        command = self.analyst.parse(player_input)

        # 3. Бросок (если нужен)
        roll: Optional[RollResult] = None
        if command.roll_needed and command.skill:
            base = self._lookup_skill(state, command.skill)
            roll = check(
                base,
                difficulty=command.difficulty,
                reason=command.skill,
                rng=self.rng,
            )

        # 4. Триггеры
        triggers: list[TriggerResult] = []
        if roll is not None:
            event = "roll_success" if roll.success else "roll_failure"
            triggers = self.trigger_engine.fire(event, state, rng=self.rng)

        # 5. Текст Мастера
        narrative = self.master.narrate(
            state, command, roll=roll, history=history or [],
            extra_context=extra_context,
        )
        narrative = ensure_action_variants(narrative)

        return TurnResult(
            player_input=player_input,
            moderation=mod,
            command=command,
            roll=roll,
            triggers=triggers,
            narrative=narrative,
        )

    # ---------- Вспомогательные ----------

    # ---------- Служебные сообщения ----------

    def _handle_service_check(self, text, state, history):
        """[ПРОВЕРКА] Характеристика: WS ... Эффективное значение: 30"""
        m_skill = _SKILL_RE.search(text)
        m_eff = _EFF_RE.search(text)
        m_base = _BASE_RE.search(text)
        if m_eff:
            base = int(m_eff.group(1))
        elif m_base:
            base = int(m_base.group(1))
        else:
            base = DEFAULT_SKILL_VALUE
        skill = m_skill.group(1).strip() if m_skill else "\u041f\u0440\u043e\u0432\u0435\u0440\u043a\u0430"

        roll = check(base, modifier=0, difficulty=None, reason=skill, rng=self.rng)
        command = ParsedCommand(
            action="other", target=skill, skill=skill,
            roll_needed=True, difficulty="Ordinary", raw=text,
        )
        triggers = []
        event = "roll_success" if roll.success else "roll_failure"
        triggers = self.trigger_engine.fire(event, state, rng=self.rng)

        narrative = self.master.narrate(state, command, roll=roll, history=history or [])
        narrative = ensure_action_variants(narrative)

        return TurnResult(
            player_input=text,
            moderation=ModerationResult(verdict="ALLOW", reason="service_check"),
            command=command, roll=roll, triggers=triggers, narrative=narrative,
        )

    def _handle_service_action(self, text, state, history):
        """[ДЕЙСТВИЕ] ... / [ПСИ] ... / [ТАЛАНТ] ... — без броска."""
        command = ParsedCommand(
            action="other", target=None, skill=None,
            roll_needed=False, difficulty="Ordinary", raw=text,
        )
        narrative = self.master.narrate(state, command, roll=None, history=history or [])
        narrative = ensure_action_variants(narrative)
        return TurnResult(
            player_input=text,
            moderation=ModerationResult(verdict="ALLOW", reason="service_action"),
            command=command, roll=None, triggers=[], narrative=narrative,
        )

    @staticmethod
    def _lookup_skill(state: Any, skill: str) -> int:
        """Ищет характеристику в state по нескольким возможным путям.

        Если ничего не нашли — возвращает DEFAULT_SKILL_VALUE (45).
        Никогда не бросает: бой не должен падать из-за опечатки в пути.
        """
        if not skill:
            return DEFAULT_SKILL_VALUE

        candidates = [
            f"skills.{skill}",
            f"skills.{skill.upper()}",
            f"skills.{skill.lower()}",
            f"characteristics.{skill}",
            f"attributes.{skill}",
            f"stats.{skill}",
        ]
        for path in candidates:
            try:
                v = state.get(path)
            except Exception:
                continue
            if isinstance(v, (int, float)):
                return int(v)
        return DEFAULT_SKILL_VALUE
