# PATCH_45
"""services/tyranids.py — загрузка и обработка данных Тиранидов."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[1]
TYRANIDS_FILE = ROOT / "data" / "tyranids.json"
TYRANIDS_WEAPONS_FILE = ROOT / "data" / "tyranids_weapons.json"
TYRANIDS_ARMOUR_FILE = ROOT / "data" / "tyranids_armour.json"
TYRANIDS_FLEET_FILE = ROOT / "data" / "tyranids_fleet.json"

_CACHE = {}


def _load_json(path):
    key = path.name
    if key in _CACHE:
        return _CACHE[key]
    if not path.exists():
        print("[tyranids] " + key + " не найден")
        _CACHE[key] = {}
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        print("[tyranids] " + key + " error: " + str(e))
        data = {}
    _CACHE[key] = data
    return data


def load() -> dict:
    return _load_json(TYRANIDS_FILE)


def get_faction_traits() -> dict:
    return load().get("traits", {})


def get_archetypes() -> list:
    return load().get("archetypes", [])


def get_archetype(arch_id: str) -> Optional[dict]:
    for a in get_archetypes():
        if a.get("id") == arch_id:
            return a
    return None


def list_archetype_ids() -> list:
    return [a["id"] for a in get_archetypes()]


def get_talents() -> list:
    return load().get("talents", [])


def get_talent(talent_id: str) -> Optional[dict]:
    for t in get_talents():
        if t.get("id") == talent_id:
            return t
    return None


def get_talents_by_category(category: str) -> list:
    return [t for t in get_talents() if t.get("category") == category]


def get_talents_by_tier(tier: int) -> list:
    return [t for t in get_talents() if t.get("tier") == tier]


def get_weapons_extended() -> list:
    return _load_json(TYRANIDS_WEAPONS_FILE).get("weapons", [])


def get_armour_extended() -> list:
    return _load_json(TYRANIDS_ARMOUR_FILE).get("armour", [])


def get_equipment_extended() -> list:
    return _load_json(TYRANIDS_ARMOUR_FILE).get("equipment", [])


def get_fleet() -> dict:
    return _load_json(TYRANIDS_FLEET_FILE)


def get_hulls() -> list:
    return get_fleet().get("hulls", [])


def get_ship_weapons() -> list:
    return get_fleet().get("weapons", [])


def get_ship_components() -> list:
    return get_fleet().get("components", [])


def get_weapon(weapon_id: str) -> Optional[dict]:
    for w in get_weapons_extended():
        if w.get("id") == weapon_id:
            return w
    return None


def get_armour_item(armour_id: str) -> Optional[dict]:
    for a in get_armour_extended():
        if a.get("id") == armour_id:
            return a
    return None


def get_equipment_item(item_id: str) -> Optional[dict]:
    for e in get_equipment_extended():
        if e.get("id") == item_id:
            return e
    return None


def get_mechanics() -> list:
    return load().get("mechanics", [])


def apply_archetype_to_character(char: dict, archetype_id: str) -> dict:
    """Применяет архетип Тиранида к персонажу: бонусы, оружие, броня, трейты."""
    arch = get_archetype(archetype_id)
    if not arch:
        return char

    # Бонусы к характеристикам
    bonus = arch.get("bonus_characteristics", {}) or {}
    chars = char.setdefault("characteristics", {})
    for k, v in bonus.items():
        chars[k] = int(chars.get(k, 0) or 0) + int(v)

    # Wounds
    w_bonus = int(arch.get("wounds_bonus", 0) or 0)
    w = char.setdefault("wounds", {"current": 10, "max": 10})
    w["max"] = int(w.get("max", 10)) + w_bonus
    w["current"] = w["max"]

    # Навыки
    skills = char.setdefault("skills", [])
    for sk in arch.get("starting_skills", []):
        if sk not in skills:
            skills.append(sk)

    # Таланты
    talents = char.setdefault("talents", [])
    for t_id in arch.get("starting_talents", []):
        t_obj = get_talent(t_id)
        entry = {"id": t_id, "name": t_obj.get("name", t_id) if t_obj else t_id}
        if entry not in talents:
            talents.append(entry)

    # Оружие
    weapons = char.setdefault("weapons", [])
    for w_id in arch.get("starting_weapons", []):
        w = get_weapon(w_id)
        if w:
            weapons.append({
                "id": w_id,
                "name": w.get("name"),
                "stats": w.get("damage", "") + " · " + w.get("special", "")
            })

    # Броня
    arm_id = arch.get("starting_armour")
    if arm_id:
        arm = get_armour_item(arm_id)
        if arm:
            ap = arm.get("all_ap", 8)
            char["armour"] = {
                "head": ap, "body": ap, "arms": ap, "legs": ap,
                "notes": arm.get("name", "Карапас")
            }

    # Трейты фракции
    char["tyranid_traits"] = list(get_faction_traits().keys())
    char["archetype_id"] = archetype_id
    char["archetype"] = arch.get("name")

    return char


if __name__ == "__main__":
    data = load()
    print("Архетипы:")
    for a in get_archetypes():
        print("  -", a["id"], "|", a["name"])
    print("Таланты по категориям:")
    for cat in ("combat", "defense", "utility", "technical", "social", "leadership", "psychic"):
        ts = get_talents_by_category(cat)
        if ts:
            print("  " + cat + ": " + str(len(ts)))
    print("Оружия:", len(get_weapons_extended()))
    print("Брони:", len(get_armour_extended()))
    print("Снаряжения:", len(get_equipment_extended()))
    print("Кораблей:", len(get_hulls()))
    print("Орудий кораблей:", len(get_ship_weapons()))
    print("Компонентов:", len(get_ship_components()))
