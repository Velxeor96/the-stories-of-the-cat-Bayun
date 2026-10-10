"""services/psychic_tyranid.py — психосилы Тиранидов (Hive Mind).

Тираниды используют единое сознание — Разум Улья. Никаких ритуалов
и favour-механик: сила Улья работает через синапс и биомассу.

ДИСЦИПЛИНЫ (3):
- hive_mind (8)   — синапс, приказы, командные баффы
- broodmind (8)   — психические атаки через Shadow in the Warp
- biomancy (8)    — изменение плоти, регенерация, биооружие

Тираниды не копят Порчу и не сходят с ума — они часть Улья.
"""
from __future__ import annotations
import random
import re

DISCIPLINES = {
    "hive_mind":  "Разум Улья (Синапс)",
    "broodmind":  "Разум Выводка (Тень в Варпе)",
    "biomancy":   "Биомантия Тиранид",
}


PSY_POWERS = {
    # ============ HIVE MIND (8) ============
    "tyr_synapse": {"name": "Синапс", "discipline": "hive_mind",
        "min_rating": 1, "cost": 2, "type": "buff",
        "desc": "Все Тираниды в зоне получают +10 WP и иммунитет к страху.",
        "buff": {"WP": 10}},
    "tyr_dominion": {"name": "Владычество", "discipline": "hive_mind",
        "min_rating": 2, "cost": 3, "type": "buff",
        "desc": "Увеличивает радиус синапса, все миньоны подчиняются.",
        "buff": {"WP": 5}},
    "tyr_catalyst": {"name": "Катализатор", "discipline": "hive_mind",
        "min_rating": 2, "cost": 3, "type": "buff",
        "desc": "Союзное существо получает 5+ Feel No Pain.",
        "buff": {"T": 10}},
    "tyr_onslaught": {"name": "Натиск", "discipline": "hive_mind",
        "min_rating": 3, "cost": 3, "type": "buff",
        "desc": "Существо может бежать и атаковать в тот же ход.",
        "buff": {"S": 5}},
    "tyr_warp_speed": {"name": "Скорость Варпа", "discipline": "hive_mind",
        "min_rating": 3, "cost": 3, "type": "buff",
        "desc": "+15 к Ag на сцену.",
        "buff": {"Ag": 15}},
    "tyr_the_horror": {"name": "Ужас", "discipline": "hive_mind",
        "min_rating": 3, "cost": 4, "type": "control",
        "desc": "Враг в зоне замирает от первобытного ужаса."},
    "tyr_shadow_attack": {"name": "Удар Тени", "discipline": "hive_mind",
        "min_rating": 4, "cost": 4, "type": "attack",
        "desc": "Атака: 2d10+6 E через Тень в Варпе.", "damage": "2d10+6"},
    "tyr_hive_command": {"name": "Приказ Улья", "discipline": "hive_mind",
        "min_rating": 5, "cost": 5, "type": "utility",
        "desc": "Все Тираниды в огромной зоне исполняют один приказ одновременно."},

    # ============ BROODMIND (8) ============
    "tyr_psychic_scream": {"name": "Психический Крик", "discipline": "broodmind",
        "min_rating": 1, "cost": 2, "type": "attack",
        "desc": "Атака областью: 1d10+4 E, оглушает.", "damage": "1d10+4"},
    "tyr_psychic_shriek": {"name": "Психический Вопль", "discipline": "broodmind",
        "min_rating": 2, "cost": 3, "type": "attack",
        "desc": "Атака: 2d10+5 E, игнорирует броню.", "damage": "2d10+5"},
    "tyr_mind_worm": {"name": "Червь Разума", "discipline": "broodmind",
        "min_rating": 2, "cost": 3, "type": "control",
        "desc": "Психический червь проникает в сознание цели, -20 WP."},
    "tyr_paroxysm": {"name": "Пароксизм", "discipline": "broodmind",
        "min_rating": 3, "cost": 3, "type": "control",
        "desc": "Цель атакует в последнюю очередь, -10 WS и BS."},
    "tyr_hemorrhage": {"name": "Кровотечение", "discipline": "broodmind",
        "min_rating": 3, "cost": 4, "type": "attack",
        "desc": "Атака: 2d10+7 E, вызывает внутреннее кровотечение.",
        "damage": "2d10+7"},
    "tyr_psychic_overload": {"name": "Психическая Перегрузка", "discipline": "broodmind",
        "min_rating": 4, "cost": 4, "type": "attack",
        "desc": "Атака: 3d10+5 E в разум врага.", "damage": "3d10+5"},
    "tyr_warp_blast": {"name": "Варп-Взрыв", "discipline": "broodmind",
        "min_rating": 4, "cost": 5, "type": "attack",
        "desc": "Атака областью: 2d10+8 E.", "damage": "2d10+8"},
    "tyr_shadow_warp": {"name": "Тень в Варпе", "discipline": "broodmind",
        "min_rating": 5, "cost": 6, "type": "control",
        "desc": "Все вражеские псайкеры в зоне не могут использовать силы (1 раунд)."},

    # ============ BIOMANCY (8) ============
    "tyr_regenerate": {"name": "Регенерация", "discipline": "biomancy",
        "min_rating": 1, "cost": 2, "type": "heal",
        "desc": "Восстанавливает 2d10 ран.", "heal": "2d10"},
    "tyr_adrenal": {"name": "Адреналиновые Железы", "discipline": "biomancy",
        "min_rating": 1, "cost": 2, "type": "buff",
        "desc": "+10 S на сцену.", "buff": {"S": 10}},
    "tyr_chitin": {"name": "Хитиновая Броня", "discipline": "biomancy",
        "min_rating": 2, "cost": 3, "type": "buff",
        "desc": "+5 AP на сцену.", "buff": {"AP": 5}},
    "tyr_toxin": {"name": "Токсичные Мешки", "discipline": "biomancy",
        "min_rating": 2, "cost": 3, "type": "buff",
        "desc": "Атаки накладывают яд (доп. 1d5 урона за ход).",
        "buff": {"S": 5}},
    "tyr_bio_plasma": {"name": "Био-Плазма", "discipline": "biomancy",
        "min_rating": 3, "cost": 4, "type": "attack",
        "desc": "Атака: 2d10+7 E, игнорирует 5 AP.", "damage": "2d10+7"},
    "tyr_bonesword_surge": {"name": "Всплеск Костяного Клинка", "discipline": "biomancy",
        "min_rating": 3, "cost": 4, "type": "attack",
        "desc": "Атака в ближнем бою: 3d10+5 R.", "damage": "3d10+5"},
    "tyr_enhanced_senses": {"name": "Обострённые Чувства", "discipline": "biomancy",
        "min_rating": 4, "cost": 4, "type": "buff",
        "desc": "+20 к Per и инициативе на сцену.",
        "buff": {"Per": 20, "Ag": 10}},
    "tyr_apex_predator": {"name": "Высший Хищник", "discipline": "biomancy",
        "min_rating": 5, "cost": 6, "type": "buff",
        "desc": "Существо становится высшим хищником: +20 S, +20 T, +20 Ag.",
        "buff": {"S": 20, "T": 20, "Ag": 20}},
}


