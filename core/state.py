"""
core/state.py — менеджер состояния персонажа.

Единственный источник правды. ИИ только читает и озвучивает.
Правила (броски, триггеры) — в других модулях.
"""
from __future__ import annotations

import copy
import json
import uuid
from pathlib import Path
from typing import Any, Iterable


class StateError(Exception):
    """Базовая ошибка состояния."""


class PathError(StateError):
    """Некорректный путь."""


BOUNDS: dict[str, tuple[float, float | None]] = {
    "corruption": (0, 100),
    "insanity": (0, 100),
    "xp": (0, None),
    "money": (0, None),
    "psy_rating": (0, 10),
    "wounds.current": (0, None),
    "fate_points.current": (0, None),
    "ship.hull.current": (0, None),
    "ship.crew.current": (0, None),
}


def new_id() -> str:
    return str(uuid.uuid4())


def _deep_get(data: dict, path: str) -> Any:
    parts = path.split(".")
    cur: Any = data
    for p in parts:
        if isinstance(cur, dict):
            if p not in cur:
                raise PathError(f"Путь '{path}' не найден (сломался на '{p}')")
            cur = cur[p]
        elif isinstance(cur, list):
            try:
                cur = cur[int(p)]
            except (ValueError, IndexError):
                raise PathError(f"Путь '{path}': '{p}' не индекс списка")
        else:
            raise PathError(f"Путь '{path}': нельзя зайти в {type(cur).__name__}")
    return cur


def _deep_set(data: dict, path: str, value: Any) -> None:
    parts = path.split(".")
    cur = data
    for p in parts[:-1]:
        if p not in cur or not isinstance(cur[p], (dict, list)):
            cur[p] = {}
        cur = cur[p]
    cur[parts[-1]] = value


