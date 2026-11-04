"""services/character_creation.py — генерация листа по фракции.

DLC-совместимая архитектура:
  - Для имперских фракций стартовый кит идёт через services.faction_starting.
  - Для alien-фракций (некроны, тираниды, любые будущие) модуль
    services.<faction_id> должен предоставить get_archetype / get_weapon /
    get_armour_item / get_faction_traits, либо собственный build_starting_kit().
    Диспетчер подхватит его автоматически — правки здесь не нужны.
  - Активация фракции — добавьте id в _ACTIVE_FACTIONS (и в _ALLOWED_FACTIONS
    в ui/screens/wizard.py).
"""
from __future__ import annotations

import importlib
import random
from datetime import datetime

from services.fallbacks import (
    CHARACTERISTIC_KEYS, FACTIONS, REPUTATION_FACTIONS, SUBFACTION_NAMES,
)
from services.faction_starting import (
    get_starting_kit, get_home_world_bonuses, get_career_bonuses,
)


# Активные фракции. DLC добавляет сюда свои id.
_ACTIVE_FACTIONS = {"imperium", "eldar", "tau", "necrons", "tyranids"}

# Имперские субфракции, у которых есть свой сервис с архетипами.
_IMPERIAL_ARCH_SERVICES = {
    "imperial_guard": "services.imperial_guard",
    "mechanicus": "services.mechanicus",
    "inquisition": "services.inquisition",
    "sororitas": "services.sororitas",
    "space_marine": "services.space_marines",
    "arbites": "services.arbites",
}


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


def _get_alien_kit_builder(faction_id):
    """Возвращает callable(career_id) -> kit_dict для alien-фракции, или None.

    Приоритет:
      1) если модуль реализует build_starting_kit — используем его;
      2) иначе — generic-сборка через services._alien_kit.build_kit().
    """
    try:
        mod = importlib.import_module("services." + str(faction_id))
    except Exception:
        return None

    if hasattr(mod, "build_starting_kit"):
        def _from_module(career_id, _mod=mod, _fid=faction_id):
            return _mod.build_starting_kit(career_id, _fid)
        return _from_module

    required = ("get_archetype", "get_weapon", "get_armour_item", "get_faction_traits")
    if not all(hasattr(mod, fn) for fn in required):
        return None

    from services._alien_kit import build_kit

    def _from_generic(career_id, _mod=mod, _fid=faction_id):
        return build_kit(_mod, career_id, _fid)
    return _from_generic


def build_character(
    *, name, gender, age, appearance, user_background,
    faction_id, subfaction_id=None,
    home_world_id=None, career_id=None, archetype_id=None,
    characteristics=None,
):
    if archetype_id and not career_id:
        career_id = archetype_id
    if faction_id not in FACTIONS:
        raise ValueError("Неизвестная фракция: " + str(faction_id))

    if faction_id not in _ACTIVE_FACTIONS:
        raise ValueError(
            "Фракция '" + str(faction_id) + "' пока недоступна. "
            "Сейчас играбелен только Империум (модуль Rogue Trader)."
        )

    base = characteristics or roll_characteristics()

    hw_name = _safe_display("home_world_display_name", faction_id, home_world_id)
    cr_name = _safe_display("career_display_name", faction_id, career_id)

    hw_b = get_home_world_bonuses(faction_id, hw_name)
    cr_b = get_career_bonuses(faction_id, cr_name)
    stats = _apply_bonuses(base, hw_b["bonus"], hw_b["penalty"])
    stats = _apply_bonuses(stats, cr_b["bonus"], cr_b["penalty"])

    weapons = []
    armour = {"head": 4, "body": 4, "arms": 4, "legs": 4, "notes": "Стандарт"}
    equipment = []
    talents = []
    skills = []
    money = 100
    currency = "Троны"
    wounds_bonus_extra = 0
    faction_traits = []

    # Бонусы архетипа для имперских субфракций
    _kit_key = subfaction_id if subfaction_id else faction_id
    _arch_key = _kit_key if _kit_key in _IMPERIAL_ARCH_SERVICES else None
    if _arch_key:
        try:
            _mod = importlib.import_module(_IMPERIAL_ARCH_SERVICES[_arch_key])
            _arch = _mod.get_archetype(career_id or "")
        except Exception as _e:
            print("[build_character] archetype: " + type(_e).__name__)
            _arch = None
        if _arch:
            for _k, _v in (_arch.get("bonus_characteristics", {}) or {}).items():
                if _k in stats:
                    stats[_k] = int(stats[_k]) + int(_v)

    # Alien-фракции через диспетчер. Никаких хардкодов necrons/tyranids —
    # любая будущая DLC-фракция подхватится, если модуль реализует интерфейс.
    alien_builder = _get_alien_kit_builder(faction_id) if faction_id != "imperium" else None
    if alien_builder is not None:
        alien = alien_builder(career_id) or {}
        for k, v in (alien.get("bonus_characteristics") or {}).items():
            if k in stats:
                stats[k] = int(stats[k]) + int(v)
        skills = list(alien.get("skills") or [])
        talents = list(alien.get("talents") or [])
        weapons = list(alien.get("weapons") or [])
        armour = alien.get("armour") or armour
        equipment = list(alien.get("equipment") or []) or equipment
        faction_traits = list(alien.get("traits") or [])
        wounds_bonus_extra = int(alien.get("wounds_bonus", 0) or 0)
        money = int(alien.get("money", 0) or 0)
        currency = alien.get("currency", "Нет")
        if alien.get("archetype_name"):
            cr_name = alien["archetype_name"]
    else:
        kit = get_starting_kit(_kit_key)
        weapons = [dict(w) for w in kit.get("weapons", [])]
        armour = dict(kit.get("armour", armour))
        equipment = list(kit.get("equipment", []))
        talents = [{"id": t, "name": t} for t in kit.get("talents", [])]
        skills = list(kit.get("skills", []))
        money = int(kit.get("money", 100) or 100)
        currency = kit.get("currency", "Троны")

    tb = stats.get("T", 30) // 10
    wounds_max = random.randint(1, 5) + 1 + 2 * tb + wounds_bonus_extra
    fate_max = 2 if random.randint(1, 10) >= 8 else 1

    faction = FACTIONS[faction_id]
    sub_key = subfaction_id
    if sub_key and sub_key not in faction.get("subfactions", []):
        sub_key = None
    sub_display = SUBFACTION_NAMES.get(sub_key, sub_key or "")

    archetype_id_final = career_id if alien_builder is not None else None

    now = datetime.now().isoformat(timespec="microseconds")

    _has_ship = bool(
        (faction_id == "imperium" and subfaction_id == "rogue_trader")
        or subfaction_id == "rogue_trader"
    )

    char = {
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
        "archetype": archetype_id_final or "",
        "archetype_id": archetype_id_final or "",
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
        # Поля ниже — для обратной совместимости со старыми сохранениями
        # и кодом, который мог их читать. Заполняются только для своей фракции.
        "necron_traits": faction_traits if faction_id == "necrons" else [],
        "tyranid_traits": faction_traits if faction_id == "tyranids" else [],
    }

    try:
        from services.psy_archetypes import ensure_psy_fields
        ensure_psy_fields(char)
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
