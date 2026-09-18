r"""
Тесты trigger_engine.

Запуск (из корня проекта):
    python tests\test_trigger_engine.py
"""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.state import CharacterState  # noqa: E402
from core.trigger_engine import (  # noqa: E402
    TriggerError,
    TriggerEngine,
)


def assert_eq(actual, expected, label: str) -> bool:
    if actual != expected:
        print(f"[FAIL] {label}: ожидалось {expected!r}, получено {actual!r}")
        return False
    print(f"[ ok ] {label}: {actual!r}")
    return True


def assert_true(cond, label: str) -> bool:
    if not cond:
        print(f"[FAIL] {label}")
        return False
    print(f"[ ok ] {label}")
    return True


def make_minimal_state() -> CharacterState:
    return CharacterState.from_dict(
        {
            "name": "Тест",
            "psy_rating": 2,
            "corruption": 0,
            "insanity": 0,
            "wounds": {"current": 10, "max": 10},
            "fate_points": {"current": 3, "max": 3},
        }
    )


def main() -> None:
    ok = True

    # --- Загрузка ---
    engine = TriggerEngine.load_default()
    ok &= assert_true(len(engine.triggers) >= 1, "триггеры загружены")
    ok &= assert_true(
        "psychic_power_used" in engine.events(),
        "есть событие psychic_power_used",
    )
    ok &= assert_true(
        "wounds_dropped_to_zero" in engine.events(),
        "есть событие wounds_dropped_to_zero",
    )

    # --- Простой триггер: пси-сила → +1 порча ---
    state = make_minimal_state()
    rng = random.Random(1)
    results = engine.fire("psychic_power_used", state, rng=rng)
    ok &= assert_eq(len(results), 1, "psychic_power_used: один триггер")
    ok &= assert_eq(state.get("corruption"), 1, "порча стала 1")

    # --- Триггер с dice: варп-пыль → +1d5 порча ---
    state = make_minimal_state()
    rng = random.Random(42)
    results = engine.fire("warp_dust_used", state, rng=rng)
    ok &= assert_eq(len(results), 1, "warp_dust_used: один триггер")
    cor = state.get("corruption")
    ok &= assert_true(1 <= cor <= 5, f"порча от варп-пыли в 1..5 (получено {cor})")

    # --- Условие НЕ выполняется: psy_rating=0 → триггер не срабатывает ---
    state = CharacterState.from_dict(
        {
            "name": "Не-псайкер",
            "psy_rating": 0,
            "corruption": 0,
            "wounds": {"current": 10, "max": 10},
        }
    )
    results = engine.fire("psychic_power_used", state, rng=rng)
    ok &= assert_eq(len(results), 0, "psy_rating=0 → триггер не сработал")
    ok &= assert_eq(state.get("corruption"), 0, "порча осталась 0")

    # --- Условие с 0 ран: wounds_dropped_to_zero ---
    state = make_minimal_state()
    state.set("wounds.current", 0)
    results = engine.fire("wounds_dropped_to_zero", state, rng=rng)
    ok &= assert_eq(len(results), 1, "0 ран: триггер сработал")
    ok &= assert_true(results[0].fatal, "0 ран: результат fatal=True")

    # --- Условие не выполнено: 3 раны ---
    state = make_minimal_state()
    results = engine.fire("wounds_dropped_to_zero", state, rng=rng)
    ok &= assert_eq(len(results), 0, "3 раны: death-триггер молчит")

    # --- Сложный триггер с двумя эффектами: fate_burn ---
    state = make_minimal_state()
    state.set("wounds.current", 0)
    results = engine.fire("burn_fate_to_survive", state, rng=rng)
    ok &= assert_eq(len(results), 1, "burn_fate: сработал")
    ok &= assert_eq(state.get("fate_points.current"), 2, "судьба -1 = 2")
    ok &= assert_eq(state.get("wounds.current"), 1, "раны стали 1")

    # --- Неизвестное событие: пусто ---
    state = make_minimal_state()
    results = engine.fire("no_such_event", state, rng=rng)
    ok &= assert_eq(len(results), 0, "неизвестное событие → пусто")

    # --- Неизвестный оператор ---
    bad_engine = TriggerEngine(
        triggers=[
            __import__("core.trigger_engine", fromlist=["Trigger"]).Trigger(
                id="bad",
                event="test",
                conditions=[{"path": "xp", "op": "~=", "value": 5}],
            )
        ]
    )
    try:
        bad_engine.fire("test", state)
        print("[FAIL] неизвестный оператор должен был упасть")
        ok = False
    except TriggerError:
        print("[ ok ] неизвестный оператор → TriggerError")

    # --- format_short / to_dict ---
    state = make_minimal_state()
    rng = random.Random(7)
    results = engine.fire("psychic_power_used", state, rng=rng)
    d = results[0].to_dict()
    ok &= assert_true("trigger_id" in d, "to_dict содержит trigger_id")
    ok &= assert_true("effects_applied" in d, "to_dict содержит effects_applied")

    print()
    if ok:
        print("ВСЕ ТЕСТЫ ПРОШЛИ.")
    else:
        print("ЕСТЬ ПАДЕНИЯ, см. выше.")
        sys.exit(1)


if __name__ == "__main__":
    main()