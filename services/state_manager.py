"""services/state_manager.py — парсинг [STATE] и применение к персонажу."""
from __future__ import annotations

import copy
import re
from core.logger import get_logger
from schemas import StateChanges
from pydantic import ValidationError

logger = get_logger(__name__)

_BLOCK_RE = re.compile(r"\[STATE\](.*?)\[/STATE\]", re.DOTALL | re.IGNORECASE)


def parse_state(text):
    if not text:
        return text, {}

    changes = {}
    blocks = _BLOCK_RE.findall(text)
    for block in blocks:
        for line in block.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()
            if not key:
                continue
            if key in changes:
                prev = changes[key]
                if isinstance(prev, list):
                    prev.append(value)
                else:
                    changes[key] = [prev, value]
            else:
                changes[key] = value

    clean = _BLOCK_RE.sub("", text)
    clean = re.sub(r"\n{3,}", "\n\n", clean).strip()
    return clean, changes


def _to_int(v, default=0):
    try:
        return int(str(v).strip())
    except Exception:
        return default


def _delta(v):
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
    if not isinstance(char, dict) or not isinstance(changes, dict):
        return []

    new_char = copy.deepcopy(char)
    applied = []

    simple_abs = {"insanity": "insanity", "corruption": "corruption", "rank": "rank"}
    for key, sub_key in simple_abs.items():
        if key not in changes:
            continue
        val = _to_int(changes[key], None)
        if val is None:
            continue
        new_char[sub_key] = val
        applied.append(key)

    if "wounds" in changes:
        w = _ensure_dict(new_char, "wounds")
        is_d, v = _delta(changes["wounds"])
        cur = int(w.get("current", 0) or 0)
        new_val = (cur + v) if is_d else _to_int(changes["wounds"], cur)
        w["current"] = max(0, new_val)
        applied.append("wounds")

    if "fate" in changes:
        fp = _ensure_dict(new_char, "fate_points")
        is_d, v = _delta(changes["fate"])
        cur = int(fp.get("current", 0) or 0)
        new_val = (cur + v) if is_d else _to_int(changes["fate"], cur)
        fp["current"] = max(0, new_val)
        applied.append("fate")

    if "xp" in changes:
        is_d, v = _delta(changes["xp"])
        cur = int(new_char.get("xp", 0) or 0)
        new_char["xp"] = (cur + v) if is_d else _to_int(changes["xp"], cur)
        applied.append("xp")

    if "money" in changes:
        raw = changes["money"]
        is_d, v = _delta(raw)
        _old = int(new_char.get("money", 0) or 0)
        _new = (_old + v) if is_d else _to_int(raw, _old)
        if _new < 0:
            logger.info(f"money clamped: {_old} -> {_new} -> 0")
            _new = 0
        new_char["money"] = _new
        if _new != _old:
            logger.info(f"money: {_old} -> {_new}")
        applied.append("money")

    if "location" in changes:
        new_char["location"] = {"place": str(changes["location"]).strip()}
        applied.append("location")
    if "date" in changes:
        new_char["game_date"] = str(changes["date"]).strip()
        applied.append("date")

    if "journal" in changes:
        journal = _ensure_list(new_char, "journal")
        for entry in _split_multi(changes["journal"]):
            journal.append(entry)
        applied.append("journal")

    adds = []
    if "equipment_add" in changes:
        adds += _split_multi(changes["equipment_add"])
    if "inventory_add" in changes:
        adds += _split_multi(changes["inventory_add"])
    if adds:
        _append_unique(_ensure_list(new_char, "equipment"), adds)
        applied.append("equipment_add")
    
    rems = []
    if "equipment_remove" in changes:
        rems += _split_multi(changes["equipment_remove"])
    if "inventory_remove" in changes:
        rems += _split_multi(changes["inventory_remove"])
    if rems:
        new_char["equipment"] = _remove_by_name(_ensure_list(new_char, "equipment"), rems)
        applied.append("equipment_remove")

    if "weapon_add" in changes:
        weapons = _ensure_list(new_char, "weapons")
        for spec in _split_multi(changes["weapon_add"]):
            if "|" in spec:
                name, _, stats = spec.partition("|")
                weapons.append({"name": name.strip(), "stats": stats.strip()})
            else:
                weapons.append({"name": spec})
        applied.append("weapon_add")
    if "weapon_lost" in changes:
        new_char["weapons"] = _remove_by_name(
            _ensure_list(new_char, "weapons"),
            _split_multi(changes["weapon_lost"]),
        )
        applied.append("weapon_lost")

    for key, value in list(changes.items()):
        if key.startswith("armour_equip_"):
            if _apply_armour_zone(new_char, key[len("armour_equip_"):], True):
                applied.append(key)
        elif key.startswith("armour_unequip_"):
            if _apply_armour_zone(new_char, key[len("armour_unequip_"):], False):
                applied.append(key)
        elif key == "armour_equip":
            for zone in _split_multi(value):
                if _apply_armour_zone(new_char, zone, True):
                    applied.append(key)
        elif key == "armour_unequip":
            for zone in _split_multi(value):
                if _apply_armour_zone(new_char, zone, False):
                    applied.append(key)

    if "npc_add" in changes:
        _append_unique(_ensure_list(new_char, "npcs"), _split_multi(changes["npc_add"]))
        applied.append("npc_add")
    if "npc_remove" in changes:
        new_char["npcs"] = _remove_by_name(_ensure_list(new_char, "npcs"), _split_multi(changes["npc_remove"]))
        applied.append("npc_remove")
    if "quest_add" in changes:
        _append_unique(_ensure_list(new_char, "quests"), _split_multi(changes["quest_add"]))
        applied.append("quest_add")
    if "quest_remove" in changes:
        new_char["quests"] = _remove_by_name(_ensure_list(new_char, "quests"), _split_multi(changes["quest_remove"]))
        applied.append("quest_remove")
    if "companion_add" in changes:
        _append_unique(_ensure_list(new_char, "companions"), _split_multi(changes["companion_add"]))
        applied.append("companion_add")
    if "companion_remove" in changes:
        new_char["companions"] = _remove_by_name(_ensure_list(new_char, "companions"), _split_multi(changes["companion_remove"]))
        applied.append("companion_remove")
    if "effect_add" in changes:
        _append_unique(_ensure_list(new_char, "effects"), _split_multi(changes["effect_add"]))
        applied.append("effect_add")
    if "effect_remove" in changes:
        new_char["effects"] = _remove_by_name(_ensure_list(new_char, "effects"), _split_multi(changes["effect_remove"]))
        applied.append("effect_remove")

    rep = _ensure_dict(new_char, "reputation")
    for key, value in list(changes.items()):
        if key.startswith("reputation_"):
            name = key[len("reputation_"):]
            is_d, v = _delta(value)
            rep[name] = (int(rep.get(name, 0) or 0) + v) if is_d else _to_int(value, int(rep.get(name, 0) or 0))
            applied.append(key)

    specials = _ensure_dict(new_char, "special")
    for key, value in list(changes.items()):
        if key.startswith("special_"):
            name = key[len("special_"):]
            is_d, v = _delta(value)
            specials[name] = (int(specials.get(name, 0) or 0) + v) if is_d else _to_int(value, int(specials.get(name, 0) or 0))
            applied.append(key)

    chars = _ensure_dict(new_char, "characteristics")
    for key, value in list(changes.items()):
        if key.startswith("characteristic_"):
            code = key[len("characteristic_"):]
            code_map = {"ws": "WS", "bs": "BS", "s": "S", "t": "T", "ag": "Ag", "int": "Int", "per": "Per", "wp": "WP", "fel": "Fel"}
            canon = code_map.get(code.lower())
            if canon:
                chars[canon] = _to_int(value, int(chars.get(canon, 0) or 0))
                applied.append(key)

    for ship_key in ("ship_hull", "ship_crew", "ship_status", "ship_note"):
        if ship_key in changes:
            new_char[ship_key] = str(changes[ship_key]).strip()
            applied.append(ship_key)

    if "ship_acquired" in changes:
        new_char["has_ship"] = True
        notes = _split_multi(changes["ship_acquired"])
        ship = _ensure_dict(new_char, "ship")
        if notes and not ship.get("name"):
            ship["name"] = notes[0]
            if len(notes) > 1:
                ship["description"] = "; ".join(notes[1:])
        applied.append("ship_acquired")
    if "ship_lost" in changes:
        new_char["has_ship"] = False
        prev_ship = new_char.get("ship") or {}
        if isinstance(prev_ship, dict):
            prev_ship["status"] = "потерян: " + str(changes["ship_lost"]).strip()
        else:
            prev_ship = {"status": "потерян: " + str(changes["ship_lost"]).strip()}
        new_char["ship"] = prev_ship
        applied.append("ship_lost")

    flags = _ensure_dict(new_char, "flags")
    for key, value in list(changes.items()):
        if key.startswith("flag_"):
            name = key[len("flag_"):].strip()
            flags[name] = str(value).strip().lower() in ("1", "true", "yes", "on", "да", "истина", "y")
            applied.append(key)
        elif key.startswith("unflag_"):
            name = key[len("unflag_"):].strip()
            flags.pop(name, None)
            applied.append(key)

    return new_char, applied


def parse_and_apply(narrative: str, char: dict) -> tuple[str, list[str], dict]:
    clean_text, changes = parse_state(narrative)
    if not changes:
        return clean_text, [], char

    try:
        validated = StateChanges(**changes)
        valid_dict = validated.model_dump(exclude_unset=True)
    except ValidationError as e:
        logger.error(f"State validation failed: {e}")
        return clean_text, [], char

    new_char, applied = apply_changes(char, valid_dict)
    return clean_text, applied, new_char
