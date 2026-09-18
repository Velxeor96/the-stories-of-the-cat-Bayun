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
            state, command, roll=roll, history=history or []
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
