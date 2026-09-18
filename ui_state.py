"""Адаптер состояния: dict (legacy) → API похожее на CharacterState.

Зачем: legacy-формат листа не совпадает со строгой схемой CharacterState.
Адаптер даёт оркестратору минимально необходимый API, не требуя миграции.
"""
from __future__ import annotations

import random
from typing import Any, Optional


class StateAdapter:
    """Обёртка над dict для ядра (get/set/to_dict/get_summary)."""

    def __init__(self, data: dict):
        self._data = data if isinstance(data, dict) else {}

    def get(self, path: str, default: Any = None) -> Any:
        cur: Any = self._data
        for part in path.split("."):
            if isinstance(cur, dict) and part in cur:
                cur = cur[part]
            else:
                return default
        return cur

    def set(self, path: str, value: Any) -> None:
        parts = path.split(".")
        cur = self._data
        for p in parts[:-1]:
            if not isinstance(cur.get(p), dict):
                cur[p] = {}
            cur = cur[p]
        cur[parts[-1]] = value

    def to_dict(self) -> dict:
        return self._data

    def get_summary(self) -> str:
        name = self._data.get("name", "Безымянный")
        w = self._data.get("wounds") or {}
        if isinstance(w, dict):
            cur, mx = w.get("current", 0), w.get("max", 0)
        else:
            cur, mx = 0, 0
        return f"Имя: {name}\nРаны: {cur}/{mx}"

    def is_dead(self) -> bool:
        w = self._data.get("wounds") or {}
        if isinstance(w, dict):
            return int(w.get("current", 1)) <= 0
        return False


# ---------- Автоэффекты от броска ----------
# Правило: успех даёт XP, провал отнимает раны в зависимости от типа действия.
# Тип действия берётся из ParsedCommand.action (см. core/analyst.py).

_DMG_ON_FAIL = {
    "attack_melee": 1,
    "attack_ranged": 1,
    "defend": 1,
    "use_psychic": 2,
}
_DMG_ON_CRIT_FAIL = {a: v * 2 for a, v in _DMG_ON_FAIL.items()}
_DMG_ON_CRIT_FAIL["use_psychic"] = 5
_DMG_ON_CRIT_FAIL["attack_melee"] = 4

_STEALTH_ACTIONS = {"stealth"}
_SOCIAL_ACTIONS = {"persuade", "deceive", "intimidate", "talk"}

_XP_CRIT = 5
_XP_SUCCESS = 2


def apply_turn_effects(
    state: StateAdapter,
    result: Any,
    *,
    rng: Optional[random.Random] = None,
) -> list[tuple[str, str, str]]:
    """Применяет эффекты хода. Возвращает список (kind, label, icon)."""
    rng = rng or random
    changes: list[tuple[str, str, str]] = []

    roll = getattr(result, "roll", None)
    cmd = getattr(result, "command", None)
    if roll is None or cmd is None:
        return changes

    action = getattr(cmd, "action", "other") or "other"
    success = bool(roll.success)
    crit_ok = bool(getattr(roll, "crit_success", False))
    crit_bad = bool(getattr(roll, "crit_fail", False))

    # --- XP ---
    xp_gain = _XP_CRIT if crit_ok else (_XP_SUCCESS if success else 0)
    if xp_gain > 0:
        cur = int(state.get("xp", 0) or 0)
        state.set("xp", cur + xp_gain)
        changes.append(("xp", f"+{xp_gain} опыта", "\u2b50"))

    # --- Раны от провала ---
    if not success:
        if crit_bad:
            dmg = _DMG_ON_CRIT_FAIL.get(action, 2)
        else:
            dmg = _DMG_ON_FAIL.get(action, 0)

        if dmg > 0:
            w = state.get("wounds", {}) or {}
            if isinstance(w, dict):
                cur_hp = int(w.get("current", 0) or 0)
                new_hp = max(0, cur_hp - dmg)
                w["current"] = new_hp
                state.set("wounds", w)
                icon = "\U0001fa78" if not crit_bad else "\U0001f480"
                changes.append(("wounds", f"-{dmg} ран", icon))

    # --- Скрытность на провале → Замечен ---
    if not success and action in _STEALTH_ACTIONS:
        effects = list(state.get("effects", []) or [])
        tag = "Замечен"
        if tag not in effects:
            effects.append(tag)
            state.set("effects", effects)
            changes.append(("effect", "Замечен", "\U0001f441\ufe0f"))

    # --- Социальный провал → -1 к репутации случайной фракции ---
    if not success and action in _SOCIAL_ACTIONS:
        rep = state.get("reputation", {}) or {}
        if isinstance(rep, dict) and rep:
            fac = rng.choice(list(rep.keys()))
            rep[fac] = int(rep.get(fac, 0)) - 1
            state.set("reputation", rep)
            changes.append(("rep", f"{fac} -1", "\U0001f5e3\ufe0f"))

    # --- Крит-успех в атаке → жетон боевой славы ---
    if crit_ok and action.startswith("attack_"):
        effects = list(state.get("effects", []) or [])
        tag = "Окрылён победой"
        if tag not in effects:
            effects.append(tag)
            state.set("effects", effects)
            changes.append(("effect", "Окрылён победой", "\u2694\ufe0f"))

    return changes

