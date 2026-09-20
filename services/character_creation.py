"""services/character_creation.py — генерация характеристик и сборка листа."""
from __future__ import annotations

import random
from datetime import datetime

from services.fallbacks import (
    CHARACTERISTIC_KEYS,
    DEFAULT_ARCHETYPE,
    FACTIONS,
    REPUTATION_FACTIONS,
    SUBFACTION_FALLBACKS,
    SUBFACTION_NAMES,
    ULTIMATE_FALLBACK,
)


def roll_characteristics(rng: random.Random | None = None) -> dict[str, int]:
    """2d10 + 25 для каждой характеристики."""
    r = rng or random.Random()
    return {key: r.randint(1, 10) + r.randint(1, 10) + 25
            for key in CHARACTERISTIC_KEYS}


def _fallback_for(subfaction_id: str) -> dict:
    return SUBFACTION_FALLBACKS.get(subfaction_id, ULTIMATE_FALLBACK)


def build_character(
    *,
    name: str,
    gender: str,
    age: str,
    appearance: str,
    user_background: str,
    faction_id: str,
    subfaction_id: str,
    archetype_id: str | None = None,
    characteristics: dict[str, int] | None = None,
) -> dict:
    """Собрать полный лист персонажа в формате, ожидаемом движком."""
    if faction_id not in FACTIONS:
        raise ValueError(f"Неизвестная фракция: {faction_id}")

    faction = FACTIONS[faction_id]
    if subfaction_id not in faction["subfactions"]:
        raise ValueError(f"Сабфракция {subfaction_id!r} не принадлежит {faction_id!r}")

    archetype_id = archetype_id or DEFAULT_ARCHETYPE.get(faction_id, "captain")
    stats = characteristics or roll_characteristics()
    fb = _fallback_for(subfaction_id)

    now = datetime.now().isoformat(timespec="microseconds")
    wounds_max = fb.get("wounds", ULTIMATE_FALLBACK["wounds"])
    fate_max = fb.get("fate", ULTIMATE_FALLBACK["fate"])

    return {
        "name": name,
        "gender": gender,
        "age": age,
        "appearance": appearance,
        "user_background": user_background,
        "background": user_background or "(не задано)",
        "faction": faction["name"],
        "faction_id": faction_id,
        "subfaction": SUBFACTION_NAMES.get(subfaction_id, subfaction_id),
        "subfaction_id": subfaction_id,
        "archetype": archetype_id,
        "archetype_id": archetype_id,
        "extra_choices": {},
        "characteristics": stats,
        "bonuses": {k: 0 for k in CHARACTERISTIC_KEYS},
        "skills": [],
        "talents": list(fb.get("talents", [])),
        "weapons": [dict(w) for w in fb.get("weapons", [])],
        "equipment": list(fb.get("equipment", [])),
        "armour": dict(fb.get("armour", ULTIMATE_FALLBACK["armour"])),
        "wounds": {"current": wounds_max, "max": wounds_max},
        "fate_points": {"current": fate_max, "max": fate_max},
        "psy_rating": 0,
        "psychic_powers": [],
        "corruption": 0,
        "insanity": 0,
        "money": 200,
        "currency": "Троны",
        "special_resources": {},
        "extra_currencies": {},
        "ship": {
            "name": "", "class": "", "type": "", "description": "",
            "hull": "", "crew": "", "weapons": [], "features": [],
            "status": "",
        },
        "location": "",
        "game_date": "Начало приключения",
        "quests": [], "npcs": [], "effects": [], "companions": [],
        "goals": [], "journal": [], "notes": "",
        "reputation": {f: 0 for f in REPUTATION_FACTIONS},
        "generation_method": "roll",
        "xp": 0,
        "rank": 1,
        "created_at": now,
    }
