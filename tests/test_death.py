r"""
Тесты core.death.

Запуск (из корня проекта):
    python tests\test_death.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.death import (  # noqa: E402
    DeathError,
    Status,
    apply_medical_help,
    can_act,
    get_status,
    handle_zero_wounds,
    is_terminal,
    mark_dead,
    mark_retired,
    try_burn_fate,
)
from core.state import CharacterState  # noqa: E402


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


def fresh_state(**overrides) -> CharacterState:
    base = {
        "name": "Тест",
        "status": "alive",
        "wounds": {"current": 10, "max": 10},
        "fate_points": {"current": 3, "max": 3},
    }
    base.update(overrides)
    return CharacterState.from_dict(base)


def main() -> None:
    ok = True

    # --- Дефолт ---
    s = fresh_state()
    ok &= assert_eq(get_status(s), Status.ALIVE, "дефолт ALIVE")
    ok &= assert_true(can_act(s), "ALIVE может действовать")
    ok &= assert_true(not is_terminal(s), "ALIVE не терминальный")

    # --- Старый сейв без status ---
    s_old = CharacterState.from_dict({"name": "Старый", "wounds": {"current": 5, "max": 5}})
    ok &= assert_eq(get_status(s_old), Status.ALIVE, "сейв без status → ALIVE")

    # --- Некорректный status ---
    s_bad = fresh_state(status="zombie")
    try:
        get_status(s_bad)
        print("[FAIL] 'zombie' должен был упасть")
        ok = False
    except DeathError:
        print("[ ok ] некорректный status → DeathError")

    # --- handle_zero_wounds при > 0 ран: без изменений ---
    s = fresh_state()
    st = handle_zero_wounds(s)
    ok &= assert_eq(st, Status.ALIVE, "10 ран → остался ALIVE")
    ok &= assert_eq(s.get("status"), "alive", "status не изменился")

    # --- handle_zero_wounds при 0 ран: ALIVE → DYING ---
    s = fresh_state()
    s.set("wounds.current", 0)
    st = handle_zero_wounds(s)
    ok &= assert_eq(st, Status.DYING, "0 ран → DYING")
    ok &= assert_eq(s.get("status"), "dying", "status = 'dying'")
    ok &= assert_true(not can_act(s), "DYING не может действовать")

    # --- try_burn_fate: успех ---
    s = fresh_state()
    s.set("wounds.current", 0)
    handle_zero_wounds(s)
    result = try_burn_fate(s)
    ok &= assert_true(result, "сжигание Судьбы: успех")
    ok &= assert_eq(s.get("fate_points.current"), 2, "судьба 3→2")
    ok &= assert_eq(s.get("wounds.current"), 1, "раны 0→1")
    ok &= assert_eq(get_status(s), Status.ALIVE, "статус снова ALIVE")

    # --- try_burn_fate: Судьбы нет ---
    s = fresh_state(fate_points={"current": 0, "max": 3})
    s.set("wounds.current", 0)
    handle_zero_wounds(s)
    result = try_burn_fate(s)
    ok &= assert_true(not result, "без Судьбы — отказ")
    ok &= assert_eq(s.get("wounds.current"), 0, "раны остались 0")
    ok &= assert_eq(get_status(s), Status.DYING, "остался DYING")

    # --- try_burn_fate: статус ALIVE ---
    s = fresh_state()
    result = try_burn_fate(s)
    ok &= assert_true(not result, "сжигание в ALIVE — отказ")
    ok &= assert_eq(s.get("fate_points.current"), 3, "судьба не тронута")

    # --- apply_medical_help ---
    s = fresh_state()
    s.set("wounds.current", 0)
    handle_zero_wounds(s)
    result = apply_medical_help(s, heal_to=5)
    ok &= assert_true(result, "медпомощь: успех")
    ok &= assert_eq(s.get("wounds.current"), 5, "раны 0→5")
    ok &= assert_eq(get_status(s), Status.ALIVE, "статус ALIVE")

    # --- apply_medical_help: не на DYING ---
    s = fresh_state()
    ok &= assert_true(not apply_medical_help(s), "медпомощь в ALIVE — отказ")

    # --- apply_medical_help: кламп по max ---
    s = fresh_state(wounds={"current": 0, "max": 3})
    handle_zero_wounds(s)
    apply_medical_help(s, heal_to=100)
    ok &= assert_eq(s.get("wounds.current"), 3, "раны клампятся по max")

    # --- mark_dead ---
    s = fresh_state()
    mark_dead(s)
    ok &= assert_eq(get_status(s), Status.DEAD, "mark_dead → DEAD")
    ok &= assert_true(is_terminal(s), "DEAD терминальный")
    ok &= assert_true(not can_act(s), "DEAD не действует")

    # --- mark_retired ---
    s = fresh_state()
    mark_retired(s)
    ok &= assert_eq(get_status(s), Status.RETIRED, "mark_retired → RETIRED")
    ok &= assert_true(is_terminal(s), "RETIRED терминальный")

    # --- handle_zero_wounds не трогает DEAD ---
    s = fresh_state()
    mark_dead(s)
    s.set("wounds.current", 0)
    st = handle_zero_wounds(s)
    ok &= assert_eq(st, Status.DEAD, "DEAD не переходит в DYING")

    print()
    if ok:
        print("ВСЕ ТЕСТЫ ПРОШЛИ.")
    else:
        print("ЕСТЬ ПАДЕНИЯ, см. выше.")
        sys.exit(1)


if __name__ == "__main__":
    main()