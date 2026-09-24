# HOTFIX_15Y
# services/progression.py — правила прокачки Rogue Trader.
from __future__ import annotations


RANKS = [
    (0, "Ранг 1"), (2000, "Ранг 2"), (5000, "Ранг 3"),
    (9000, "Ранг 4"), (14000, "Ранг 5"), (20000, "Ранг 6"),
    (27000, "Ранг 7"), (35000, "Ранг 8"),
]

CHAR_COSTS = {
    "Simple":       [100, 250, 500],
    "Intermediate": [250, 500, 750],
    "Trained":      [500, 750, 1000],
    "Expert":       [750, 1000, 2500],
}

SKILL_COSTS = {"Trained": 100, "Experienced": 200, "Veteran": 300}
TALENT_COSTS = {"basic": 400, "prereq": 600, "universal": 750}

ARCHETYPE_CHARS = {
    "rogue_trader":  ["Fel", "Int", "Per"],
    "arch_militant": ["WS", "BS", "S", "T"],
    "astropath":     ["WP", "Per", "Int"],
    "explorator":    ["Int", "T", "Per"],
    "void_master":   ["Ag", "Int", "Per"],
    "missionary":    ["Fel", "WP", "S"],
    "navigator":     ["WP", "Int", "Per"],
    "seneschal":     ["Int", "Fel", "Per"],
}


def total_spent_xp(char):
    base = int(char.get("xp_spent_base", 0) or 0)
    extra = int(char.get("xp_spent", 0) or 0)
    return base + extra


def current_rank(char):
    spent = total_spent_xp(char)
    idx = 0
    for i, (threshold, _name) in enumerate(RANKS):
        if spent >= threshold:
            idx = i
    return idx + 1, RANKS[idx][1]


def rank_progress(char):
    spent = total_spent_xp(char)
    cur = 0
    nxt = None
    for threshold, _name in RANKS:
        if spent >= threshold:
            cur = threshold
        elif nxt is None:
            nxt = threshold
    if nxt is None:
        nxt = cur
    return spent, cur, nxt


def is_proficient(char, stat):
    arch = str(char.get("archetype_id") or char.get("archetype") or "").lower()
    lst = ARCHETYPE_CHARS.get(arch, [])
    return stat in lst


def char_advance_level(char, stat):
    adv = char.setdefault("advances", {})
    per = adv.setdefault(stat, {})
    return int(per.get("count", 0) or 0)


def char_advance_cost(char, stat):
    lvl = char_advance_level(char, stat)
    if lvl >= 3:
        return -1
    tier = "Simple" if is_proficient(char, stat) else "Expert"
    costs = CHAR_COSTS[tier]
    return costs[lvl]


def buy_char_advance(char, stat):
    cost = char_advance_cost(char, stat)
    if cost < 0:
        return False, "Характеристика уже на максимуме (+20)."
    if int(char.get("xp", 0) or 0) < cost:
        return False, "Недостаточно XP (нужно " + str(cost) + ")."
    char["xp"] = int(char.get("xp", 0)) - cost
    char["xp_spent"] = int(char.get("xp_spent", 0)) + cost
    chars = char.setdefault("characteristics", {})
    chars[stat] = int(chars.get(stat, 0)) + 5
    adv = char.setdefault("advances", {})
    per = adv.setdefault(stat, {})
    per["count"] = int(per.get("count", 0)) + 1
    return True, "+5 к " + stat + " за " + str(cost) + " XP."


def skill_cost(next_level):
    return SKILL_COSTS.get(next_level, 100)


def buy_skill(char, name):
    skills = char.setdefault("skills", [])
    found = None
    for s in skills:
        if isinstance(s, dict) and str(s.get("name")) == name:
            found = s
            break
        if isinstance(s, str) and s == name:
            found = {"name": s, "level": "Trained"}
            skills.remove(s)
            skills.append(found)
            break
    if found is None:
        cost = SKILL_COSTS["Trained"]
        if int(char.get("xp", 0)) < cost:
            return False, "Недостаточно XP (нужно " + str(cost) + ")."
        char["xp"] = int(char["xp"]) - cost
        char["xp_spent"] = int(char.get("xp_spent", 0)) + cost
        skills.append({"name": name, "level": "Trained"})
        return True, "Навык " + name + " (Trained) за " + str(cost) + " XP."
    level = str(found.get("level") or "Trained")
    order = ["Trained", "Experienced", "Veteran"]
    if level not in order:
        level = "Trained"
    idx = order.index(level)
    if idx >= len(order) - 1:
        return False, "Навык уже на максимуме (Veteran +20)."
    nxt = order[idx + 1]
    cost = SKILL_COSTS[nxt]
    if int(char.get("xp", 0)) < cost:
        return False, "Недостаточно XP (нужно " + str(cost) + ")."
    char["xp"] = int(char["xp"]) - cost
    char["xp_spent"] = int(char.get("xp_spent", 0)) + cost
    found["level"] = nxt
    return True, "Навык " + name + " -> " + nxt + " за " + str(cost) + " XP."


def buy_talent(char, name, cost):
    if int(char.get("xp", 0)) < cost:
        return False, "Недостаточно XP (нужно " + str(cost) + ")."
    tal = char.setdefault("talents", [])
    if any(str(t) == name for t in tal):
        return False, "Талант уже взят."
    char["xp"] = int(char["xp"]) - cost
    char["xp_spent"] = int(char.get("xp_spent", 0)) + cost
    tal.append(name)
    return True, "Талант " + name + " за " + str(cost) + " XP."


def buy_psy(char, name, cost):
    if int(char.get("psy_rating", 0) or 0) <= 0:
        return False, "Нет психорейтинга."
    if int(char.get("xp", 0)) < cost:
        return False, "Недостаточно XP (нужно " + str(cost) + ")."
    psy = char.setdefault("psychic_powers", [])
    if any(str(p) == name for p in psy):
        return False, "Техника уже известна."
    char["xp"] = int(char["xp"]) - cost
    char["xp_spent"] = int(char.get("xp_spent", 0)) + cost
    psy.append(name)
    return True, "Психосила " + name + " за " + str(cost) + " XP."


def available_psy_value(char):
    rank, _ = current_rank(char)
    if rank >= 6:
        return 400
    if rank >= 5:
        return 300
    if rank >= 3:
        return 200
    return 100
