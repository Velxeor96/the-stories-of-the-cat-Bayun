r"""Тесты core.roll_engine — чистый pytest."""
from __future__ import annotations

import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.roll_engine import (  # noqa: E402
    DIFFICULTY_MODIFIERS,
    check,
)


class FixedRng:
    """Фейковый RNG для детерминированных тестов check()."""
    def __init__(self, value: int):
        self.value = value

    def randint(self, a: int, b: int) -> int:
        if a != 1 or b != 100:
            raise AssertionError(f"FixedRng только для d100, а тут {a}..{b}")
        return self.value


# ============================================================
# Базовые проверки d100
# ============================================================

def test_success_roll():
    r = check(50, reason="Внимание", rng=FixedRng(32))
    assert r.roll == 32
    assert r.target == 50
    assert r.success is True
    assert r.degrees == 1
    assert r.critical is None


def test_exact_threshold_success():
    r = check(50, reason="Внимание", rng=FixedRng(50))
    assert r.success is True
    assert r.degrees == 0


def test_failure_roll():
    r = check(50, reason="Внимание", rng=FixedRng(67))
    assert r.success is False
    assert r.degrees == 1
    assert r.critical is None


# ============================================================
# Крит
# ============================================================

def test_crit_success():
    r = check(50, reason="Внимание", rng=FixedRng(3))
    assert r.critical == "success"
    assert r.success is True


def test_crit_fail():
    r = check(50, reason="Внимание", rng=FixedRng(98))
    assert r.critical == "fail"
    assert r.success is False


def test_crit_fail_on_100():
    r = check(99, reason="Внимание", rng=FixedRng(100))
    assert r.critical == "fail"


# ============================================================
# Модификаторы
# ============================================================

def test_modifier_added():
    r = check(40, modifier=20, reason="Внимание", rng=FixedRng(55))
    assert r.target == 60
    assert r.success is True
    assert r.modifier == 20


def test_difficulty_hard():
    r = check(40, difficulty="Hard", reason="Внимание", rng=FixedRng(25))
    assert r.target == 40 + DIFFICULTY_MODIFIERS["Hard"]
    assert r.success is False


def test_difficulty_and_modifier():
    r = check(40, modifier=10, difficulty="Easy",
              reason="Внимание", rng=FixedRng(50))
    assert r.target == 40 + DIFFICULTY_MODIFIERS["Easy"] + 10
    assert r.success is True


def test_unknown_difficulty_zero_mod():
    r = check(40, difficulty="NoSuchDiff", reason="Внимание", rng=FixedRng(30))
    assert r.target == 40


# ============================================================
# to_dict
# ============================================================

def test_to_dict_roundtrip():
    r = check(50, reason="Внимание", rng=FixedRng(30))
    d = r.to_dict()
    for key in ("roll", "target", "base", "modifier", "success",
                "critical", "degrees", "difficulty", "reason"):
        assert key in d


def test_reason_preserved():
    r = check(50, reason="Тест разума", rng=FixedRng(30))
    assert r.reason == "Тест разума"


# ============================================================
# Random.Random совместимость
# ============================================================

def test_real_rng_range():
    rng = random.Random(42)
    for _ in range(100):
        r = check(50, reason="x", rng=rng)
        assert 1 <= r.roll <= 100
