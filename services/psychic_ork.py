"""services/psychic_ork.py — психосилы Орков (WAAAGH!).

Орочьи психосилы = WAAAGH!-энергия. Чем больше орков рядом,
тем сильнее Вирдбой. Никакой Порчи, никакого Безумия —
только зелёная ярость.

ДИСЦИПЛИНЫ (2):
- waaagh (8)     — классические силы Вирдбоя
- mork_gork (8)  — силы Морка и Горка (Вуррбой, Психобой)
"""
from __future__ import annotations
import random
import re

DISCIPLINES = {
    "waaagh":    "WAAAGH! (Вирдбой)",
    "mork_gork": "Силы Морка и Горка (Вуррбой)",
}


PSY_POWERS = {
    # ============ WAAAGH (8) ============
    "ork_eadbanger": {"name": "Мозголом", "discipline": "waaagh",
        "min_rating": 1, "cost": 2, "type": "attack",
        "desc": "Атака: 2d10+5 E в разум одной цели.", "damage": "2d10+5"},
    "ork_frazzle": {"name": "Фраззл", "discipline": "waaagh",
        "min_rating": 1, "cost": 2, "type": "attack",
        "desc": "Атака: 2d10+4 E, оглушает цель.", "damage": "2d10+4"},
    "ork_da_jump": {"name": "Прыжок", "discipline": "waaagh",
        "min_rating": 2, "cost": 3, "type": "utility",
        "desc": "Телепортирует отряд орков в любую точку поля."},
    "ork_warpath": {"name": "Тропа Войны", "discipline": "waaagh",
        "min_rating": 2, "cost": 3, "type": "buff",
        "desc": "Все орки в зоне получают +1 A и ярость.",
        "buff": {"S": 10}},
    "ork_gift_of_waaagh": {"name": "Дар WAAAGH!", "discipline": "waaagh",
        "min_rating": 3, "cost": 3, "type": "buff",
        "desc": "Один орк получает +20 S на сцену.",
        "buff": {"S": 20}},
    "ork_psychic_vomit": {"name": "Психическая Блевотина", "discipline": "waaagh",
        "min_rating": 3, "cost": 4, "type": "attack",
        "desc": "Атака областью: 2d10+6 E, отравляет.", "damage": "2d10+6"},
    "ork_roar_of_mork": {"name": "Рёв Морка", "discipline": "waaagh",
        "min_rating": 4, "cost": 4, "type": "control",
        "desc": "Враги в зоне теряют действие от рёва."},
    "ork_blood_axe": {"name": "Кровавый Топор", "discipline": "waaagh",
        "min_rating": 5, "cost": 5, "type": "attack",
        "desc": "Призрачный топор Горка: 3d10+8 R по всем врагам.",
        "damage": "3d10+8"},

    # ============ MORK_GORK (8) ============
    "ork_power_vomit": {"name": "Мощная Блевотина", "discipline": "mork_gork",
        "min_rating": 1, "cost": 2, "type": "attack",
        "desc": "Атака: 2d10+5 E, сбивает с ног.", "damage": "2d10+5"},
    "ork_morks_roar": {"name": "Рёв Морка (Усиленный)", "discipline": "mork_gork",
        "min_rating": 2, "cost": 3, "type": "control",
        "desc": "Все враги в зоне получают -20 Ld и бегут."},
    "ork_ere_we_go": {"name": "Вперёд, парни!", "discipline": "mork_gork",
        "min_rating": 2, "cost": 3, "type": "buff",
        "desc": "Отряд орков получает +3 дюйма к движению и реролл чарджа."},
    "ork_waaagh_shout": {"name": "Крик WAAAGH!", "discipline": "mork_gork",
        "min_rating": 3, "cost": 4, "type": "buff",
        "desc": "Все орки в радиусе получают +1 A и Fearless.",
        "buff": {"S": 5, "WP": 5}},
    "ork_bash": {"name": "Затрещина", "discipline": "mork_gork",
        "min_rating": 3, "cost": 3, "type": "attack",
        "desc": "Атака: 2d10+6 I, игнорирует броню.", "damage": "2d10+6"},
    "ork_kunnin_plan": {"name": "Хитрая Мысль", "discipline": "mork_gork",
        "min_rating": 4, "cost": 4, "type": "utility",
        "desc": "Даёт оркам реролл одного броска в сцене."},
    "ork_bigga_brains": {"name": "Огромные Мозги", "discipline": "mork_gork",
        "min_rating": 4, "cost": 4, "type": "buff",
        "desc": "+15 Int, +15 WP на сцену.",
        "buff": {"Int": 15, "WP": 15}},
    "ork_warphead": {"name": "Варпоголовый", "discipline": "mork_gork",
        "min_rating": 5, "cost": 6, "type": "special",
        "desc": "Открывает варп-разлом: 3d10+7 E по всем врагам в зоне.",
        "damage": "3d10+7"},
}


def get_disciplines() -> dict:
    return dict(DISCIPLINES)


def _discipline_access(char: dict) -> set:
    if not isinstance(char, dict):
        return set()
    fid = str(char.get("faction_id", "")).lower()
    cid = str(char.get("career_id", "")).lower()
    if fid in ("ork", "orks", "orc"):
        return set(DISCIPLINES.keys())
    if "weirdboy" in cid or "wurrboy" in cid or "psyk" in cid:
        return set(DISCIPLINES.keys())
    return set()


