"""services/psychic.py — диспетчер пси-сил по фракциям.

Модули:
- human     — Империум (Astropath / Sanctioned Psyker и др.)
- navigator — Навигатор (Imperium)
- chaos     — Хаос (5 дисциплин, favor-механика)
- eldar     — Эльдар (6 рунических дисциплин)
- tyranid   — Тираниды (Hive Mind / Broodmind / Biomancy)
- ork       — Орки (WAAAGH! / Mork & Gork)

Заблокированы (нет псайкеров по лору):
- necron    — используют технологии, не Варп
- drukhari  — Слаанеш пожирает их души при психосиле
- tau       — нет врождённых псайкеров
"""
from __future__ import annotations

from services import psychic_human
from services import psychic_navigator
from services import psychic_chaos
from services import psychic_eldar
from services import psychic_tyranid
from services import psychic_ork


_HUMAN_ASTROPATH_CAREERS = {"astropath", "астропат"}
_HUMAN_NAVIGATOR_CAREERS = {"navigator", "навигатор"}

# Фракции без психосил
_BLOCKED_FACTIONS = {"necron", "necrons", "drukhari", "dark_eldar", "tau", "t_au"}

# Русские названия для UI
_BLOCKED_REASONS = {
    "necron": "Некроны не используют Варп — только технологии Ка'тан.",
    "necrons": "Некроны не используют Варп — только технологии Ка'тан.",
    "drukhari": "Друкхари не могут использовать психосилы: Слаанеш пожирает их души.",
    "dark_eldar": "Тёмные Эльдар не могут использовать психосилы: Слаанеш пожирает их души.",
    "tau": "У Тау нет врождённых псайкеров.",
    "t_au": "У Тау нет врождённых псайкеров.",
}


def _classify(char: dict) -> dict:
    fid = str(char.get("faction_id", "")).lower()
    sfid = str(char.get("subfaction_id", "")).lower()
    cid = str(char.get("career_id", "")).lower()
    cname = str(char.get("career_name", ""))
    rating = int(char.get("psy_rating", 0) or 0)

    out = {"module": None, "chaos_only": False, "astropath_only": False,
           "has_psy": rating > 0, "blocked": False, "blocked_reason": ""}

    # === ЗАБЛОКИРОВАННЫЕ ===
    if fid in _BLOCKED_FACTIONS:
        out["blocked"] = True
        out["blocked_reason"] = _BLOCKED_REASONS.get(
            fid, "Эта фракция не имеет психосил.")
        return out

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

    if fid in ("eldar", "aeldari"):
        out["module"] = "eldar"
        return out

    if fid in ("tyranid", "tyranids"):
        out["module"] = "tyranid"
        return out

    if fid in ("ork", "orks", "orc"):
        out["module"] = "ork"
        return out

    return out


def is_blocked(char: dict) -> bool:
    """True, если фракция принципиально не имеет психосил."""
    if not isinstance(char, dict):
        return False
    return _classify(char).get("blocked", False)


def get_blocked_reason(char: dict) -> str:
    if not isinstance(char, dict):
        return ""
    return _classify(char).get("blocked_reason", "")


def get_disciplines(char: dict = None) -> dict:
    if not char:
        return {}
    info = _classify(char)
    m = info["module"]
    if m == "human":
        return psychic_human.get_disciplines()
    if m == "navigator":
        return psychic_navigator.get_disciplines()
    if m == "chaos":
        return psychic_chaos.get_disciplines()
    if m == "eldar":
        return psychic_eldar.get_disciplines()
    if m == "tyranid":
        return psychic_tyranid.get_disciplines()
    if m == "ork":
        return psychic_ork.get_disciplines()
    return {}


def get_powers(char: dict) -> list:
    info = _classify(char)
    m = info["module"]
    if m == "human":
        return psychic_human.get_powers(
            char, chaos_only=info["chaos_only"],
            astropath_only=info["astropath_only"])
    if m == "navigator":
        return psychic_navigator.get_powers(char)
    if m == "chaos":
        return psychic_chaos.get_powers(char)
    if m == "eldar":
        return psychic_eldar.get_powers(char)
    if m == "tyranid":
        return psychic_tyranid.get_powers(char)
    if m == "ork":
        return psychic_ork.get_powers(char)
    return []


def get_power(power_id: str):
    for mod in (psychic_human, psychic_navigator, psychic_chaos,
                psychic_eldar, psychic_tyranid, psychic_ork):
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
    m = info["module"]
    if info["blocked"]:
        return {"ok": False, "reason": info["blocked_reason"]}
    if not m:
        return {"ok": False, "reason": "нет доступа к психосилам"}
    if m == "human":
        return psychic_human.cast(
            char, power_key, chaos_only=info["chaos_only"],
            astropath_only=info["astropath_only"])
    if m == "navigator":
        return psychic_navigator.cast(char, power_key)
    if m == "chaos":
        return psychic_chaos.cast(char, power_key)
    if m == "eldar":
        return psychic_eldar.cast(char, power_key)
    if m == "tyranid":
        return psychic_tyranid.cast(char, power_key)
    if m == "ork":
        return psychic_ork.cast(char, power_key)
    return {"ok": False, "reason": "нет доступа"}


def full_catalog(char: dict) -> dict:
    info = _classify(char)
    rating = int(char.get("psy_rating", 0) or 0)
    m = info["module"]
    if info["blocked"] or not m:
        return {}
    if m == "human":
        return psychic_human.full_catalog(
            rating, chaos_only=info["chaos_only"],
            astropath_only=info["astropath_only"])
    if m == "navigator":
        return psychic_navigator.full_catalog(rating)
    if m == "chaos":
        return psychic_chaos.full_catalog(rating, char=char)
    if m == "eldar":
        return psychic_eldar.full_catalog(rating, char=char)
    if m == "tyranid":
        return psychic_tyranid.full_catalog(rating, char=char)
    if m == "ork":
        return psychic_ork.full_catalog(rating, char=char)
    return {}


def has_access(char: dict) -> bool:
    if not isinstance(char, dict):
        return False
    info = _classify(char)
    if info["blocked"]:
        return False
    return bool(info["module"]) and int(char.get("psy_rating", 0) or 0) > 0


# ================ FAVOR (Chaos) ================

def get_favor_level(char: dict, god: str) -> int:
    return psychic_chaos.get_favor_level(char, god)


def add_favor(char: dict, god: str, amount: int) -> None:
    psychic_chaos.add_favor(char, god, amount)


def get_all_favor(char: dict) -> dict:
    return psychic_chaos.get_all_favor(char)