# ============================================================
# patch25: расширенные эффекты
# ============================================================

def _apply_gender_default(state) -> None:
    """Гарантирует наличие gender."""
    if state.get("gender") is None:
        state.set("gender", "male")


def _add_money_on_success(state, amount: int) -> list:
    """Начисление денег при успехе."""
    changes = []
    if amount <= 0:
        return changes
    cur = int(state.get("money", 0) or 0)
    state.set("money", cur + amount)
    cur_name = state.get("currency", "монет")
    changes.append(("money", f"+{amount} {cur_name}", "\u25ce"))
    return changes


def _add_corruption_on_crit_fail(state, amount: int = 1) -> list:
    """Порча при крит.провале психики."""
    changes = []
    if amount <= 0:
        return changes
    cur = int(state.get("corruption", 0) or 0)
    state.set("corruption", cur + amount)
    changes.append(("corruption", f"+{amount} порчи", "\u2625"))
    return changes


def _add_insanity_on_crit_fail(state, amount: int = 1) -> list:
    """Безумие при крит.провале в псих-действиях."""
    changes = []
    if amount <= 0:
        return changes
    cur = int(state.get("insanity", 0) or 0)
    state.set("insanity", cur + amount)
    changes.append(("insanity", f"+{amount} безумия", "\u2623"))
    return changes


def _level_up(state) -> list:
    """Проверка повышения ранга при накоплении XP."""
    changes = []
    xp = int(state.get("xp", 0) or 0)
    rank = int(state.get("rank", 1) or 1)
    threshold = rank * 500
    if xp >= threshold:
        state.set("rank", rank + 1)
        state.set("xp", xp - threshold)
        changes.append(("level_up", f"Ранг {rank+1}!", "\u2605"))
    return changes


def apply_turn_effects_pro(state, result, rng=None) -> list:
    """Расширенные эффекты: XP, порча, деньги, повышение ранга."""
    import random as _rng
    rng = rng or _rng
    changes = []

    roll = getattr(result, "roll", None)
    cmd = getattr(result, "command", None)
    if roll is None or cmd is None:
        return changes

    action = getattr(cmd, "action", "other") or "other"
    success = bool(roll.success)
    crit_ok = bool(getattr(roll, "crit_success", False))
    crit_bad = bool(getattr(roll, "crit_fail", False))

    # Пол — всегда есть
    _apply_gender_default(state)

    # XP
    if success:
        gain = 5 if crit_ok else 2
        cur = int(state.get("xp", 0) or 0)
        state.set("xp", cur + gain)
        changes.append(("xp", f"+{gain} опыта", "\u2605"))
        changes.extend(_level_up(state))

    # Деньги за успешное обыскивание
    if success and action in ("search", "observe", "take"):
        money = 10 if crit_ok else (5 if rng.random() < 0.4 else 0)
        if money:
            changes.extend(_add_money_on_success(state, money))

    # Порча/безумие за крит.провал
    if crit_bad and action == "use_psychic":
        changes.extend(_add_corruption_on_crit_fail(state, 2))
        changes.extend(_add_insanity_on_crit_fail(state, 1))

    return changes
