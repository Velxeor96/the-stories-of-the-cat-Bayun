# PATCH_46
"""services/talents_registry.py — универсальный реестр талантов."""
from __future__ import annotations


# PATCH_50: универсальный реестр источников талантов
_TALENT_SOURCES = {
    "necrons":        "services.necrons",
    "tyranids":       "services.tyranids",
    "imperial_guard": "services.imperial_guard",
    "mechanicus":     "services.mechanicus",
    "inquisition":    "services.inquisition",
    "sororitas":      "services.sororitas",
    "space_marine":   "services.space_marines",
    "arbites":        "services.arbites",
}


def _source_for(faction_id: str):
    """Возвращает модуль-источник талантов для фракции."""
    mod_name = _TALENT_SOURCES.get(faction_id)
    if not mod_name:
        return None
    try:
        return __import__(mod_name, fromlist=["get_talents", "get_talent"])
    except Exception as e:
        print("[talents_registry] " + faction_id + ": " + str(e))
        return None


def get_talent(talent_id: str):
    """Ищет талант по ID во всех источниках."""
    for fid in _TALENT_SOURCES.keys():
        src = _source_for(fid)
        if not src:
            continue
        t = src.get_talent(talent_id)
        if t:
            return t
    return None


def list_talents_for_faction(faction_id: str) -> list:
    src = _source_for(faction_id)
    if not src:
        return []
    return src.get_talents()


def is_talent_owned(char: dict, talent_id: str) -> bool:
    owned = char.get("talents", []) or []
    for t in owned:
        if isinstance(t, dict) and t.get("id") == talent_id:
            return True
        elif str(t) == talent_id:
            return True
    tal = get_talent(talent_id)
    if tal:
        name = tal.get("name", "")
        for t in owned:
            if isinstance(t, dict) and t.get("name") == name:
                return True
            elif str(t) == name:
                return True
    return False


def check_prerequisites(char: dict, talent_id: str) -> tuple:
    prereqs = {}
    tal = get_talent(talent_id)
    if not tal:
        return False, "Талант не найден."
    prereqs = tal.get("prerequisites", {}) or {}

    rank_min = prereqs.get("rank")
    if rank_min is not None:
        rank = int(char.get("rank", 1) or 1)
        if rank < rank_min:
            return False, "Требуется ранг " + str(rank_min) + "."

    chars = char.get("characteristics", {}) or {}
    for key, val in prereqs.items():
        if key in ("rank", "talent"):
            continue
        if key in ("WS", "BS", "S", "T", "Ag", "Int", "Per", "WP", "Fel"):
            current = int(chars.get(key, 0) or 0)
            if current < int(val):
                return False, key + " должен быть не менее " + str(val) + "."

    req_talent = prereqs.get("talent")
    if req_talent:
        if not is_talent_owned(char, req_talent):
            return False, "Требуется талант: " + str(req_talent)

    for key, val in prereqs.items():
        if key in ("rank", "talent"):
            continue
        if key in ("WS", "BS", "S", "T", "Ag", "Int", "Per", "WP", "Fel"):
            continue
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
    tal = get_talent(talent_id)
    if not tal:
        return False, 0, 0
    cost = int(tal.get("cost", 0))
    xp = int(char.get("xp", 0) or 0)
    return xp >= cost, cost, xp


def buy_talent(char: dict, talent_id: str) -> tuple:
    tal = get_talent(talent_id)
    if not tal:
        return False, "Талант не найден."

    if is_talent_owned(char, talent_id):
        return False, "Талант уже куплен."

    ok, reason = check_prerequisites(char, talent_id)
    if not ok:
        return False, reason

    ok, cost, xp = can_afford(char, talent_id)
    if not ok:
        return False, "Недостаточно XP. Нужно " + str(cost) + ", есть " + str(xp) + "."

    char["xp"] = xp - cost
    char["xp_spent"] = int(char.get("xp_spent", 0) or 0) + cost
    talents = char.setdefault("talents", [])
    talents.append({
        "id": talent_id,
        "name": tal.get("name", talent_id),
        "effect": tal.get("effect", "")
    })
    return True, "Талант «" + str(tal.get("name")) + "» куплен за " + str(cost) + " XP."


def list_available(char: dict) -> list:
    faction_id = str(char.get("faction_id", "") or "")
    out = []
    for t in list_talents_for_faction(faction_id):
        tid = t.get("id")
        if not tid:
            continue
        owned = is_talent_owned(char, tid)
        if owned:
            out.append({
                "id": tid, "name": t.get("name", tid),
                "cost": int(t.get("cost", 0)),
                "tier": int(t.get("tier", 1)),
                "category": t.get("category", "other"),
                "description": t.get("description", ""),
                "effect": t.get("effect", ""),
                "available": False,
                "reason": "Уже изучен",
                "owned": True,
            })
            continue
        ok, reason = check_prerequisites(char, tid)
        xp = int(char.get("xp", 0) or 0)
        cost = int(t.get("cost", 0))
        if ok and xp < cost:
            ok = False
            reason = "Нужно XP: " + str(cost) + " (есть " + str(xp) + ")"
        out.append({
            "id": tid, "name": t.get("name", tid),
            "cost": cost,
            "tier": int(t.get("tier", 1)),
            "category": t.get("category", "other"),
            "description": t.get("description", ""),
            "effect": t.get("effect", ""),
            "available": ok,
            "reason": reason if not ok else "",
            "owned": False,
        })
    out.sort(key=lambda x: (x["owned"], not x["available"], x["tier"], x["name"]))
    return out


if __name__ == "__main__":
    for fid in ("necrons", "tyranids"):
        fake = {
            "faction_id": fid,
            "rank": 1,
            "xp": 800,
            "characteristics": {"WS": 40, "BS": 40, "T": 40, "WP": 40},
            "talents": [], "skills": [],
        }
        ts = list_available(fake)
        print(fid + ": талантов " + str(len(ts)))
        for t in ts[:3]:
            status = "✓" if t["available"] else ("★" if t["owned"] else "✗")
            print("  " + status + " [" + str(t['tier']) + "] " + t["name"] + " — " + str(t["cost"]) + " XP")
