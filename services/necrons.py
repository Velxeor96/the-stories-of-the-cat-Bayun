# PATCH_40
"""services/necrons.py — загрузка и обработка данных Некронов."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[1]
NECRONS_FILE = ROOT / "data" / "necrons.json"

_CACHE: Optional[dict] = None


def load() -> dict:
    """Загружает и кеширует данные Некронов."""
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if not NECRONS_FILE.exists():
        print("[necrons] файл не найден: " + str(NECRONS_FILE))
        _CACHE = {}
        return _CACHE
    try:
        _CACHE = json.loads(NECRONS_FILE.read_text(encoding="utf-8"))
        print("[necrons] загружено: архетипов=" + str(len(_CACHE.get("archetypes", [])))
              + ", талантов=" + str(len(_CACHE.get("talents", [])))
              + ", оружия=" + str(len(_CACHE.get("weapons", [])))
              + ", кораблей=" + str(len(_CACHE.get("ships", []))))
    except Exception as e:
        print("[necrons] ошибка загрузки: " + str(e))
        _CACHE = {}
    return _CACHE


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


def get_weapons() -> list:
    return load().get("weapons", [])


def get_weapon(weapon_id: str) -> Optional[dict]:
    for w in get_weapons():
        if w.get("id") == weapon_id:
            return w
    return None


def get_armour() -> list:
    return load().get("armour", [])


def get_armour_item(armour_id: str) -> Optional[dict]:
    for a in get_armour():
        if a.get("id") == armour_id:
            return a
    return None


def get_equipment() -> list:
    return load().get("equipment", [])


def get_equipment_item(item_id: str) -> Optional[dict]:
    for e in get_equipment():
        if e.get("id") == item_id:
            return e
    return None


def get_ships() -> list:
    return load().get("ships", [])


def get_ship(ship_id: str) -> Optional[dict]:
    for s in get_ships():
        if s.get("id") == ship_id:
            return s
    return None


def get_mechanics() -> list:
    return load().get("mechanics", [])


def check_talent_prerequisites(char: dict, talent_id: str) -> tuple:
    """Проверяет, может ли персонаж купить талант.
    Возвращает (ok: bool, reason: str)."""
    talent = get_talent(talent_id)
    if not talent:
        return False, "Талант не найден."

    prereqs = talent.get("prerequisites", {}) or {}

    # Проверка ранга
    rank_min = prereqs.get("rank")
    if rank_min is not None:
        rank = int(char.get("rank", 1) or 1)
        if rank < rank_min:
            return False, "Требуется ранг " + str(rank_min) + "."

    # Проверка характеристик
    chars = char.get("characteristics", {}) or {}
    for key, val in prereqs.items():
        if key in ("rank", "talent"):
            continue
        if key in ("WS", "BS", "S", "T", "Ag", "Int", "Per", "WP", "Fel"):
            current = int(chars.get(key, 0) or 0)
            if current < int(val):
                return False, key + " должен быть не менее " + str(val) + "."

    # Проверка требуемого таланта
    req_talent = prereqs.get("talent")
    if req_talent:
        player_talents = char.get("talents", []) or []
        # player_talents может быть списком строк или список словарей
        names = []
        for t in player_talents:
            if isinstance(t, dict):
                names.append(t.get("id") or t.get("name", ""))
            else:
                names.append(str(t))
        if req_talent not in names and get_talent(req_talent) and \
           get_talent(req_talent).get("name") not in names:
            return False, "Требуется талант: " + str(req_talent)

    # Проверка требуемого навыка (если указан как строка)
    for key, val in prereqs.items():
        if key in ("rank", "talent"):
            continue
        if key in ("WS", "BS", "S", "T", "Ag", "Int", "Per", "WP", "Fel"):
            continue
        # Остальные ключи считаем навыками
        skills = char.get("skills", []) or []
        skill_names = []
        for s in skills:
            if isinstance(s, dict):
                skill_names.append(s.get("name", ""))
            else:
                skill_names.append(str(s))
        if key not in skill_names:
            return False, "Требуется навык: " + str(key)

    return True, ""


def can_afford(char: dict, talent_id: str) -> tuple:
    """Проверяет, хватает ли XP на талант.
    Возвращает (ok: bool, cost: int, xp: int)."""
    talent = get_talent(talent_id)
    if not talent:
        return False, 0, 0
    cost = int(talent.get("cost", 0))
    xp = int(char.get("xp", 0) or 0)
    return xp >= cost, cost, xp


def buy_talent(char: dict, talent_id: str) -> tuple:
    """Покупает талант за XP. Возвращает (ok: bool, message: str)."""
    talent = get_talent(talent_id)
    if not talent:
        return False, "Талант не найден."

    # Проверка, не куплен ли уже
    player_talents = char.get("talents", []) or []
    for t in player_talents:
        if isinstance(t, dict):
            if t.get("id") == talent_id or t.get("name") == talent.get("name"):
                return False, "Талант уже куплен."
        elif str(t) == talent.get("name"):
            return False, "Талант уже куплен."

    # Проверка требований
    ok, reason = check_talent_prerequisites(char, talent_id)
    if not ok:
        return False, reason

    # Проверка XP
    ok, cost, xp = can_afford(char, talent_id)
    if not ok:
        return False, "Недостаточно XP. Нужно " + str(cost) + ", есть " + str(xp) + "."

    # Покупка
    char["xp"] = xp - cost
    char["xp_spent"] = int(char.get("xp_spent", 0) or 0) + cost
    talents = char.setdefault("talents", [])
    talents.append({
        "id": talent_id,
        "name": talent.get("name", talent_id),
        "effect": talent.get("effect", "")
    })
    return True, "Талант «" + str(talent.get("name")) + "» куплен за " + str(cost) + " XP."


def apply_archetype_to_character(char: dict, archetype_id: str) -> dict:
    """Применяет архетип Некрона к персонажу: бонусы, оружие, броня."""
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
                "name": w.get("name"),
                "stats": w.get("damage", "") + " " + w.get("special", "")
            })

    # Броня
    arm_id = arch.get("starting_armour")
    if arm_id:
        arm = get_armour_item(arm_id)
        if arm:
            ap = arm.get("all_ap", 6)
            char["armour"] = {
                "head": ap, "body": ap, "arms": ap, "legs": ap,
                "notes": arm.get("name", "Некродермис")
            }

    # Трейты фракции — добавляем пометки
    char["necron_traits"] = list(get_faction_traits().keys())
    char["archetype_id"] = archetype_id
    char["archetype"] = arch.get("name")

    return char


if __name__ == "__main__":
    data = load()
    print("Архетипы:")
    for a in get_archetypes():
        print("  -", a["id"], "|", a["name"])
    print("Таланты по категориям:")
    for cat in ("combat", "defense", "utility", "technical", "social", "leadership"):
        ts = get_talents_by_category(cat)
        if ts:
            print("  " + cat + ": " + str(len(ts)))
    print("Оружия:", len(get_weapons()))
    print("Брони:", len(get_armour()))
    print("Кораблей:", len(get_ships()))

# === PATCH_43: расширенные данные (дедуп в PATCH_88) ===
# === PATCH_43: расширенные данные ===
import json as _json

_NECRONS_WEAPONS_FILE = ROOT / "data" / "necrons_weapons.json"
_NECRONS_ARMOUR_FILE = ROOT / "data" / "necrons_armour.json"
_NECRONS_FLEET_FILE = ROOT / "data" / "necrons_fleet.json"

_EXT_CACHE = {}


def _load_ext(path):
    if path.name in _EXT_CACHE:
        return _EXT_CACHE[path.name]
    if not path.exists():
        _EXT_CACHE[path.name] = {}
        return {}
    try:
        data = _json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        print("[necrons] " + path.name + ": " + str(e))
        data = {}
    _EXT_CACHE[path.name] = data
    return data


def get_weapons_extended():
    return _load_ext(_NECRONS_WEAPONS_FILE).get("weapons", [])


def get_armour_extended():
    return _load_ext(_NECRONS_ARMOUR_FILE).get("armour", [])


def get_equipment_extended():
    return _load_ext(_NECRONS_ARMOUR_FILE).get("equipment", [])


def get_fleet():
    return _load_ext(_NECRONS_FLEET_FILE)


def get_hulls():
    return get_fleet().get("hulls", [])


def get_ship_weapons():
    return get_fleet().get("weapons", [])


def get_ship_components():
    return get_fleet().get("components", [])


# PATCH_88: алиас для совместимости с внешним кодом
def get_components():
    return get_ship_components()
