# PATCH_36
"""services/character_creation.py — генерация и сборка листа по фракции."""
from __future__ import annotations
import random
from datetime import datetime

from services.fallbacks import (
    CHARACTERISTIC_KEYS, FACTIONS, REPUTATION_FACTIONS,
    SUBFACTION_NAMES,
)
from services.faction_starting import (
    get_starting_kit, get_home_world_bonuses, get_career_bonuses,
)


def roll_pool(rng=None):
    r = rng or random.Random()
    return [r.randint(1, 10) + r.randint(1, 10) + 20 for _ in range(9)]


def roll_characteristics(rng=None):
    pool = roll_pool(rng)
    return {k: v for k, v in zip(CHARACTERISTIC_KEYS, pool)}


def auto_distribute(pool):
    ordered = sorted(pool)
    return {k: ordered[i] for i, k in enumerate(CHARACTERISTIC_KEYS)}


def _apply_bonuses(stats, bonus, penalty):
    result = dict(stats)
    for k, v in (bonus or {}).items():
        if k in result:
            result[k] = int(result[k]) + int(v)
    for k, v in (penalty or {}).items():
        if k in result:
            result[k] = int(result[k]) - int(v)
    return result


def _safe_display(fn_name, faction_id, key):
    try:
        from services import fallbacks as _fb
        fn = getattr(_fb, fn_name, None)
        if fn and key:
            return fn(faction_id, key)
    except Exception:
        pass
    return key or ""


def build_character(
    *, name, gender, age, appearance, user_background,
    faction_id, subfaction_id=None,
    home_world_id=None, career_id=None,
    characteristics=None,
):
    if faction_id not in FACTIONS:
        raise ValueError("Неизвестная фракция: " + str(faction_id))

    # 1) Базовые характеристики
    base = characteristics or roll_characteristics()

    # 2) Названия родного мира и карьеры
    hw_name = _safe_display("home_world_display_name", faction_id, home_world_id)
    cr_name = _safe_display("career_display_name", faction_id, career_id)

    # 3) Бонусы от родного мира и карьеры
    hw_b = get_home_world_bonuses(faction_id, hw_name)
    cr_b = get_career_bonuses(faction_id, cr_name)
    stats = _apply_bonuses(base, hw_b["bonus"], hw_b["penalty"])
    stats = _apply_bonuses(stats, cr_b["bonus"], cr_b["penalty"])

    # 4) Стартовый набор
    kit = get_starting_kit(faction_id)
    weapons = [dict(w) for w in kit.get("weapons", [])]
    armour = dict(kit.get("armour", {"head": 4, "body": 4,
                                      "arms": 4, "legs": 4,
                                      "notes": "Стандарт"}))
    equipment = list(kit.get("equipment", []))
    talents = list(kit.get("talents", []))
    skills = list(kit.get("skills", []))

    # 5) Раны и судьба
    tb = stats.get("T", 30) // 10
    wounds_max = random.randint(1, 5) + 1 + 2 * tb
    fate_max = 2 if random.randint(1, 10) >= 8 else 1

    # 6) Субфракция
    faction = FACTIONS[faction_id]
    sub_key = subfaction_id or (faction.get("subfactions") or [None])[0]
    if sub_key and sub_key not in faction.get("subfactions", []):
        sub_key = None
    sub_display = SUBFACTION_NAMES.get(sub_key, sub_key or "")

    now = datetime.now().isoformat(timespec="microseconds")

    return {
        "name": name, "gender": gender, "age": age,
        "appearance": appearance,
        "user_background": user_background,
        "background": user_background or "(не задано)",
        "faction": faction["name"], "faction_id": faction_id,
        "subfaction": sub_display, "subfaction_id": sub_key or "",
        "home_world_id": home_world_id or "",
        "home_world_name": hw_name,
        "career_id": career_id or "",
        "career_name": cr_name,
        "archetype": career_id or "",
        "archetype_id": career_id or "",
        "extra_choices": {},
        "characteristics": stats,
        "bonuses": {k: 0 for k in CHARACTERISTIC_KEYS},
        "skills": skills,
        "talents": talents,
        "weapons": weapons,
        "equipment": equipment,
        "armour": armour,
        "wounds": {"current": wounds_max, "max": wounds_max},
        "fate_points": {"current": fate_max, "max": fate_max},
        "psy_rating": 2 if faction_id == "eldar" and "Провидца" in cr_name else 0,
        "psychic_powers": [],
        "corruption": 0, "insanity": 0,
        "money": int(kit.get("money", 100) or 100),
        "currency": kit.get("currency", "Троны"),
        "special_resources": {},
        "extra_currencies": {},
        "ship": {"name": "", "class": "", "type": "", "description": "",
                 "hull": "", "crew": "", "weapons": [], "features": [],
                 "status": ""},
        "location": "", "game_date": "Начало приключения",
        "quests": [], "npcs": [], "effects": [], "companions": [],
        "goals": [], "journal": [], "notes": "",
        "player_notes": [],
        "reputation": {f: 0 for f in REPUTATION_FACTIONS},
        "generation_method": "roll+distribute",
        "xp": 300, "rank": 1, "created_at": now,
    }
