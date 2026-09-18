r"""
Тесты roll_engine.

Запуск (из корня проекта):
    python tests\test_roll_engine.py
"""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.roll_engine import (  # noqa: E402
    DIFFICULTY_MODIFIERS,
    RollError,
    check,
    parse_dice_expression,
    roll_d100,
    roll_dice,
)


class FixedRng:
    """Фейковый RNG для детерминированных тестов check()."""

    def __init__(self, value: int):
        self.value = value

    def randint(self, a: int, b: int) -> int:
        if a != 1 or b != 100:
            raise AssertionError(
                f"FixedRng только для d100, а тут {a}..{b}"
            )
        return self.value


def assert_eq(actual, expected, label: str) -> bool:
    if actual != expected:
        print(f"[FAIL] {label}: ожидалось {expected!r}, получено {actual!r}")
        return False
    print(f"[ ok ] {label}: {actual!r}")
    return True


def main() -> None:
    ok = True

    # --- Парсер ---
    ok &= assert_eq(parse_dice_expression("1d100"), (1, 100, 0), "parse 1d100")
    ok &= assert_eq(parse_dice_expression("2d10+3"), (2, 10, 3), "parse 2d10+3")
    ok &= assert_eq(parse_dice_expression("1d5 - 2"), (1, 5, -2), "parse 1d5 - 2")

    try:
        parse_dice_expression("abc")
        print("[FAIL] parse abc должен был упасть")
        ok = False
    except RollError:
        print("[ ok ] parse abc → RollError")

    # --- roll_d100 ---
    rng = random.Random(42)
    for _ in range(100):
        v = roll_d100(rng)
        assert 1 <= v <= 100, f"roll_d100 вне диапазона: {v}"
    print("[ ok ] roll_d100 всегда в 1..100")

    # --- roll_dice ---
    rng = random.Random(1)
    rolls, mod, total = roll_dice("2d6+1", rng)
    ok &= assert_eq(len(rolls), 2, "2d6+1: 2 кубика")
    ok &= assert_eq(mod, 1, "2d6+1: mod=1")
    ok &= assert_eq(total, sum(rolls) + 1, "2d6+1: total")

    # --- check: базовые случаи ---
    r = check(50, reason="Внимание", rng=FixedRng(32))
    ok &= assert_eq(r.total, 32, "check(50) roll=32 total")
    ok &= assert_eq(r.success, True, "check(50) roll=32 success")
    ok &= assert_eq(r.margin, 18, "check(50) roll=32 margin")
    ok &= assert_eq(r.degrees, 1, "check(50) roll=32 degrees")
    ok &= assert_eq(r.crit_success, False, "check(50) roll=32 crit_success")
    ok &= assert_eq(r.crit_fail, False, "check(50) roll=32 crit_fail")

    r = check(50, reason="Внимание", rng=FixedRng(43))
    ok &= assert_eq(r.margin, 7, "check(50) roll=43 margin")
    ok &= assert_eq(r.degrees, 0, "check(50) roll=43 degrees")

    r = check(50, reason="Внимание", rng=FixedRng(67))
    ok &= assert_eq(r.success, False, "check(50) roll=67 success=False")
    ok &= assert_eq(r.margin, -17, "check(50) roll=67 margin=-17")
    ok &= assert_eq(r.degrees, 1, "check(50) roll=67 degrees=1")

    # --- Крит ---
    r = check(50, reason="Внимание", rng=FixedRng(3))
    ok &= assert_eq(r.crit_success, True, "check(50) roll=3 crit_success")
    ok &= assert_eq(r.success, True, "check(50) roll=3 success")

    r = check(50, reason="Внимание", rng=FixedRng(98))
    ok &= assert_eq(r.crit_fail, True, "check(50) roll=98 crit_fail")
    ok &= assert_eq(r.success, False, "check(50) roll=98 success=False")

    # --- Модификатор ---
    r = check(40, modifier=20, reason="Внимание", rng=FixedRng(55))
    ok &= assert_eq(r.target, 60, "check(40, +20) target=60")
    ok &= assert_eq(r.success, True, "check(40, +20) roll=55 success")

    # --- Сложность ---
    r = check(40, difficulty="Hard", reason="Внимание", rng=FixedRng(25))
    ok &= assert_eq(r.target, 20, "check(40, Hard) target=20")
    ok &= assert_eq(r.success, False, "check(40, Hard) roll=25 success=False")

    # --- Сложность + модификатор ---
    r = check(40, modifier=10, difficulty="Easy", reason="Внимание", rng=FixedRng(50))
    ok &= assert_eq(r.target, 80, "check(40, +10, Easy) target=80")
    ok &= assert_eq(r.success, True, "check(40, +10, Easy) roll=50 success")

    # --- format_short не падает ---
    r = check(50, modifier=-20, difficulty="Hard", reason="Тест", rng=FixedRng(30))
    print(f"[ ok ] format_short: {r.format_short()}")

    print()
    if ok:
        print("ВСЕ ТЕСТЫ ПРОШЛИ.")
    else:
        print("ЕСТЬ ПАДЕНИЯ, см. выше.")
        sys.exit(1)


if __name__ == "__main__":
    main()