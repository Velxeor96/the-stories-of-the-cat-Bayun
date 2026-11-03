"""services/psychic.py — Диспетчер психосил (PATCH_98)."""
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
