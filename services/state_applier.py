# PATCH_16J
# services/state_applier.py — применение [STATE] changes к листу персонажа.
from __future__ import annotations


def _to_int(v, default=0):
    try:
        return int(str(v).strip())
    except Exception:
        return default


def _delta(v):
    # Парсит '+N' / '-N' / 'N' -> (is_delta, N).
    s = str(v).strip()
    if s.startswith("+") or s.startswith("-"):
        try:
            return True, int(s)
        except Exception:
            return False, 0
    return False, _to_int(s)


def _as_list(v):
    if isinstance(v, list):
        return v
    return [v]


def _split_multi(v):
    # 'Кинжал; Камни Души' -> ['Кинжал', 'Камни Души'].
    out = []
    for chunk in _as_list(v):
        for piece in str(chunk).split(";"):
            piece = piece.strip()
            if piece:
                out.append(piece)
    return out


def _ensure_dict(parent, key):
    if not isinstance(parent.get(key), dict):
        parent[key] = {}
    return parent[key]


def _ensure_list(parent, key):
    if not isinstance(parent.get(key), list):
        parent[key] = []
    return parent[key]


def _append_unique(lst, items):
    existing = set()
    for it in lst:
        if isinstance(it, dict):
            existing.add(str(it.get("name") or it))
        else:
            existing.add(str(it))
    for it in items:
        key = str(it.get("name") if isinstance(it, dict) else it)
        if key not in existing:
            lst.append(it)
            existing.add(key)


def _remove_by_name(lst, names):
    names_set = {str(n).strip().lower() for n in names}
    out = []
    for it in lst:
        if isinstance(it, dict):
            nm = str(it.get("name") or "")
        else:
            nm = str(it)
        if nm.strip().lower() in names_set:
            continue
        out.append(it)
    return out


def _apply_armour_zone(char, zone, do_equip):
    zone = str(zone).strip().lower()
    if zone not in ("head", "body", "arms", "legs"):
        return False
    armour = _ensure_dict(char, "armour")
    if do_equip:
        armour.setdefault(zone, "")
    else:
        removed = armour.get(zone) or ""
        armour[zone] = ""
        if removed:
            equip = _ensure_list(char, "equipment")
            _append_unique(equip, [removed])
    return True


