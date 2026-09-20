"""core/roll_engine.py — броски d100 и определение успеха/провала.

Терминология Rogue Trader:
  - Характеристики и навыки: значения 0–100.
  - Бросок: d100 (1..100). roll <= target — успех.
  - Сложность модифицирует base. Trivial +60, Ordinary 0, Hellish -60 и т.д.
  - Крит: 1–5 — критический успех, 96–100 — критический провал.
  - Марки успеха: (target - roll) // 10 (только для успеха).

Никаких вызовов LLM. Чистая математика.
"""
from __future__ import annotations

import random
from dataclasses import dataclass


# Модификаторы сложности по канону WH40K
DIFFICULTY_MODIFIERS: dict[str, int] = {
    "Trivial":     +60,
    "Easy":        +40,
    "Routine":     +20,
    "Ordinary":    0,
    "Challenging": -10,
    "Difficult":   -20,
    "Hard":        -30,
    "Very Hard":   -40,
    "Hellish":     -60,
}

CRIT_SUCCESS_MAX = 5
CRIT_FAIL_MIN = 96


@dataclass
class RollResult:
    """Результат одного броска d100."""
    roll: int
    target: int
    base: int
    modifier: int
    success: bool
    critical: str | None  # "success" | "fail" | None
    degrees: int
    difficulty: str
    reason: str

    def to_dict(self) -> dict:
        return {
            "roll": self.roll,
            "target": self.target,
            "base": self.base,
            "modifier": self.modifier,
            "success": self.success,
            "critical": self.critical,
            "degrees": self.degrees,
            "difficulty": self.difficulty,
            "reason": self.reason,
        }


def check(
    base: int,
    *,
    difficulty: str | None = None,
    modifier: int = 0,
    reason: str = "",
    rng: random.Random | None = None,
) -> RollResult:
    """Сделать бросок d100 против base с учётом difficulty и modifier.

    Итоговый target = base + difficulty_mod + modifier.
    Может уйти в минус — это нормально, любой бросок будет провалом.
    """
    diff_mod = DIFFICULTY_MODIFIERS.get(difficulty or "", 0)
    total_mod = diff_mod + modifier
    target = base + total_mod

    r = rng if rng is not None else random
    roll = r.randint(1, 100)

    success = roll <= target

    critical: str | None = None
    if success and roll <= CRIT_SUCCESS_MAX:
        critical = "success"
    elif (not success) and roll >= CRIT_FAIL_MIN:
        critical = "fail"

    if success:
        degrees = max(0, (target - roll) // 10)
    else:
        degrees = max(0, (roll - target) // 10)

    return RollResult(
        roll=roll,
        target=target,
        base=base,
        modifier=total_mod,
        success=success,
        critical=critical,
        degrees=degrees,
        difficulty=difficulty or "",
        reason=reason,
    )
