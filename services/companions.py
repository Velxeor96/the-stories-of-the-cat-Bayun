# PATCH_28
"""services/companions.py — компаньоны игрока."""
from __future__ import annotations
import random


PRESET_COMPANIONS = {
    "eldar": [
        {"name": "Аин-Литас", "role": "Рейнджер", "hp": 10, "weapon": "Сюрикен-катапульта"},
        {"name": "Виэль-Морн", "role": "Провидец", "hp": 8, "weapon": "Сюрикен-пистолет"},
    ],
    "imperium": [
        {"name": "Сержант Кроу", "role": "Гвардеец", "hp": 12, "weapon": "Лазган"},
        {"name": "Сестра Марта", "role": "Сестра Битвы", "hp": 11, "weapon": "Болтер"},
    ],
    "chaos": [
        {"name": "Ксав'ир", "role": "Культист", "hp": 9, "weapon": "Автопистолет"},
    ],
    "orks": [
        {"name": "Грубник", "role": "Ноб", "hp": 14, "weapon": "Чоппа"},
        {"name": "Снагга", "role": "Гретчин", "hp": 5, "weapon": "Нож"},
    ],
    "tau": [
        {"name": "Шас'ла", "role": "Воин Огня", "hp": 10, "weapon": "Импульсная винтовка"},
    ],
    "necrons": [
        {"name": "Слуга-скарабей", "role": "Скарабей", "hp": 6, "weapon": "Клешни"},
    ],
}


def get_companions(char: dict) -> list:
    if not isinstance(char, dict):
        return []
    comp = char.get("companions")
    if not isinstance(comp, list):
        comp = []
        char["companions"] = comp
    return comp


def add_companion(char: dict, name: str, role: str, hp: int,
                  weapon: str = "") -> None:
    comp = get_companions(char)
    for c in comp:
        if isinstance(c, dict) and c.get("name") == name:
            return
    comp.append({
        "name": name, "role": role, "hp": int(hp),
        "hp_max": int(hp), "weapon": weapon or "Кулак",
        "alive": True,
    })


def remove_companion(char: dict, index: int) -> bool:
    comp = get_companions(char)
    if index < 0 or index >= len(comp):
        return False
    comp.pop(index)
    return True


def get_preset(faction_id: str) -> list:
    return list(PRESET_COMPANIONS.get(faction_id, []))


def companion_attack(comp: dict, base_skill: int = 30) -> dict:
    if not isinstance(comp, dict):
        return {"error": "нет компаньона"}
    if not comp.get("alive", True):
        return {"error": "компаньон мёртв"}
    roll = random.randint(1, 100)
    hit = roll <= base_skill
    dmg = random.randint(1, 10) + 2 if hit else 0
    return {"roll": roll, "hit": hit, "damage": dmg,
            "name": comp.get("name"), "weapon": comp.get("weapon")}
