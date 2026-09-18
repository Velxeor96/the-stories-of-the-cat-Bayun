"""
core/death.py — Death State Machine.

Статусы персонажа:
    ALIVE   — живой, может действовать
    DYING   — на 0 ран, при смерти, но ещё не мёртв.
              Спасается сжиганием Судьбы или медицинской помощью.
    DEAD    — мёртв. Терминальный статус, действий нет.
    RETIRED — ушёл на покой / выбыл из игры по воле игрока.
              Не мёртв, но не действует.

Правила переходов:
    ALIVE → DYING   : wounds.current == 0 и нет Судьбы
    ALIVE → DYING   : wounds.current == 0, Судьба есть, но не сжёг
    DYING → ALIVE   : сжечь Очко Судьбы (wounds.current := 1)
    DYING → DEAD    : добивание / отсутствие помощи (явный вызов)
    любой → RETIRED : явный вызов
"""
from __future__ import annotations

from enum import Enum

from core.state import CharacterState


class Status(str, Enum):
    ALIVE = "alive"
    DYING = "dying"
    DEAD = "dead"
    RETIRED = "retired"


class DeathError(Exception):
    """Ошибка перехода статуса."""


_VALID = {s.value for s in Status}


# ============================================================
# Чтение
# ============================================================

def get_status(state: CharacterState) -> Status:
    """Вернуть текущий статус. Если нет — 'alive' (для старых сейвов)."""
    raw = state.get("status", Status.ALIVE.value)
    if raw not in _VALID:
        raise DeathError(
            f"Некорректный status='{raw}'. Допустимо: {sorted(_VALID)}"
        )
    return Status(raw)


def can_act(state: CharacterState) -> bool:
    """Может ли персонаж совершать действия."""
    return get_status(state) == Status.ALIVE


def is_terminal(state: CharacterState) -> bool:
    """Терминальные статусы — игра для персонажа закончена."""
    return get_status(state) in (Status.DEAD, Status.RETIRED)


# ============================================================
# Переходы
# ============================================================

def handle_zero_wounds(state: CharacterState) -> Status:
    """
    Вызывается после того, как wounds.current достиг 0.
    Возвращает новый статус.

    Логика:
    - Если Судьбы нет — сразу DYING (ждём явного решения игрока: сжечь или умереть).
    - Если Судьба есть — тоже DYING. Сжигание — отдельное действие
      (try_burn_fate), чтобы игрок сам решал.
    """
    if state.get("wounds.current", 0) > 0:
        return get_status(state)

    current = get_status(state)
    if current != Status.ALIVE:
        return current

    state.set("status", Status.DYING.value)
    return Status.DYING


def try_burn_fate(state: CharacterState) -> bool:
    """
    Попытка сжечь Очко Судьбы, чтобы выжить на 1 ране.

    Возвращает:
        True  — Судьба сожжена, wounds.current := 1, статус ALIVE
        False — Судьбы нет или статус не DYING, ничего не изменено
    """
    if get_status(state) != Status.DYING:
        return False

    fate = state.get("fate_points.current", 0)
    if not isinstance(fate, int) or fate < 1:
        return False

    state.apply_effect({"op": "sub", "path": "fate_points.current", "value": 1})
    state.apply_effect({"op": "set", "path": "wounds.current", "value": 1})
    state.set("status", Status.ALIVE.value)
    return True


def apply_medical_help(state: CharacterState, heal_to: int = 1) -> bool:
    """
    Внешняя помощь (аптечка, медик, пси-восстановление).
    Работает только для DYING.

    Возвращает True, если статус подняли до ALIVE.
    """
    if get_status(state) != Status.DYING:
        return False

    if heal_to < 1:
        raise DeathError("heal_to должен быть >= 1")

    max_w = state.get("wounds.max", heal_to)
    heal_to = min(heal_to, max_w)

    state.apply_effect({"op": "set", "path": "wounds.current", "value": heal_to})
    state.set("status", Status.ALIVE.value)
    return True


def mark_dead(state: CharacterState) -> None:
    """Терминальный переход: мёртв."""
    state.set("status", Status.DEAD.value)


def mark_retired(state: CharacterState) -> None:
    """Терминальный переход: вышел из игры (не мёртв)."""
    state.set("status", Status.RETIRED.value)


# ============================================================
# Сводка для ИИ
# ============================================================

_STATUS_HINT = {
    Status.ALIVE:   "Живой. Действует.",
    Status.DYING:   "При смерти. Не может действовать, пока не спасён.",
    Status.DEAD:    "Мёртв. Не действует. Игра для персонажа окончена.",
    Status.RETIRED: "Вышел из игры. Не действует.",
}


def get_summary(state: CharacterState) -> str:
    """Строка для промта Мастеру."""
    st = get_status(state)
    return f"Статус: {st.value} — {_STATUS_HINT[st]}"