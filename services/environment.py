# PATCH_25
"""services/environment.py — погода, время, среда."""
from __future__ import annotations
import random

WEATHERS = ["Ясно", "Туман", "Дождь", "Гроза", "Пыльная буря", "Снег"]
TIMES = ["Утро", "День", "Вечер", "Ночь"]
ATMOSPHERES = ["Спокойно", "Тревожно", "Зловеще", "Мертвенно тихо"]

PER_MODS = {"Ясно": 0, "Туман": -10, "Дождь": -5, "Гроза": -10,
            "Пыльная буря": -20, "Снег": -10}
TIME_MODS = {"Утро": 0, "День": 0, "Вечер": -5, "Ночь": -20}


def get_env(char: dict) -> dict:
    if not isinstance(char, dict):
        return {"weather": "Ясно", "time": "День", "atmosphere": "Спокойно"}
    e = char.get("environment")
    if not isinstance(e, dict):
        e = {"weather": random.choice(WEATHERS),
             "time": random.choice(TIMES),
             "atmosphere": random.choice(ATMOSPHERES)}
        char["environment"] = e
    return e


def rotate(char: dict) -> dict:
    e = get_env(char)
    e["weather"] = random.choice(WEATHERS)
    e["time"] = random.choice(TIMES)
    e["atmosphere"] = random.choice(ATMOSPHERES)
    return e


def perception_mod(char: dict) -> int:
    e = get_env(char)
    return PER_MODS.get(e.get("weather", ""), 0) + TIME_MODS.get(e.get("time", ""), 0)


def env_summary(char: dict) -> str:
    e = get_env(char)
    mod = perception_mod(char)
    mod_str = ("+" + str(mod)) if mod >= 0 else str(mod)
    return (str(e.get("time")) + ", " + str(e.get("weather"))
            + ", " + str(e.get("atmosphere"))
            + " (Per " + mod_str + ")")