def apply_changes(char, changes):
    # Мутирует char по changes. Возвращает список применённых ключей.
    if not isinstance(char, dict):
        return []
    if not isinstance(changes, dict):
        return []

    applied = []

    simple_abs = {
        "wounds": ("wounds", "current"),
        "fate": ("fate_points", "current"),
        "insanity": (None, "insanity"),
        "corruption": (None, "corruption"),
        "xp": (None, "xp"),
        "rank": (None, "rank"),
    }
    for key, (sub_dict, sub_key) in simple_abs.items():
        if key not in changes:
            continue
        val = _to_int(changes[key], None)
        if val is None:
            continue
        if sub_dict:
            d = _ensure_dict(char, sub_dict)
            d[sub_key] = val
        else:
            char[sub_key] = val
        applied.append(key)

    if "xp" in changes:
        is_d, v = _delta(changes["xp"])
        if is_d:
            char["xp"] = int(char.get("xp", 0) or 0) + v

    if "money" in changes:
        raw = changes["money"]
        is_d, v = _delta(raw)
        if is_d:
            char["money"] = int(char.get("money", 0) or 0) + v
        else:
            char["money"] = _to_int(raw, int(char.get("money", 0) or 0))
        applied.append("money")

    if "location" in changes:
        char["location"] = {"place": str(changes["location"]).strip()}
        applied.append("location")
    if "date" in changes:
        char["game_date"] = str(changes["date"]).strip()
        applied.append("date")

    if "journal" in changes:
        journal = _ensure_list(char, "journal")
        for entry in _split_multi(changes["journal"]):
            journal.append(entry)
        applied.append("journal")

    adds = []
    if "equipment_add" in changes:
        adds += _split_multi(changes["equipment_add"])
    if "inventory_add" in changes:
        adds += _split_multi(changes["inventory_add"])
    if adds:
        _append_unique(_ensure_list(char, "equipment"), adds)
        applied.append("equipment_add")
    rems = []
    if "equipment_remove" in changes:
        rems += _split_multi(changes["equipment_remove"])
    if "inventory_remove" in changes:
        rems += _split_multi(changes["inventory_remove"])
    if rems:
        char["equipment"] = _remove_by_name(_ensure_list(char, "equipment"), rems)
        applied.append("equipment_remove")

    if "weapon_add" in changes:
        weapons = _ensure_list(char, "weapons")
        for spec in _split_multi(changes["weapon_add"]):
            if "|" in spec:
                name, _, stats = spec.partition("|")
                weapons.append({"name": name.strip(), "stats": stats.strip()})
            else:
                weapons.append({"name": spec})
        applied.append("weapon_add")
    if "weapon_lost" in changes:
        char["weapons"] = _remove_by_name(
            _ensure_list(char, "weapons"),
            _split_multi(changes["weapon_lost"]),
        )
        applied.append("weapon_lost")

    for key, value in list(changes.items()):
        if key.startswith("armour_equip_"):
            zone = key[len("armour_equip_"):]
            if _apply_armour_zone(char, zone, True):
                applied.append(key)
        elif key.startswith("armour_unequip_"):
            zone = key[len("armour_unequip_"):]
            if _apply_armour_zone(char, zone, False):
                applied.append(key)
        elif key == "armour_equip":
            for zone in _split_multi(value):
                if _apply_armour_zone(char, zone, True):
                    applied.append(key)
        elif key == "armour_unequip":
            for zone in _split_multi(value):
                if _apply_armour_zone(char, zone, False):
                    applied.append(key)

    if "npc_add" in changes:
        _append_unique(_ensure_list(char, "npcs"), _split_multi(changes["npc_add"]))
        applied.append("npc_add")
    if "npc_remove" in changes:
        char["npcs"] = _remove_by_name(_ensure_list(char, "npcs"),
                                       _split_multi(changes["npc_remove"]))
        applied.append("npc_remove")

    if "quest_add" in changes:
        _append_unique(_ensure_list(char, "quests"),
                       _split_multi(changes["quest_add"]))
        applied.append("quest_add")
    if "quest_remove" in changes:
        char["quests"] = _remove_by_name(_ensure_list(char, "quests"),
                                         _split_multi(changes["quest_remove"]))
        applied.append("quest_remove")

    if "companion_add" in changes:
        _append_unique(_ensure_list(char, "companions"),
                       _split_multi(changes["companion_add"]))
        applied.append("companion_add")
    if "companion_remove" in changes:
        char["companions"] = _remove_by_name(
            _ensure_list(char, "companions"),
            _split_multi(changes["companion_remove"]))
        applied.append("companion_remove")

    if "effect_add" in changes:
        _append_unique(_ensure_list(char, "effects"),
                       _split_multi(changes["effect_add"]))
        applied.append("effect_add")
    if "effect_remove" in changes:
        char["effects"] = _remove_by_name(
            _ensure_list(char, "effects"),
            _split_multi(changes["effect_remove"]))
        applied.append("effect_remove")

    rep = _ensure_dict(char, "reputation")
    for key, value in list(changes.items()):
        if key.startswith("reputation_"):
            name = key[len("reputation_"):]
            is_d, v = _delta(value)
            if is_d:
                rep[name] = int(rep.get(name, 0) or 0) + v
            else:
                rep[name] = _to_int(value, int(rep.get(name, 0) or 0))
            applied.append(key)

    specials = _ensure_dict(char, "special")
    for key, value in list(changes.items()):
        if key.startswith("special_"):
            name = key[len("special_"):]
            is_d, v = _delta(value)
            if is_d:
                specials[name] = int(specials.get(name, 0) or 0) + v
            else:
                specials[name] = _to_int(value, int(specials.get(name, 0) or 0))
            applied.append(key)

    chars = _ensure_dict(char, "characteristics")
    for key, value in list(changes.items()):
        if key.startswith("characteristic_"):
            code = key[len("characteristic_"):]
            code_map = {
                "ws": "WS", "bs": "BS", "s": "S", "t": "T",
                "ag": "Ag", "int": "Int", "per": "Per",
                "wp": "WP", "fel": "Fel",
            }
            canon = code_map.get(code.lower())
            if not canon:
                continue
            chars[canon] = _to_int(value, int(chars.get(canon, 0) or 0))
            applied.append(key)

    for ship_key in ("ship_hull", "ship_crew", "ship_status", "ship_note"):
        if ship_key in changes:
            char[ship_key] = str(changes[ship_key]).strip()
            applied.append(ship_key)

    return applied
