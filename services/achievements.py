# PATCH_28
"""services/achievements.py — достижения игрока."""
from __future__ import annotations

ACHIEVEMENTS = [
    ("first_blood",  "Первая кровь",   "Победить в первом бою"),
    ("ten_rolls",    "Бросок за броском", "Сделать 10 бросков (по логу)"),
    ("sailor",       "Мореход",         "Совершить 3 варп-прыжка"),
    ("rich",         "Богач",           "5000+ тронов"),
    ("rank_3",       "Ранг 3",          "Достичь третьего ранга"),
    ("madman",       "Сумасшедший",     "Безумие 50+"),
    ("corrupted",    "Запятнанный",     "Порча 50+"),
    ("collector",    "Коллекционер",    "20+ предметов в инвентаре"),
    ("explorer",     "Исследователь",   "5+ записей в дневнике"),
    ("diplomat",     "Дипломат",        "Репутация 50+ с любой фракцией"),
]


def _has_flag(char: dict, key: str) -> bool:
    flags = char.get("achievements") or {}
    return bool(flags.get(key))


def _set_flag(char: dict, key: str) -> None:
    f = char.setdefault("achievements", {})
    f[key] = True


def check_all(char: dict, extra: dict = None) -> list:
    """Возвращает список новых достижений."""
    extra = extra or {}
    new = []
    if not isinstance(char, dict):
        return new

    # first_blood
    if extra.get("combat_win") and not _has_flag(char, "first_blood"):
        _set_flag(char, "first_blood")
        new.append("first_blood")

    # ten_rolls
    if int(extra.get("total_rolls", 0) or 0) >= 10 and not _has_flag(char, "ten_rolls"):
        _set_flag(char, "ten_rolls")
        new.append("ten_rolls")

    # sailor — отслеживается через warp_jumps
    if int(char.get("warp_jumps", 0) or 0) >= 3 and not _has_flag(char, "sailor"):
        _set_flag(char, "sailor")
        new.append("sailor")

    # rich
    if int(char.get("money", 0) or 0) >= 5000 and not _has_flag(char, "rich"):
        _set_flag(char, "rich")
        new.append("rich")

    # rank_3
    if int(char.get("rank", 1) or 1) >= 3 and not _has_flag(char, "rank_3"):
        _set_flag(char, "rank_3")
        new.append("rank_3")

    # madman
    if int(char.get("insanity", 0) or 0) >= 50 and not _has_flag(char, "madman"):
        _set_flag(char, "madman")
        new.append("madman")

    # corrupted
    if int(char.get("corruption", 0) or 0) >= 50 and not _has_flag(char, "corrupted"):
        _set_flag(char, "corrupted")
        new.append("corrupted")

    # collector
    total = 0
    try:
        from services.inventory import get_inventory, CATEGORIES
        inv = get_inventory(char)
        total = sum(len(inv[c]) for c in CATEGORIES)
    except Exception:
        pass
    if total >= 20 and not _has_flag(char, "collector"):
        _set_flag(char, "collector")
        new.append("collector")

    # explorer
    journal = char.get("journal") or []
    if len(journal) >= 5 and not _has_flag(char, "explorer"):
        _set_flag(char, "explorer")
        new.append("explorer")

    # diplomat
    rep = char.get("reputation") or {}
    if isinstance(rep, dict):
        for v in rep.values():
            try:
                if int(v) >= 50 and not _has_flag(char, "diplomat"):
                    _set_flag(char, "diplomat")
                    new.append("diplomat")
                    break
            except Exception:
                continue

    return new


def describe(key: str) -> tuple:
    for k, name, desc in ACHIEVEMENTS:
        if k == key:
            return name, desc
    return key, ""


def all_with_status(char: dict) -> list:
    flags = (char.get("achievements") if isinstance(char, dict) else None) or {}
    out = []
    for k, name, desc in ACHIEVEMENTS:
        out.append({"key": k, "name": name, "desc": desc,
                    "unlocked": bool(flags.get(k))})
    return out
