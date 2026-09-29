# PATCH_24A
"""services/effects.py — Страх, Безумие, Порча, Травмы."""
from __future__ import annotations
from datetime import datetime

FEAR_LABELS = {1: "Лёгкий", 2: "Заметный", 3: "Сильный", 4: "Ужасающий"}


def add_insanity(char: dict, amount: int, reason: str = "") -> None:
    if not isinstance(char, dict):
        return
    char["insanity"] = max(0, min(100,
        int(char.get("insanity", 0) or 0) + int(amount)))
    if reason:
        char.setdefault("effects_log", []).append({
            "type": "insanity", "delta": int(amount), "reason": reason,
            "ts": datetime.now().isoformat(timespec="seconds")})


def add_corruption(char: dict, amount: int, reason: str = "") -> None:
    if not isinstance(char, dict):
        return
    char["corruption"] = max(0, min(100,
        int(char.get("corruption", 0) or 0) + int(amount)))
    if reason:
        char.setdefault("effects_log", []).append({
            "type": "corruption", "delta": int(amount), "reason": reason,
            "ts": datetime.now().isoformat(timespec="seconds")})


def add_injury(char, name, stat, penalty, source=""):
    if not isinstance(char, dict):
        return
    inj = char.setdefault("injuries", [])
    if not isinstance(inj, list):
        inj = []
        char["injuries"] = inj
    inj.append({"name": name, "stat": stat, "penalty": int(penalty),
                "source": source,
                "ts": datetime.now().isoformat(timespec="seconds")})


def remove_injury(char, index):
    inj = char.get("injuries")
    if not isinstance(inj, list) or index < 0 or index >= len(inj):
        return False
    inj.pop(index)
    return True


INJURY_TABLE = [
    (1,   "Лёгкая контузия",       "Per", -5),
    (15,  "Рассечение",            "Fel", -5),
    (30,  "Ушиб руки",             "WS", -5),
    (45,  "Помятое плечо",         "BS", -5),
    (60,  "Сломано ребро",         "T",  -5),
    (75,  "Вывих лодыжки",         "Ag", -10),
    (90,  "Тяжёлая травма головы", "Int", -10),
    (100, "Увечье",                "T",  -15),
]


def roll_injury(rng=None):
    import random
    r = rng or random
    roll = r.randint(1, 100)
    for cap, name, stat, pen in INJURY_TABLE:
        if roll <= cap:
            return name, stat, pen
    return "Увечье", "T", -15


def effects_summary(char: dict) -> str:
    if not isinstance(char, dict):
        return "—"
    parts = []
    ins = int(char.get("insanity", 0) or 0)
    cor = int(char.get("corruption", 0) or 0)
    fear = int(char.get("fear_rating", 0) or 0)
    inj = char.get("injuries") or []
    if ins:
        parts.append("Безумие: " + str(ins))
    if cor:
        parts.append("Порча: " + str(cor))
    if fear:
        parts.append("Страх: " + str(fear)
                     + " (" + FEAR_LABELS.get(fear, "?") + ")")
    if inj:
        names = [str(i.get("name")) for i in inj[:5] if isinstance(i, dict)]
        parts.append("Травмы: " + ", ".join(names))
    return "; ".join(parts) if parts else "—"
