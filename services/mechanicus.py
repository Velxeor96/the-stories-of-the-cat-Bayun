"""services/mechanicus.py — сервис субфракции Адептус Механикус."""
from __future__ import annotations
import json
from pathlib import Path

_DATA = None

def _load() -> dict:
    global _DATA
    if _DATA is None:
        p = Path(__file__).resolve().parent.parent / "data" / "mechanicus.json"
        _DATA = json.loads(p.read_text(encoding="utf-8"))
    return _DATA


def get_archetypes() -> list:
    return _load().get("archetypes", [])

def get_archetypes_by_type(t: str) -> list:
    return [a for a in get_archetypes() if a.get("type") == t]

def get_archetype(arch_id: str):
    for a in get_archetypes():
        if a["id"] == arch_id:
            return a
    return None

def get_talents() -> list:
    return _load().get("talents", [])

def get_talent(talent_id: str):
    for t in get_talents():
        if t.get("id") == talent_id:
            return t
    return None

def get_faction_meta() -> dict:
    d = _load()
    return {
        "id": d["faction_id"],
        "name": d["name"],
        "full_name": d.get("full_name", d["name"]),
        "description": d.get("description", ""),
    }

