# PATCH_25
"""services/ship.py — корабль Вольного Торговца."""
from __future__ import annotations
import random


DEFAULT_SHIP = {
    "name": "«Неустрашимый»",
    "class": "Лёгкий крейсер",
    "type": "Рейдер",
    "description": "Корабль династии, видавший лучшие дни.",
    "hull": 100, "hull_max": 100,
    "crew": 25000, "crew_max": 30000,
    "morale": 80, "morale_max": 100,
    "fuel": 100, "fuel_max": 100,
    "supplies": 100, "supplies_max": 100,
    "weapons": ["Портовые макропушки", "Носовые торпеды"],
    "features": ["Геллер-поле", "Варп-двигатель", "Библиотека"],
    "status": "В строю",
}


def get_ship(char: dict) -> dict:
    if not isinstance(char, dict):
        return dict(DEFAULT_SHIP)
    s = char.get("ship")
    if not isinstance(s, dict):
        s = dict(DEFAULT_SHIP)
        char["ship"] = s
    for k, v in DEFAULT_SHIP.items():
        if k not in s:
            s[k] = v
    return s


def warp_travel(char: dict, distance_ly: int = 5) -> dict:
    s = get_ship(char)
    fuel_cost = max(1, int(distance_ly) * 2)
    if int(s.get("fuel", 0)) < fuel_cost:
        return {"ok": False, "reason": "Недостаточно топлива",
                "fuel_cost": fuel_cost}
    s["fuel"] = int(s["fuel"]) - fuel_cost
    roll = random.randint(1, 100)
    if roll <= 5:
        s["hull"] = max(0, int(s["hull"]) - 15)
        return {"ok": True, "event": "Демоническая атака! Корпус повреждён.",
                "fuel_cost": fuel_cost, "hull": s["hull"], "roll": roll}
    if roll <= 15:
        loss = random.randint(100, 500)
        s["crew"] = max(0, int(s["crew"]) - loss)
        return {"ok": True, "event": "Варп-шторм. Потери среди экипажа: "
                + str(loss), "fuel_cost": fuel_cost, "roll": roll}
    return {"ok": True, "event": "Прыжок прошёл гладко.",
            "fuel_cost": fuel_cost, "roll": roll}


def repair(char: dict, amount: int = 20) -> dict:
    s = get_ship(char)
    if int(s.get("supplies", 0)) < 5:
        return {"ok": False, "reason": "Недостаточно припасов"}
    s["supplies"] = int(s["supplies"]) - 5
    s["hull"] = min(int(s["hull_max"]),
                    int(s["hull"]) + int(amount))
    return {"ok": True, "hull": s["hull"]}


def requisition(char: dict) -> dict:
    s = get_ship(char)
    if int(s.get("supplies", 0)) < 10:
        return {"ok": False, "reason": "Недостаточно припасов"}
    s["supplies"] = int(s["supplies"]) - 10
    gold = random.randint(50, 200)
    char["money"] = int(char.get("money", 0) or 0) + gold
    return {"ok": True, "gold": gold, "money": char["money"]}


def ship_summary(char: dict) -> str:
    s = get_ship(char)
    return ("Корабль «" + str(s.get("name")) + "» ("
            + str(s.get("class")) + "). "
            + "Корпус " + str(s.get("hull")) + "/" + str(s.get("hull_max"))
            + ", экипаж " + str(s.get("crew")) + "/" + str(s.get("crew_max"))
            + ", мораль " + str(s.get("morale"))
            + ", топливо " + str(s.get("fuel"))
            + ", припасы " + str(s.get("supplies")))
