# PATCH_46
"""services/character_creation.py — генерация листа по фракции."""
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


def _build_alien_character(stats, faction_id, career_id):
    """
    Применяет архетип для некронов или тиранидов.
    Возвращает dict с полями: skills, talents, weapons, armour,
    money, currency, traits, archetype_name, wounds_bonus.
    """
    out = {
        "skills": [], "talents": [], "weapons": [], "armour": {},
        "money": 0, "currency": "Нет",
        "traits": [], "archetype_name": career_id or "",
        "wounds_bonus": 0,
    }

    src = None
    if faction_id == "necrons":
        try:
            from services import necrons as src
        except Exception as e:
            print("[creation] necrons import: " + str(e))
    elif faction_id == "tyranids":
        try:
            from services import tyranids as src
        except Exception as e:
            print("[creation] tyranids import: " + str(e))

    if src is None:
        return out

    try:
        arch = src.get_archetype(career_id or "")
    except Exception:
        arch = None

    if not arch:
        return out

    out["archetype_name"] = arch.get("name", career_id or "")

    # Бонусы к характеристикам
    bonus = arch.get("bonus_characteristics", {}) or {}
    for k, v in bonus.items():
        if k in stats:
            stats[k] = int(stats[k]) + int(v)

    # Навыки
    out["skills"] = list(arch.get("starting_skills", []))

    # Таланты
    for t_id in arch.get("starting_talents", []):
        t_obj = None
        try:
            t_obj = src.get_talent(t_id)
        except Exception:
            pass
        out["talents"].append({
            "id": t_id,
            "name": (t_obj or {}).get("name", t_id)
        })

    # Оружие
    for w_id in arch.get("starting_weapons", []):
        try:
            w = src.get_weapon(w_id)
        except Exception:
            w = None
        if w:
            out["weapons"].append({
                "id": w_id,
                "name": w.get("name", w_id),
                "stats": w.get("damage", "") + " · " + w.get("special", "")
            })
        else:
            out["weapons"].append({"id": w_id, "name": w_id, "stats": ""})

    # Броня
    arm_id = arch.get("starting_armour", "")
    if arm_id:
        try:
            arm = src.get_armour_item(arm_id)
        except Exception:
            arm = None
        if arm:
            ap = arm.get("all_ap", 8)
            out["armour"] = {
                "head": ap, "body": ap, "arms": ap, "legs": ap,
                "notes": arm.get("name", "Карапас")
            }

    # Трейты
    try:
        out["traits"] = list(src.get_faction_traits().keys())
    except Exception:
        pass

    # Wounds bonus
    out["wounds_bonus"] = int(arch.get("wounds_bonus", 0) or 0)

    return out


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

    # 2) Названия
    hw_name = _safe_display("home_world_display_name", faction_id, home_world_id)
    cr_name = _safe_display("career_display_name", faction_id, career_id)

    # 3) Бонусы от мира/карьеры (для не-ксенов)
    hw_b = get_home_world_bonuses(faction_id, hw_name)
    cr_b = get_career_bonuses(faction_id, cr_name)
    stats = _apply_bonuses(base, hw_b["bonus"], hw_b["penalty"])
    stats = _apply_bonuses(stats, cr_b["bonus"], cr_b["penalty"])

    # 4) Стартовый набор
    weapons = []
    armour = {"head": 4, "body": 4, "arms": 4, "legs": 4, "notes": "Стандарт"}
    equipment = []
    talents = []
    skills = []
    money = 100
    currency = "Троны"
    wounds_bonus_extra = 0
    faction_traits = []

    # PATCH_64: бонусы архетипа для всех субфракций с сервисом
    _arch_service_map = {
        "imperial_guard": "services.imperial_guard",
        "mechanicus":     "services.mechanicus",
        "inquisition":    "services.inquisition",
        "sororitas":      "services.sororitas",
        "space_marine":   "services.space_marines",
        "arbites":        "services.arbites",
    }
    _kit_key = subfaction_id if subfaction_id else faction_id
    _arch_key = _kit_key if _kit_key in _arch_service_map else None
    if _arch_key:
        try:
            _mod = __import__(_arch_service_map[_arch_key],
                              fromlist=["get_archetype"])
            _arch = _mod.get_archetype(career_id or "")
        except Exception as _e:
            print("[build_character] archetype: " + type(_e).__name__)
            _arch = None
        if _arch:
            for _k, _v in (_arch.get("bonus_characteristics", {}) or {}).items():
                if _k in stats:
                    stats[_k] = int(stats[_k]) + int(_v)

    if faction_id in ("necrons", "tyranids"):
        alien = _build_alien_character(dict(stats), faction_id, career_id)
        # Переписываем stats на изменённые
        for k in list(stats.keys()):
            stats[k] = int(stats[k])
        # Но _build_alien_character менял свою копию — поэтому применяем заново
        stats = dict(base)
        stats = _apply_bonuses(stats, hw_b["bonus"], hw_b["penalty"])
        stats = _apply_bonuses(stats, cr_b["bonus"], cr_b["penalty"])
        # Теперь с архетипом:
        arch = None
        if faction_id == "necrons":
            try:
                from services.necrons import get_archetype
                arch = get_archetype(career_id or "")
            except Exception:
                pass
        else:
            try:
                from services.tyranids import get_archetype
                arch = get_archetype(career_id or "")
            except Exception:
                pass
        if arch:
            for k, v in (arch.get("bonus_characteristics", {}) or {}).items():
                if k in stats:
                    stats[k] = int(stats[k]) + int(v)

        skills = alien["skills"]
        talents = alien["talents"]
        weapons = alien["weapons"]
        armour = alien["armour"] or armour
        faction_traits = alien["traits"]
        wounds_bonus_extra = alien["wounds_bonus"]
        if faction_id == "necrons":
            money = 0
            currency = "Нет"
            equipment = ["resurrection_orb"]
        else:
            money = 0
            currency = "Нет"
            equipment = ["adrenal_gland"]
    else:
        kit = get_starting_kit(_kit_key)
        weapons = [dict(w) for w in kit.get("weapons", [])]
        armour = dict(kit.get("armour", armour))
        equipment = list(kit.get("equipment", []))
        talents = [{"id": t, "name": t} for t in kit.get("talents", [])]
        skills = list(kit.get("skills", []))
        money = int(kit.get("money", 100) or 100)
        currency = kit.get("currency", "Троны")

    # 5) Раны и судьба
    tb = stats.get("T", 30) // 10
    wounds_max = random.randint(1, 5) + 1 + 2 * tb + wounds_bonus_extra
    fate_max = 2 if random.randint(1, 10) >= 8 else 1

    # 6) Субфракция
    faction = FACTIONS[faction_id]
    sub_key = subfaction_id
    if sub_key and sub_key not in faction.get("subfactions", []):
        sub_key = None
    sub_display = SUBFACTION_NAMES.get(sub_key, sub_key or "")

    # 7) Архетип
    archetype_id = career_id if faction_id in ("necrons", "tyranids") else None
    if archetype_id:
        try:
            if faction_id == "necrons":
                from services.necrons import get_archetype
            else:
                from services.tyranids import get_archetype
            arch = get_archetype(archetype_id) or {}
            cr_name = arch.get("name", cr_name)
        except Exception:
            pass

    now = datetime.now().isoformat(timespec="microseconds")

    _has_ship = bool(
        (faction_id == "imperium" and subfaction_id == "rogue_trader")
        or subfaction_id == "rogue_trader"
    )

    char = {  # PATCH_59: has_ship
        "has_ship": _has_ship,
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
        "archetype": archetype_id or "",
        "archetype_id": archetype_id or "",
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
        "psy_rating": 0,
        "psychic_powers": [],
        "corruption": 0, "insanity": 0,
        "money": money, "currency": currency,
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
        "alien_traits": faction_traits,
        "necron_traits": faction_traits if faction_id == "necrons" else [],
        "tyranid_traits": faction_traits if faction_id == "tyranids" else [],
    }

    # PATCH_87: авто-инициализация психосил по архетипу
    try:
        from services.psy_archetypes import ensure_psy_fields
        ensure_psy_fields(char)
        # Если у псайкера есть psy_rating, но не заданы силы —
        # дадим стартовый набор доступных ему сил.
        _pr = int(char.get("psy_rating", 0) or 0)
        if _pr > 0 and not char.get("psychic_powers"):
            try:
                from services import psychic as _psy
                _powers = _psy.get_powers(char) or []
                char["psychic_powers"] = list(_powers)[:5]
                char["psy_charge"] = _pr * 3
            except Exception as _e:
                print("[creation] psy powers: " + type(_e).__name__)
    except Exception as _e:
        print("[creation] ensure_psy_fields: " + type(_e).__name__)

    return char
