"""services/psychic_navigator.py — силы Навигатора.

Особые способности, дающиеся мутацией третьего глаза.
"""
from __future__ import annotations
import random
import re

DISCIPLINES = {
    "navigator": "Силы Навигатора",
}

PSY_POWERS = {
    "lidless_stare": {
        "name": "Взор без век", "discipline": "navigator",
        "desc": "Раскрывает третий глаз. Смертельная атака взглядом: 2d10+8 E.",
        "cost": 4, "type": "attack", "min_rating": 1,
        "damage": "2d10+8",
    },
    "gaze_abyss": {
        "name": "Взор в бездну", "discipline": "navigator",
        "desc": "Видит Варп напрямую. Даёт +20 к Навигации (Варп) на сцену.",
        "cost": 3, "type": "buff", "min_rating": 1,
        "buff": {"Int": 10},
    },
    "heldrane_hands": {
        "name": "Руки Хелдрейна", "discipline": "navigator",
        "desc": "Управляет Варп-потоками. Перебрасывает провал Навигации.",
        "cost": 3, "type": "utility", "min_rating": 1,
    },
    "void_watcher": {
        "name": "Наблюдатель Пустоты", "discipline": "navigator",
        "desc": "Видит корабли и объекты на дистанции 100 VU.",
        "cost": 2, "type": "utility", "min_rating": 1,
    },
    "the_eye": {
        "name": "Око", "discipline": "navigator",
        "desc": "Прямой взгляд в реальность. Цель в ужасе бежит.",
        "cost": 4, "type": "control", "min_rating": 3,
    },
    "navigator_wings": {
        "name": "Крылья Навигатора", "discipline": "navigator",
        "desc": "Полёт в Варпе и реальности на сцену.",
        "cost": 3, "type": "utility", "min_rating": 3,
    },
    "beyond_veil": {
        "name": "За завесой", "discipline": "navigator",
        "desc": "Прячется от Варп-сущностей. +20 к скрытности в Варпе.",
        "cost": 3, "type": "buff", "min_rating": 3,
        "buff": {"Ag": 10},
    },
    "warp_eye": {
        "name": "Варп-глаз", "discipline": "navigator",
        "desc": "Атака: 3d10+10 E, игнорирует 6 AP.",
        "cost": 5, "type": "attack", "min_rating": 5,
        "damage": "3d10+10",
    },
    "cruel_fate": {
        "name": "Жестокая судьба", "discipline": "navigator",
        "desc": "Проклинает цель: -20 на все броски на сцену.",
        "cost": 4, "type": "control", "min_rating": 5,
    },
    "bones_navigator": {
        "name": "Кости Навигатора", "discipline": "navigator",
        "desc": "Иммунитет к Страху и Порче на сцену.",
        "cost": 3, "type": "buff", "min_rating": 3,
    },
    "step_beyond": {
        "name": "Шаг за грань", "discipline": "navigator",
        "desc": "Телепортация на 50 м.",
        "cost": 5, "type": "utility", "min_rating": 5,
    },
    "course_untravelled": {
        "name": "Непройденный курс", "discipline": "navigator",
        "desc": "Находит оптимальный путь через Варп. Сокращает время прыжка в 2 раза.",
        "cost": 4, "type": "utility", "min_rating": 5,
    },
}


def get_disciplines() -> dict:
    return dict(DISCIPLINES)


def get_powers(char: dict) -> list:
    if not isinstance(char, dict):
        return []
    rating = int(char.get("psy_rating", 0) or 0)
    if rating <= 0:
        return []
    return [pid for pid, p in PSY_POWERS.items()
            if int(p.get("min_rating", 1)) <= rating]


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
    rating = int(char.get("psy_rating", 0) or 0)
    if rating < int(power.get("min_rating", 1)):
        return {"ok": False, "reason": "недостаточный psy_rating"}
    cost = int(power.get("cost", 2))
    charge = int(char.get("psy_charge", 0) or 0)
    if charge < cost:
        return {"ok": False, "reason": "не хватает заряда"}

    wp = int((char.get("characteristics") or {}).get("WP", 30))
    roll = random.randint(1, 100)
    success = roll <= wp
    char["psy_charge"] = charge - cost
    ptype = power.get("type", "utility")

    if ptype == "attack":
        if success:
            dmg = _roll_damage(power.get("damage", "1d10"))
            return {"ok": True, "roll": roll, "success": True, "damage": dmg,
                    "text": power["name"] + " бьёт на " + str(dmg) + " урона."}
        return {"ok": True, "roll": roll, "success": False, "damage": 0,
                "text": power["name"] + " сорвалась."}

    if ptype in ("control", "utility", "buff"):
        if not success:
            char["insanity"] = int(char.get("insanity", 0) or 0) + 1
            return {"ok": True, "roll": roll, "success": False,
                    "text": power["name"] + " сорвалась. +1 Безумие."}
        applied = power.get("buff", {}) or {}
        chars = char.setdefault("characteristics", {})
        for k, v in applied.items():
            if k in ("WS", "BS", "S", "T", "Ag", "Int", "Per", "WP", "Fel"):
                chars[k] = int(chars.get(k, 0) or 0) + int(v)
        return {"ok": True, "roll": roll, "success": True,
                "text": power["name"] + ": " + power.get("desc", "")}

    return {"ok": True, "roll": roll, "text": power["name"] + ": применено."}


def full_catalog(rating: int = 10) -> dict:
    powers = []
    for pid, p in PSY_POWERS.items():
        powers.append({
            "id": pid, "name": p.get("name", pid),
            "desc": p.get("desc", ""), "cost": p.get("cost", 2),
            "type": p.get("type", "utility"),
            "min_rating": p.get("min_rating", 1),
            "available": int(p.get("min_rating", 1)) <= int(rating),
        })
    return {"navigator": {"name": "Силы Навигатора", "powers": powers}}
