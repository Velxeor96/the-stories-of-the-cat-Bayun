"""services/psychic_engine.py — Единый движок психосил."""
from __future__ import annotations
import random
import re
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
PSY_DIR = ROOT / "data" / "modules" / "rogue_trader" / "psychic"

_CACHE = {}

def _load_json(name: str) -> dict:
    if name in _CACHE:
        return _CACHE[name]
    p = PSY_DIR / f"{name}.json"
    if not p.exists():
        return {}
    data = json.loads(p.read_text(encoding="utf-8"))
    _CACHE[name] = data
    return data

def get_disciplines(race: str) -> dict:
    return _load_json(race).get("disciplines", {})

def get_powers(race: str) -> dict:
    return _load_json(race).get("powers", {})

def get_power(race: str, power_id: str) -> dict:
    return get_powers(race).get(power_id, {})

def _roll_damage(expr: str) -> int:
    m = re.match(r"(\d+)d(\d+)([+\-]\d+)?", str(expr))
    if not m:
        return 0
    n, f = int(m.group(1)), int(m.group(2))
    total = sum(random.randint(1, f) for _ in range(n))
    if m.group(3):
        total += int(m.group(3))
    return total

def cast(char: dict, race: str, power_id: str, allowed: set, favor_level: int = 0) -> dict:
    power = get_power(race, power_id)
    if not power:
        return {"ok": False, "reason": "неизвестная сила"}

    config = _load_json(race).get("config", {})

    if power.get("discipline") not in allowed:
        return {"ok": False, "reason": "дисциплина недоступна"}

    rating = int(char.get("psy_rating", 0) or 0)
    if rating < int(power.get("min_rating", 1)):
        return {"ok": False, "reason": "недостаточный psy_rating"}

    if int(power.get("favor_level", 0)) > favor_level:
        return {"ok": False, "reason": "недостаточная благосклонность"}

    cost = int(power.get("cost", 2))
    charge = int(char.get("psy_charge", 0) or 0)
    if charge < cost:
        return {"ok": False, "reason": "не хватает заряда"}

    wp = int((char.get("characteristics") or {}).get("WP", 30))
    roll = random.randint(1, 100)
    success = roll <= wp
    char["psy_charge"] = charge - cost

    corruption = int(power.get("corruption", 0))
    if corruption > 0:
        char["corruption"] = int(char.get("corruption", 0) or 0) + corruption

    fail_effect = config.get("fail_effect", "insanity")
    if not success:
        if fail_effect == "damage_self":
            dmg = _roll_damage(config.get("fail_damage", "1d5"))
            w = char.setdefault("wounds", {})
            w["current"] = max(0, int(w.get("current", 0)) - dmg)
            return {"ok": True, "roll": roll, "success": False, "text": f"{power['name']} сорвалась. Урон себе: {dmg}"}
        elif fail_effect == "insanity":
            char["insanity"] = int(char.get("insanity", 0) or 0) + 1
            return {"ok": True, "roll": roll, "success": False, "text": f"{power['name']} сорвалась. +1 Безумие"}
        else:
            return {"ok": True, "roll": roll, "success": False, "text": f"{power['name']} рассеялась в Варпе"}

    ptype = power.get("type", "utility")
    if ptype == "attack":
        dmg = _roll_damage(power.get("damage", "1d10"))
        return {"ok": True, "roll": roll, "success": True, "damage": dmg, "text": f"{power['name']} бьёт на {dmg}"}
    elif ptype == "heal":
        heal = _roll_damage(power.get("heal", "1d5"))
        w = char.setdefault("wounds", {})
        w["current"] = min(int(w.get("max", 10)), int(w.get("current", 0)) + heal)
        return {"ok": True, "roll": roll, "success": True, "heal": heal, "text": f"{power['name']}: +{heal} ран"}
    elif ptype == "buff":
        applied = power.get("buff", {})
        chars = char.setdefault("characteristics", {})
        for k, v in applied.items():
            if k in ("WS","BS","S","T","Ag","Int","Per","WP","Fel"):
                chars[k] = int(chars.get(k, 0)) + int(v)
        return {"ok": True, "roll": roll, "success": True, "text": f"{power['name']}: применено"}
    else:
        return {"ok": True, "roll": roll, "success": True, "text": f"{power['name']}: {power.get('desc','')}"}
