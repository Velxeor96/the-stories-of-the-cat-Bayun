"""services/psychic.py — диспетчер пси-сил.

Определяет по фракции/субфракции/карьере, какой модуль использовать.
"""
from __future__ import annotations

from services import psychic_human
from services import psychic_navigator


# --- Кто имеет доступ к каким модулям ---
# Eldar / Tyranids / Orks — добавятся в PATCH_80-81
_RACE_ACCESS = {
    "imperium":     ["human", "navigator"],  # зависит от карьеры
    "chaos":        ["human"],               # Sorcerer, включая Demonology
    "eldar":        [],                      # PATCH_80
    "drukhari":     [],                      # НЕТ психосил
    "orks":         [],                      # PATCH_81
    "tau":          [],                      # НЕТ психосил
    "necrons":      [],                      # НЕТ психосил
    "tyranids":     [],                      # PATCH_81
    "genestealers": [],                      # PATCH_81
}

# Внутри human — какие карьеры что видят
_HUMAN_ASTROPATH_CAREERS = {"astropath", "Астропат"}
_HUMAN_NAVIGATOR_CAREERS = {"navigator", "Навигатор"}


def _classify(char: dict) -> dict:
    """Определяет доступ для персонажа."""
    fid = str(char.get("faction_id", "")).lower()
    sfid = str(char.get("subfaction_id", "")).lower()
    cid = str(char.get("career_id", "")).lower()
    cname = str(char.get("career_name", ""))
    rating = int(char.get("psy_rating", 0) or 0)

    out = {
        "module": None,
        "chaos_only": False,
        "astropath_only": False,
        "navigator_only": False,
        "has_psy": rating > 0,
    }

    if fid not in _RACE_ACCESS:
        return out
    allowed = _RACE_ACCESS[fid]
    if not allowed:
        return out

    # Chaos — Sorcerer
    if fid == "chaos":
        if "human" in allowed:
            out["module"] = "human"
            out["chaos_only"] = True
        return out

    # Imperium — по карьере
    if fid == "imperium":
        if cid in _HUMAN_NAVIGATOR_CAREERS or cname in _HUMAN_NAVIGATOR_CAREERS:
            out["module"] = "navigator"
            out["navigator_only"] = True
            return out
        if cid in _HUMAN_ASTROPATH_CAREERS or cname in _HUMAN_ASTROPATH_CAREERS:
            out["module"] = "human"
            out["astropath_only"] = True
            return out
        # Все остальные псайкеры Империума (Sanctioned Psyker, Librarian, Inq Psyker)
        out["module"] = "human"
        return out

    return out


# ============================================================
# Публичный API
# ============================================================

def get_disciplines(char: dict = None) -> dict:
    """Список дисциплин для персонажа (или пустой, если нет доступа)."""
    if not char:
        return {}
    info = _classify(char)
    if info["module"] == "human":
        return psychic_human.get_disciplines()
    if info["module"] == "navigator":
        return psychic_navigator.get_disciplines()
    return {}


def get_powers(char: dict) -> list:
    """Список доступных сил по персонажу."""
    info = _classify(char)
    if info["module"] == "human":
        return psychic_human.get_powers(
            char,
            chaos_only=info["chaos_only"],
            astropath_only=info["astropath_only"],
        )
    if info["module"] == "navigator":
        return psychic_navigator.get_powers(char)
    return []


def get_power(power_id: str):
    """Ищет силу во всех модулях."""
    p = psychic_human.get_power(power_id)
    if p:
        return p
    p = psychic_navigator.get_power(power_id)
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
    """Применяет силу."""
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
    return {"ok": False, "reason": "нет доступа"}


def full_catalog(char: dict) -> dict:
    """Полный каталог для UI по персонажу."""
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
    return {}


def has_access(char: dict) -> bool:
    """Есть ли у персонажа вообще доступ к психосилам."""
    if not isinstance(char, dict):
        return False
    info = _classify(char)
    return bool(info["module"]) and int(char.get("psy_rating", 0) or 0) > 0
