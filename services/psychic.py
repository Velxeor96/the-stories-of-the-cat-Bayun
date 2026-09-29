# PATCH_28
"""services/psychic.py — пси-силы."""
from __future__ import annotations
import random

PSY_POWERS = {
    "smite": {
        "name": "Разрушитель",
        "desc": "Психический удар по врагу.",
        "cost": 2, "damage": "1d10+5", "type": "attack",
    },
    "fortune": {
        "name": "Фортуна",
        "desc": "+10 к следующему броску.",
        "cost": 2, "type": "buff",
    },
    "foresight": {
        "name": "Предвидение",
        "desc": "+20 к следующему броску.",
        "cost": 3, "type": "buff",
    },
    "heal": {
        "name": "Восстановление",
        "desc": "Лечит 1d5 ран.",
        "cost": 2, "heal": "1d5", "type": "heal",
    },
}


def get_powers(char: dict) -> list:
    if not isinstance(char, dict):
        return []
    rating = int(char.get("psy_rating", 0) or 0)
    if rating <= 0:
        return []
    out = ["smite", "fortune"]
    if rating >= 3:
        out.append("heal")
    if rating >= 5:
        out.append("foresight")
    return out


def get_charge(char: dict) -> int:
    if not isinstance(char, dict):
        return 0
    return int(char.get("psy_charge", 0) or 0)


def regen_charge(char: dict) -> None:
    if not isinstance(char, dict):
        return
    rating = int(char.get("psy_rating", 0) or 0)
    if rating > 0:
        char["psy_charge"] = rating * 2


def cast(char: dict, power_key: str) -> dict:
    if power_key not in PSY_POWERS:
        return {"ok": False, "reason": "неизвестная сила"}
    power = PSY_POWERS[power_key]
    cost = int(power.get("cost", 2))
    charge = get_charge(char)
    if charge < cost:
        return {"ok": False, "reason": "не хватает заряда",
                "charge": charge, "need": cost}
    # бросок WP против сложности
    wp = int((char.get("characteristics") or {}).get("WP", 30))
    roll = random.randint(1, 100)
    success = roll <= wp
    char["psy_charge"] = charge - cost

    if power["type"] == "attack":
        if success:
            import re
            m = re.match(r"(\d+)d(\d+)([+\-]\d+)?", power.get("damage", "1d10"))
            dmg = 0
            if m:
                n, f = int(m.group(1)), int(m.group(2))
                dmg = sum(random.randint(1, f) for _ in range(n))
                if m.group(3):
                    dmg += int(m.group(3))
            return {"ok": True, "roll": roll, "damage": dmg,
                    "text": "Разрушитель бьёт на " + str(dmg) + " урона."}
        else:
            # варп-парадокс
            char["insanity"] = int(char.get("insanity", 0) or 0) + 1
            return {"ok": True, "roll": roll, "damage": 0,
                    "text": "Сила сорвалась. +1 Безумие."}

    if power["type"] == "buff":
        bonus = 10 if power_key == "fortune" else 20
        char["psy_buff"] = int(char.get("psy_buff", 0) or 0) + bonus
        return {"ok": True, "roll": roll,
                "text": power["name"] + " +" + str(bonus)
                + " к следующему броску."}

    if power["type"] == "heal":
        import re
        m = re.match(r"(\d+)d(\d+)", power.get("heal", "1d5"))
        heal = 1
        if m:
            n, f = int(m.group(1)), int(m.group(2))
            heal = sum(random.randint(1, f) for _ in range(n))
        w = char.setdefault("wounds", {})
        cur = int(w.get("current", 0) or 0)
        mx = int(w.get("max", cur) or cur)
        w["current"] = min(mx, cur + heal)
        return {"ok": True, "roll": roll, "heal": heal,
                "text": "Восстановление: +" + str(heal) + " ран."}

    return {"ok": True, "text": "Сила применена."}
