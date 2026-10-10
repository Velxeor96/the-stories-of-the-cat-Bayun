"""services/psychic.py — диспетчер пси-сил по фракциям."""
from __future__ import annotations

from services import psychic_human
from services import psychic_navigator
from services import psychic_chaos


_HUMAN_ASTROPATH_CAREERS = {"astropath", "астропат"}
_HUMAN_NAVIGATOR_CAREERS = {"navigator", "навигатор"}


def _classify(char: dict) -> dict:
    fid = str(char.get("faction_id", "")).lower()
    sfid = str(char.get("subfaction_id", "")).lower()
    cid = str(char.get("career_id", "")).lower()
    cname = str(char.get("career_name", ""))
    rating = int(char.get("psy_rating", 0) or 0)

    out = {"module": None, "chaos_only": False,
           "astropath_only": False, "has_psy": rating > 0}

    if fid == "imperium":
        if cid in _HUMAN_NAVIGATOR_CAREERS or cname in _HUMAN_NAVIGATOR_CAREERS:
            out["module"] = "navigator"
            return out
        if cid in _HUMAN_ASTROPATH_CAREERS or cname in _HUMAN_ASTROPATH_CAREERS:
            out["module"] = "human"
            out["astropath_only"] = True
            return out
        out["module"] = "human"
        return out

    if fid == "chaos":
        out["module"] = "chaos"
        return out

    # Eldar — PATCH_81
    # Orks — PATCH_81
    # Tyranids / Genestealers — PATCH_81

    return out


def get_disciplines(char: dict = None) -> dict:
    if not char:
        return {}
    info = _classify(char)
    if info["module"] == "human":
        return psychic_human.get_disciplines()
    if info["module"] == "navigator":
        return psychic_navigator.get_disciplines()
    if info["module"] == "chaos":
        return psychic_chaos.get_disciplines()
    return {}


def get_powers(char: dict) -> list:
    info = _classify(char)
    if info["module"] == "human":
        return psychic_human.get_powers(
            char,
            chaos_only=info["chaos_only"],
            astropath_only=info["astropath_only"],
        )
    if info["module"] == "navigator":
        return psychic_navigator.get_powers(char)
    if info["module"] == "chaos":
        return psychic_chaos.get_powers(char)
    return []


def get_power(power_id: str):
    for mod in (psychic_human, psychic_navigator, psychic_chaos):
        p = mod.get_power(power_id)
        if p:
            return p
    return None


def get_charge(char: dict) -> int:
    if not isinstance(char, dict):
        return 0
    return int(char.get("psy_charge", 0) or 0)


def regen_charge(char: dict) -> None:
    if not isinstance(char, dict):
        return
    rating = int(char.get("psy_rating", 0) or 0)
    if rating > 0:
        char["psy_charge"] = rating * 3


def cast(char: dict, power_key: str) -> dict:
    info = _classify(char)
    if not info["module"]:
        return {"ok": False, "reason": "нет доступа к психосилам"}
    if info["module"] == "human":
        return psychic_human.cast(
            char, power_key,
            chaos_only=info["chaos_only"],
            astropath_only=info["astropath_only"],
        )
    if info["module"] == "navigator":
        return psychic_navigator.cast(char, power_key)
    if info["module"] == "chaos":
        return psychic_chaos.cast(char, power_key)
    return {"ok": False, "reason": "нет доступа"}


def full_catalog(char: dict) -> dict:
    info = _classify(char)
    rating = int(char.get("psy_rating", 0) or 0)
    if not info["module"]:
        return {}
    if info["module"] == "human":
        return psychic_human.full_catalog(
            rating,
            chaos_only=info["chaos_only"],
            astropath_only=info["astropath_only"],
        )
    if info["module"] == "navigator":
        return psychic_navigator.full_catalog(rating)
    if info["module"] == "chaos":
        return psychic_chaos.full_catalog(rating, char=char)
    return {}


def has_access(char: dict) -> bool:
    if not isinstance(char, dict):
        return False
    info = _classify(char)
    return bool(info["module"]) and int(char.get("psy_rating", 0) or 0) > 0
