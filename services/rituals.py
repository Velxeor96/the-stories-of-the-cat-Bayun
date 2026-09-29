# PATCH_30
"""services/rituals.py — ритуалы фракций."""
from __future__ import annotations
import random

RITUALS = {
    "imperium": [
        ("Литургия Императору", "Восстановить 1d5 ран.", "heal"),
        ("Помазание", "Снять 1 страх.", "remove_fear"),
        ("Молитва перед боем", "+10 к следующему броску.", "buff"),
    ],
    "chaos": [
        ("Кровавый обряд", "+1d10 к атаке, но +1 Порча.", "chaos"),
        ("Шёпот Тзинча", "Узнать правду о NPC, но +1 Безумие.", "chaos"),
        ("Обряд Нургла", "Иммунитет к яду на сцену, +1 Порча.", "chaos"),
    ],
    "eldar": [
        ("Медитация на Камень Души", "Восстановить заряд пси-сил.", "psy_restore"),
        ("Путь Провидца", "+20 к следующему Per-броску.", "buff"),
        ("Песнь Кости", "Починить один артефакт.", "repair"),
    ],
    "orks": [
        ("ВАААГХ!", "+10 к S на следующий бой.", "buff"),
        ("Покрасить что-нибудь", "+5 к BS на сцену.", "buff"),
    ],
    "tau": [
        ("Кастовое служение", "+10 к Fel на сцену.", "buff"),
        ("Тау'ва", "Снять 2 страха.", "remove_fear"),
    ],
    "necrons": [
        ("Спящее пробуждение", "Восстановить 1d5 ран.", "heal"),
        ("Приказ династии", "+10 к Int на сцену.", "buff"),
    ],
    "drukhari": [
        ("Церемония боли", "Лечит 1d10 ран, но +1 Безумие.", "pain"),
        ("Кабальный обряд", "+20 к Intimidate, но -5 Fel.", "buff"),
    ],
}


def list_rituals(faction_id: str) -> list:
    return RITUALS.get(faction_id, [])


def perform(char: dict, ritual_name: str) -> dict:
    fid = str((char.get("faction_id") or "")) if isinstance(char, dict) else ""
    pool = RITUALS.get(fid, [])
    for r in pool:
        if r[0] == ritual_name:
            return _apply(char, r)
    return {"ok": False, "text": "Такого ритуала нет в твоей традиции."}


def _apply(char: dict, ritual: tuple) -> dict:
    name, desc, kind = ritual
    wp = int((char.get("characteristics") or {}).get("WP", 30))
    roll = random.randint(1, 100)
    success = roll <= wp + 20

    if not success:
        return {"ok": True, "roll": roll, "text": "Ритуал не сработал."}

    if kind == "heal":
        heal = random.randint(1, 5)
        w = char.setdefault("wounds", {})
        cur = int(w.get("current", 0) or 0)
        mx = int(w.get("max", cur) or cur)
        w["current"] = min(mx, cur + heal)
        return {"ok": True, "roll": roll,
                "text": name + ": восстановлено " + str(heal) + " ран."}

    if kind == "remove_fear":
        char["fear_rating"] = max(0, int(char.get("fear_rating", 0) or 0) - 1)
        return {"ok": True, "roll": roll, "text": name + ": страх отступил."}

    if kind == "buff":
        char["ritual_buff"] = int(char.get("ritual_buff", 0) or 0) + 10
        return {"ok": True, "roll": roll,
                "text": name + ": +10 к следующему броску."}

    if kind == "psy_restore":
        try:
            from services.psychic import regen_charge
            regen_charge(char)
        except Exception:
            pass
        return {"ok": True, "roll": roll,
                "text": name + ": заряд пси-сил восстановлен."}

    if kind == "chaos":
        char["corruption"] = min(100, int(char.get("corruption", 0) or 0) + 1)
        return {"ok": True, "roll": roll,
                "text": name + ": +1 Порча."}

    if kind == "pain":
        heal = random.randint(1, 10)
        w = char.setdefault("wounds", {})
        cur = int(w.get("current", 0) or 0)
        mx = int(w.get("max", cur) or cur)
        w["current"] = min(mx, cur + heal)
        char["insanity"] = min(100, int(char.get("insanity", 0) or 0) + 1)
        return {"ok": True, "roll": roll,
                "text": name + ": +" + str(heal) + " ран, +1 Безумие."}

    if kind == "repair":
        return {"ok": True, "roll": roll,
                "text": name + ": артефакт восстановлен."}

    return {"ok": True, "roll": roll, "text": name + ": обряд завершён."}