def get_disciplines() -> dict:
    return dict(DISCIPLINES)


def _discipline_access(char: dict) -> set:
    if not isinstance(char, dict):
        return set()
    fid = str(char.get("faction_id", "")).lower()
    if fid in ("tyranid", "tyranids"):
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

    wp = int((char.get("characteristics") or {}).get("WP", 40))
    roll = random.randint(1, 100)
    success = roll <= wp
    char["psy_charge"] = charge - cost
    # Тираниды не получают Безумие при провале — они часть Улья.
    ptype = power.get("type", "utility")

    if ptype == "attack":
        if success:
            dmg = _roll_damage(power.get("damage", "1d10"))
            return {"ok": True, "roll": roll, "success": True, "damage": dmg,
                    "text": power["name"] + " бьёт на " + str(dmg) + " урона"}
        return {"ok": True, "roll": roll, "success": False, "damage": 0,
                "text": power["name"] + " рассеялась в Варпе."}

    if ptype == "heal":
        if not success:
            return {"ok": True, "roll": roll, "success": False,
                    "text": power["name"] + " рассеялась в Варпе."}
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
        buffs = char.setdefault("psy_buffs", {})
        for k, v in applied.items():
            if k == "AP":
                buffs["AP"] = int(buffs.get("AP", 0)) + int(v)
        return {"ok": True, "roll": roll, "success": True,
                "text": power["name"] + ": применено"}

    if ptype in ("control", "utility", "special"):
        if not success and ptype != "special":
            return {"ok": True, "roll": roll, "success": False,
                    "text": power["name"] + " рассеялась в Варпе."}
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