def get_powers(char: dict) -> list:
    if not isinstance(char, dict):
        return []
    rating = int(char.get("psy_rating", 0) or 0)
    if rating <= 0:
        return []
    allowed = _discipline_access(char)
    if not allowed:
        return []
    out = []
    for pid, p in PSY_POWERS.items():
        if p.get("discipline") not in allowed:
            continue
        if int(p.get("min_rating", 1)) <= rating:
            out.append(pid)
    return out


def get_power(pid: str):
    return PSY_POWERS.get(pid)


def _roll_damage(expr: str) -> int:
    m = re.match(r"(\d+)d(\d+)([+\-]\d+)?", str(expr))
    if not m:
        return 0
    n, f = int(m.group(1)), int(m.group(2))
    total = sum(random.randint(1, f) for _ in range(n))
    if m.group(3):
        total += int(m.group(3))
    return total


def cast(char: dict, power_key: str) -> dict:
    if not isinstance(char, dict):
        return {"ok": False, "reason": "нет персонажа"}
    power = PSY_POWERS.get(power_key)
    if not power:
        return {"ok": False, "reason": "неизвестная сила"}

    allowed = _discipline_access(char)
    if power.get("discipline") not in allowed:
        return {"ok": False, "reason": "дисциплина недоступна"}

    rating = int(char.get("psy_rating", 0) or 0)
    if rating < int(power.get("min_rating", 1)):
        return {"ok": False, "reason": "недостаточный psy_rating"}

    cost = int(power.get("cost", 2))
    charge = int(char.get("psy_charge", 0) or 0)
    if charge < cost:
        return {"ok": False, "reason": "не хватает заряда"}

    wp = int((char.get("characteristics") or {}).get("WP", 30))
    roll = random.randint(1, 100)
    # У орков психотест: roll <= WP, крит.успех = дубль (11, 22, ...)
    success = roll <= wp
    crit_success = roll % 11 == 0 and roll <= 88  # дубли до 88
    crit_fail = roll >= 96
    char["psy_charge"] = charge - cost
    # Провал у орков = Перильная голова (урон себе), а не Безумие
    headbang_txt = ""
    if not success:
        dmg_self = random.randint(1, 5)
        w = char.setdefault("wounds", {})
        cur = int(w.get("current", 0) or 0)
        w["current"] = max(0, cur - dmg_self)
        headbang_txt = " [Перильная голова: -" + str(dmg_self) + " ран]"

    ptype = power.get("type", "utility")

    if ptype == "attack":
        if success:
            dmg = _roll_damage(power.get("damage", "1d10"))
            if crit_success:
                dmg *= 2
                return {"ok": True, "roll": roll, "success": True, "damage": dmg,
                        "text": power["name"] + " КРИТ! " + str(dmg) + " урона!"}
            return {"ok": True, "roll": roll, "success": True, "damage": dmg,
                    "text": power["name"] + " бьёт на " + str(dmg) + " урона"}
        return {"ok": True, "roll": roll, "success": False, "damage": 0,
                "text": power["name"] + " сорвалась." + headbang_txt}

    if ptype == "heal":
        if not success:
            return {"ok": True, "roll": roll, "success": False,
                    "text": power["name"] + " сорвалась." + headbang_txt}
        heal = _roll_damage(power.get("heal", "1d5"))
        w = char.setdefault("wounds", {})
        cur = int(w.get("current", 0) or 0)
        mx = int(w.get("max", cur) or cur)
        w["current"] = min(mx, cur + heal)
        return {"ok": True, "roll": roll, "success": True, "heal": heal,
                "text": power["name"] + ": +" + str(heal) + " ран"}

    if ptype == "buff":
        applied = power.get("buff", {}) or {}
        chars = char.setdefault("characteristics", {})
        for k, v in applied.items():
            if k in ("WS", "BS", "S", "T", "Ag", "Int", "Per", "WP", "Fel"):
                chars[k] = int(chars.get(k, 0) or 0) + int(v)
        return {"ok": True, "roll": roll, "success": True,
                "text": power["name"] + ": применено"}

    if ptype in ("control", "utility", "special"):
        if not success and ptype != "special":
            return {"ok": True, "roll": roll, "success": False,
                    "text": power["name"] + " сорвалась." + headbang_txt}
        return {"ok": True, "roll": roll, "success": True,
                "text": power["name"] + ": " + power.get("desc", "")}

    return {"ok": True, "roll": roll, "text": power["name"] + ": применено."}


def full_catalog(rating: int = 10, char: dict = None) -> dict:
    char = char or {}
    allowed = _discipline_access(char)
    out = {}
    for did, dname in DISCIPLINES.items():
        if did not in allowed:
            continue
        powers = []
        for pid, p in PSY_POWERS.items():
            if p.get("discipline") != did:
                continue
            powers.append({
                "id": pid,
                "name": p.get("name", pid),
                "desc": p.get("desc", ""),
                "cost": p.get("cost", 2),
                "type": p.get("type", "utility"),
                "min_rating": p.get("min_rating", 1),
                "available": int(p.get("min_rating", 1)) <= int(rating),
            })
        out[did] = {"name": dname, "powers": powers}
    return out
