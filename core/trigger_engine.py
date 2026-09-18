"""
core/trigger_engine.py — движок триггеров.

Событие (event) → список эффектов, которые применяются к CharacterState.

Правила хранятся в rules/*.json (данные), а не в коде.
Это значит: чтобы добавить новый триггер — правим JSON, не Python.

Поддерживаемые операторы условий:
    ==, !=, >, >=, <, <=, in, not_in, contains

Значения эффектов:
    - число: {"op":"add","path":"corruption","value":1}
    - dice:  {"op":"add","path":"corruption","value":"1d5"}
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional

from core.roll_engine import roll_dice
from core.state import CharacterState


class TriggerError(Exception):
    """Ошибка триггера."""


@dataclass
class Trigger:
    id: str
    event: str
    effects: list[dict] = field(default_factory=list)
    description: str = ""
    conditions: list[dict] = field(default_factory=list)
    message: str = ""
    fatal: bool = False


@dataclass
class TriggerResult:
    trigger_id: str
    event: str
    message: str
    description: str
    effects_applied: list[dict]
    fatal: bool

    def to_dict(self) -> dict:
        return asdict(self)


class TriggerEngine:
    """
    Загружает таблицу триггеров из JSON, применяет к CharacterState.

    Использование:
        engine = TriggerEngine.load_default()
        results = engine.fire("psychic_power_used", state)
        for r in results:
            print(r.message, r.effects_applied)
    """

    def __init__(self, triggers: list[Trigger]):
        self.triggers = triggers

    # ---------- Загрузка ----------

    @classmethod
    def from_file(cls, path: str | Path) -> "TriggerEngine":
        p = Path(path)
        if not p.exists():
            raise TriggerError(f"Файл триггеров не найден: {p}")
        with p.open("r", encoding="utf-8") as f:
            data = json.load(f)

        if "triggers" not in data:
            raise TriggerError(f"В {p.name} нет ключа 'triggers'")

        triggers = []
        for raw in data["triggers"]:
            try:
                triggers.append(Trigger(**raw))
            except TypeError as e:
                raise TriggerError(f"Некорректный триггер {raw.get('id')!r}: {e}")
        return cls(triggers)

    @classmethod
    def load_default(cls, root: Optional[Path] = None) -> "TriggerEngine":
        """Ищет rules/wh40k_triggers.json относительно корня проекта."""
        if root is None:
            root = Path(__file__).resolve().parents[1]
        return cls.from_file(Path(root) / "rules" / "wh40k_triggers.json")

    # ---------- Основной метод ----------

    def fire(
        self,
        event: str,
        state: CharacterState,
        *,
        rng=None,
    ) -> list[TriggerResult]:
        """
        Найти все триггеры на событие event, проверить условия, применить эффекты.
        Возвращает список сработавших триггеров (в порядке из JSON).
        """
        results: list[TriggerResult] = []

        for trig in self.triggers:
            if trig.event != event:
                continue
            if not self._conditions_pass(trig.conditions, state):
                continue

            applied: list[dict] = []
            for raw_effect in trig.effects:
                effect = dict(raw_effect)
                effect["value"] = self._resolve_value(effect.get("value"), rng)
                rec = state.apply_effect(effect)
                applied.append(rec)

            results.append(
                TriggerResult(
                    trigger_id=trig.id,
                    event=trig.event,
                    message=trig.message,
                    description=trig.description,
                    effects_applied=applied,
                    fatal=trig.fatal,
                )
            )

        return results

    def events(self) -> list[str]:
        """Список всех событий, на которые есть триггеры."""
        return sorted({t.event for t in self.triggers})

    # ---------- Внутренние ----------

    @staticmethod
    def _resolve_value(value: Any, rng) -> Any:
        """Если value — строка вроде '1d5', бросить кубик. Иначе вернуть как есть."""
        if not isinstance(value, str):
            return value
        # Простейшая проверка, что это dice-выражение
        if "d" in value.lower():
            _rolls, _mod, total = roll_dice(value, rng)
            return total
        return value

    def _conditions_pass(
        self,
        conditions: list[dict],
        state: CharacterState,
    ) -> bool:
        for c in conditions:
            try:
                path = c["path"]
                op = c["op"]
                expected = c["value"]
            except KeyError as e:
                raise TriggerError(f"Условие без обязательного поля: {c} ({e})")

            actual = state.get(path)
            if not self._compare(actual, op, expected):
                return False
        return True

    @staticmethod
    def _compare(actual: Any, op: str, expected: Any) -> bool:
        if op == "==":
            return actual == expected
        if op == "!=":
            return actual != expected
        if op == ">":
            return actual is not None and actual > expected
        if op == ">=":
            return actual is not None and actual >= expected
        if op == "<":
            return actual is not None and actual < expected
        if op == "<=":
            return actual is not None and actual <= expected
        if op == "in":
            return actual in expected
        if op == "not_in":
            return actual not in expected
        if op == "contains":
            return actual is not None and expected in actual
        raise TriggerError(f"Неизвестный оператор: {op!r}")


def apply_triggers(
    event: str,
    state: CharacterState,
    engine: Optional[TriggerEngine] = None,
    *,
    rng=None,
) -> list[TriggerResult]:
    """
    Удобная обёртка: если движок не передан — берёт дефолтный.
    """
    if engine is None:
        engine = TriggerEngine.load_default()
    return engine.fire(event, state, rng=rng)