class CharacterState:
    """
    Обёртка над character.json.

    Ответственность:
    - загрузка/сохранение JSON (атомарно)
    - чтение/запись по точечному пути
    - применение эффектов с проверкой границ
    - краткая сводка для ИИ (get_summary)
    - история изменений (для отладки и нарратива)

    НЕ ответственность:
    - броски (roll_engine.py)
    - триггеры (trigger_engine.py)
    - правила системы (rules/, а не этот класс)
    """

    def __init__(self, data: dict, path: Path | None = None):
        if not isinstance(data, dict):
            raise StateError("character.json должен быть словарём на верхнем уровне")
        self.data = data
        self.path = Path(path) if path else None
        self._history: list[dict] = []

    @classmethod
    def load(cls, path: str | Path) -> "CharacterState":
        p = Path(path)
        if not p.exists():
            raise StateError(f"Файл не найден: {p}")
        with p.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return cls(data, p)

    @classmethod
    def from_dict(cls, data: dict) -> "CharacterState":
        return cls(copy.deepcopy(data))

    def save(self, path: str | Path | None = None) -> Path:
        """Атомарное сохранение: пишем в .tmp, потом replace."""
        target = Path(path) if path else self.path
        if target is None:
            raise StateError("Не указан путь сохранения")
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_suffix(target.suffix + ".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
        tmp.replace(target)
        return target

    def to_dict(self) -> dict:
        return copy.deepcopy(self.data)

    def ensure_ids(self) -> dict:
        """Добавить session_id / player_id / character_id, если их нет."""
        for key in ("session_id", "player_id", "character_id"):
            if not self.data.get(key):
                self.data[key] = new_id()
        return {
            "session_id": self.data["session_id"],
            "player_id": self.data["player_id"],
            "character_id": self.data["character_id"],
        }

    def get(self, path: str, default: Any = None) -> Any:
        try:
            return _deep_get(self.data, path)
        except PathError:
            return default

    def set(self, path: str, value: Any) -> None:
        _deep_set(self.data, path, value)
        self.recalc_derived()

    def recalc_derived(self) -> None:
        """Бонусы = характеристика // 10. Вызывается после любого изменения."""
        chars = self.data.get("characteristics")
        if isinstance(chars, dict):
            self.data["bonuses"] = {k: int(v) // 10 for k, v in chars.items()}

    def apply_effect(self, effect: dict) -> dict:
        """
        Применить один эффект.

        Формат:
            {"op": "add"|"sub"|"set"|"append"|"remove",
             "path": "wounds.current",
             "value": -3}
        """
        op = effect.get("op")
        path = effect.get("path")
        value = effect.get("value")

        if not op or not path:
            raise StateError(f"Эффект должен содержать op и path: {effect}")
        if op not in {"add", "sub", "set", "append", "remove"}:
            raise StateError(f"Неизвестная операция: {op}")

        before = self.get(path)

        if op == "set":
            after = value
        elif op == "add":
            after = (before or 0) + value
        elif op == "sub":
            after = (before or 0) - value
        elif op == "append":
            if before is None:
                _deep_set(self.data, path, [])
                before = []
            if not isinstance(before, list):
                raise StateError(
                    f"append можно только в список, а '{path}' — {type(before).__name__}"
                )
            before.append(value)
            after = before
        elif op == "remove":
            if not isinstance(before, list):
                raise StateError(
                    f"remove можно только из списка, а '{path}' — {type(before).__name__}"
                )
            try:
                before.remove(value)
            except ValueError:
                raise StateError(f"Элемент {value!r} не найден в '{path}'")
            after = before

        after = self._apply_bounds(path, after)
        _deep_set(self.data, path, after)
        self.recalc_derived()

        delta = None
        if isinstance(after, (int, float)) and isinstance(before, (int, float)):
            delta = after - before

        record = {"op": op, "path": path, "before": before, "after": after, "delta": delta}
        self._history.append(record)
        return record

    def apply_effects(self, effects: Iterable[dict]) -> list[dict]:
        return [self.apply_effect(e) for e in effects]

    def _apply_bounds(self, path: str, value: Any) -> Any:
        if not isinstance(value, (int, float)):
            return value

        lo, hi = BOUNDS.get(path, (None, None))

        if path == "wounds.current":
            hi = self.get("wounds.max", hi)
        elif path == "fate_points.current":
            hi = self.get("fate_points.max", hi)
        elif path == "ship.hull.current":
            hi = self.get("ship.hull.max", hi)
        elif path == "ship.crew.current":
            hi = self.get("ship.crew.max", hi)

        if lo is not None:
            value = max(lo, value)
        if hi is not None:
            value = min(hi, value)
        return value

    @property
    def history(self) -> list[dict]:
        return list(self._history)

    def clear_history(self) -> None:
        self._history.clear()

    def is_dead(self) -> bool:
        """Упрощённо: 0 ран = смерть. Уточним в rules/."""
        return self.get("wounds.current", 1) <= 0

    def get_summary(self) -> str:
        """
        Компактная сводка для промта Мастеру.
        Только факты о состоянии. Никаких правил.
        """
        d = self.data
        chars = d.get("characteristics", {}) or {}
        chars_str = ", ".join(f"{k}:{v}" for k, v in chars.items())

        wounds = d.get("wounds", {}) or {}
        fate = d.get("fate_points", {}) or {}
        ship = d.get("ship", {}) or {}
        hull = ship.get("hull", {}) or {}
        crew = ship.get("crew", {}) or {}

        lines = [
            f"Имя: {d.get('name', '?')}",
            f"Раса/фракция: {d.get('faction', '?')} / {d.get('subfaction', '?')}",
            f"Архетип: {d.get('archetype', '?')}",
            f"Ранг: {d.get('rank', '?')}    XP: {d.get('xp', 0)}",
            f"Характеристики: {chars_str}",
            f"Ранения: {wounds.get('current', '?')}/{wounds.get('max', '?')}",
            f"Очки Судьбы: {fate.get('current', '?')}/{fate.get('max', '?')}",
            f"Порча: {d.get('corruption', 0)}    Безумие: {d.get('insanity', 0)}",
        ]

        psy_rating = d.get("psy_rating", 0)
        if psy_rating:
            lines.append(f"Пси-рейтинг: {psy_rating}")
            powers = d.get("psychic_powers") or []
            if powers:
                lines.append(f"Пси-силы: {', '.join(map(str, powers))}")

        # Навыки: краткий список "Имя (хар-ка: значение)"
        skills = d.get("skills") or []
        if skills:
            sk = "; ".join(
                f"{s.get('name', '?')} ({s.get('characteristic', '?')}:{s.get('value', '?')})"
                for s in skills
            )
            lines.append(f"Навыки: {sk}")

        talents = d.get("talents") or []
        if talents:
            lines.append(f"Таланты: {', '.join(map(str, talents))}")

        # Броня: суммарная сводка по equipped-частям
        armour = d.get("armour") or {}
        if armour:
            equipped_parts = []
            for part in ("head", "body", "arms", "legs"):
                p = armour.get(part) or {}
                if p.get("equipped"):
                    equipped_parts.append(f"{part}:{p.get('value', '?')}")
            notes = armour.get("notes")
            arm_str = ", ".join(equipped_parts) if equipped_parts else "снята"
            if notes:
                arm_str += f" ({notes})"
            lines.append(f"Броня: {arm_str}")

        weapons = d.get("weapons") or []
        if weapons:
            w = "; ".join(
                f"{x.get('name', '?')} ({x.get('stats', '')})"
                + ("" if x.get("equipped") else " [снято]")
                for x in weapons
            )
            lines.append(f"Оружие: {w}")

        eq = d.get("equipment") or []
        if eq:
            lines.append(f"Снаряжение: {', '.join(map(str, eq))}")

        unequipped = d.get("unequipped_items") or []
        if unequipped:
            lines.append(f"Снято: {', '.join(map(str, unequipped))}")

        special = d.get("special_resources") or {}
        if special:
            sr = ", ".join(f"{k}: {v}" for k, v in special.items())
            lines.append(f"Особые ресурсы: {sr}")

        money = d.get("money", 0)
        currency = d.get("currency", "")
        extra_cur = d.get("extra_currencies") or {}
        money_str = f"{money} {currency}".strip()
        if extra_cur:
            extra = ", ".join(f"{k}: {v}" for k, v in extra_cur.items())
            money_str += f" (+ {extra})"
        lines.append(f"Деньги: {money_str}")

        effects = d.get("effects") or []
        if effects:
            lines.append(f"Активные эффекты: {effects}")

        goals = d.get("goals") or []
        if goals:
            lines.append(f"Цели: {goals}")

        quests = d.get("quests") or []
        if quests:
            lines.append(f"Квесты: {quests}")

        companions = d.get("companions") or []
        if companions:
            lines.append(f"Спутники: {companions}")

        npcs = d.get("npcs") or []
        if npcs:
            lines.append(f"NPC: {npcs}")

        if ship:
            lines.append(
                f"Корабль: {ship.get('name', '?')} ({ship.get('class', '?')}), "
                f"корпус {hull.get('current', '?')}/{hull.get('max', '?')}, "
                f"экипаж {crew.get('current', '?')}/{crew.get('max', '?')}, "
                f"статус: {ship.get('status', '?')}"
            )

        lines.append(
            f"Локация: {d.get('location', '?')}    Время: {d.get('game_date', '?')}"
        )

        rep = d.get("reputation") or {}
        nonzero = {k: v for k, v in rep.items() if v}
        if nonzero:
            lines.append(f"Репутация: {nonzero}")

        notes = d.get("notes")
        if notes:
            lines.append(f"Заметки: {notes}")

        return "\n".join(lines)

    @property
    def xp(self) -> int:
        return int(self.data.get("xp", 0))

    @property
    def wounds(self) -> dict:
        return self.data.get("wounds", {})

    @property
    def fate(self) -> dict:
        return self.data.get("fate_points", {})

    def __repr__(self) -> str:
        return (
            f"<CharacterState name={self.data.get('name')!r} "
            f"xp={self.xp} wounds={self.wounds.get('current')}/{self.wounds.get('max')}>"
        )