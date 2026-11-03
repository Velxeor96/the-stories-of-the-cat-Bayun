# scripts/patch.py — PATCH_98
# Унификация психосил: данные в JSON, единый psychic_engine.py
from __future__ import annotations
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

LOG = []
PSY_DIR = ROOT / "data" / "modules" / "rogue_trader" / "psychic"
PSY_DIR.mkdir(parents=True, exist_ok=True)


def extract_data():
    from services import psychic_human, psychic_chaos, psychic_eldar
    from services import psychic_tyranid, psychic_ork, psychic_navigator

    modules = {
        "human": psychic_human,
        "chaos": psychic_chaos,
        "eldar": psychic_eldar,
        "tyranid": psychic_tyranid,
        "ork": psychic_ork,
        "navigator": psychic_navigator,
    }

    for name, mod in modules.items():
        data = {
            "disciplines": getattr(mod, "DISCIPLINES", {}),
            "powers": getattr(mod, "PSY_POWERS", {}),
            "config": {}
        }
        if name == "ork":
            data["config"]["fail_effect"] = "damage_self"
            data["config"]["fail_damage"] = "1d5"
        elif name == "tyranid":
            data["config"]["fail_effect"] = "none"
        elif name == "chaos":
            data["config"]["fail_effect"] = "insanity"
            data["config"]["has_favor"] = True
        else:
            data["config"]["fail_effect"] = "insanity"

        out_path = PSY_DIR / f"{name}.json"
        out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        LOG.append(f"[EXPORT] data/modules/rogue_trader/psychic/{name}.json")


PSY_ENGINE_PY = r'''"""services/psychic_engine.py — Единый движок психосил."""
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
'''

def create_engine():
    path = ROOT / "services" / "psychic_engine.py"
    path.write_text(PSY_ENGINE_PY, encoding="utf-8")
    LOG.append("[CREATE] services/psychic_engine.py")


DISPATCHER_PY = r'''"""services/psychic.py — Диспетчер психосил (PATCH_98)."""
from __future__ import annotations
from services import psychic_engine

_BLOCKED = {"necron", "necrons", "drukhari", "dark_eldar", "tau", "t_au"}

def _get_race(char: dict) -> str:
    fid = str(char.get("faction_id", "")).lower()
    cid = str(char.get("career_id", "")).lower()
    if fid in ("imperium",):
        if cid == "navigator" or "навигатор" in cid:
            return "navigator"
        return "human"
    if fid == "chaos":
        return "chaos"
    if fid in ("eldar", "aeldari"):
        return "eldar"
    if fid in ("tyranid", "tyranids"):
        return "tyranid"
    if fid in ("ork", "orks"):
        return "ork"
    return "human"

def is_blocked(char: dict) -> bool:
    return str(char.get("faction_id", "")).lower() in _BLOCKED

def get_blocked_reason(char: dict) -> str:
    if is_blocked(char):
        return "Эта фракция не имеет психосил."
    return ""

def get_disciplines(char: dict) -> dict:
    if is_blocked(char):
        return {}
    return psychic_engine.get_disciplines(_get_race(char))

def get_powers(char: dict) -> list:
    if is_blocked(char):
        return []
    race = _get_race(char)
    powers = psychic_engine.get_powers(race)
    rating = int(char.get("psy_rating", 0) or 0)
    return [pid for pid, p in powers.items() if int(p.get("min_rating", 1)) <= rating]

def cast(char: dict, power_id: str) -> dict:
    if is_blocked(char):
        return {"ok": False, "reason": get_blocked_reason(char)}
    race = _get_race(char)
    allowed = set(psychic_engine.get_disciplines(race).keys())
    return psychic_engine.cast(char, race, power_id, allowed)
'''

def update_dispatcher():
    path = ROOT / "services" / "psychic.py"
    path.write_text(DISPATCHER_PY, encoding="utf-8")
    LOG.append("[PATCH] services/psychic.py (thin dispatcher)")


def cleanup():
    files = ["psychic_human.py", "psychic_chaos.py", "psychic_eldar.py",
             "psychic_tyranid.py", "psychic_ork.py", "psychic_navigator.py"]
    for f in files:
        p = ROOT / "services" / f
        if p.exists():
            p.unlink()
            LOG.append(f"[DELETE] services/{f}")


def main() -> int:
    print("=== PATCH_98: Psychic Engine ===\n")

    extract_data()
    create_engine()
    update_dispatcher()
    cleanup()

    print("\n".join(LOG))
    print("\n=== ПРОВЕРКИ ===")
    print("1. python -c \"import app\"")
    print("2. python -c \"from services.psychic import get_powers; print('Powers:', len(get_powers({'faction_id':'imperium','psy_rating':3})))\"")
    print("3. python -m pytest tests/ -q")
    print("\nDONE — PATCH_98.")
    return 0


if __name__ == "__main__":
    sys.exit(main())