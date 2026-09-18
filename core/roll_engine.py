"""
core/roll_engine.py — движок бросков.

Система: d100 roll-under (Warhammer 40K Rogue Trader / FFG).
- Бросок 1d100 против целевого числа (target).
- Успех: roll <= target.
- Margin: target - roll. Положительный при успехе, отрицательный при провале.
- Degrees = |margin| // 10.
- Крит-успех: 1..5. Крит-провал: 96..100.

Все броски воспроизводимы через rng (для тестов и отладки).
"""
from __future__ import annotations

import random
import re
from dataclasses import asdict, dataclass
from typing import Optional


CRIT_SUCCESS_MAX = 5
CRIT_FAIL_MIN = 96

DIFFICULTY_MODIFIERS = {
    "Trivial":     +60,
    "Easy":        +30,
    "Routine":     +20,
    "Ordinary":    +10,
    "Challenging":   0,
    "Difficult":   -10,
    "Hard":        -20,
    "Very Hard":   -30,
    "Hellish":     -60,
}


class RollError(Exception):
    """Ошибка броска."""


@dataclass
class RollResult:
    expression: str
    reason: str
    rolls: list[int]
    modifier: int
    target: int
    total: int
    success: bool
    margin: int
    degrees: int
    crit_success: bool
    crit_fail: bool

    def to_dict(self) -> dict:
        return asdict(self)

    def format_short(self) -> str:
        if self.crit_success:
            status = "КРИТ. УСПЕХ"
        elif self.crit_fail:
            status = "КРИТ. ПРОВАЛ"
        elif self.success:
            status = "УСПЕХ"
        else:
            status = "ПРОВАЛ"

        base = self.target - self.modifier
        sign = "+" if self.modifier >= 0 else ""
        return (
            f"[{self.reason}] 1d100={self.total} vs цель {self.target} "
            f"(база {base}{sign}{self.modifier}) → {status} "
            f"(margin={self.margin}, degrees={self.degrees})"
        )


_DICE_RE = re.compile(r"^\s*(\d+)\s*d\s*(\d+)\s*([+-]\s*\d+)?\s*$", re.IGNORECASE)


def parse_dice_expression(expr: str) -> tuple[int, int, int]:
    m = _DICE_RE.match(expr)
    if not m:
        raise RollError(f"Не могу разобрать выражение: {expr!r}")
    count = int(m.group(1))
    sides = int(m.group(2))
    mod = int(m.group(3).replace(" ", "")) if m.group(3) else 0
    if count < 1 or sides < 2:
        raise RollError(f"Некорректное выражение: {expr!r}")
    return count, sides, mod


def roll_d100(rng: Optional[random.Random] = None) -> int:
    r = rng or random
    return r.randint(1, 100)


def roll_dice(
    expression: str,
    rng: Optional[random.Random] = None,
) -> tuple[list[int], int, int]:
    count, sides, mod = parse_dice_expression(expression)
    r = rng or random
    rolls = [r.randint(1, sides) for _ in range(count)]
    total = sum(rolls) + mod
    return rolls, mod, total


def check(
    base_target: int,
    *,
    modifier: int = 0,
    difficulty: Optional[str] = None,
    reason: str = "",
    rng: Optional[random.Random] = None,
) -> RollResult:
    if not isinstance(base_target, int):
        raise RollError(
            f"base_target должен быть int, а не {type(base_target).__name__}"
        )
    if base_target < 1:
        raise RollError(f"base_target должен быть >= 1, а не {base_target}")

    total_mod = int(modifier)
    if difficulty is not None:
        if difficulty not in DIFFICULTY_MODIFIERS:
            raise RollError(
                f"Неизвестная сложность: {difficulty!r}. "
                f"Допустимые: {list(DIFFICULTY_MODIFIERS)}"
            )
        total_mod += DIFFICULTY_MODIFIERS[difficulty]

    target = max(1, base_target + total_mod)

    roll = roll_d100(rng)

    success = roll <= target
    margin = target - roll
    degrees = abs(margin) // 10

    crit_success = 1 <= roll <= CRIT_SUCCESS_MAX
    crit_fail = roll >= CRIT_FAIL_MIN

    if crit_success:
        success = True
        margin = abs(margin)
        degrees = max(degrees, 1)
    elif crit_fail:
        success = False
        margin = -abs(margin)
        degrees = max(degrees, 1)

    return RollResult(
        expression="1d100",
        reason=reason,
        rolls=[roll],
        modifier=total_mod,
        target=target,
        total=roll,
        success=success,
        margin=margin,
        degrees=degrees,
        crit_success=crit_success,
        crit_fail=crit_fail,
    )