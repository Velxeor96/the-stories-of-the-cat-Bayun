"""services/psychic.py — пси-силы (24 силы, 5 дисциплин)."""
from __future__ import annotations
import random
import re

DISCIPLINES = {
    "biomancy":    "Биомантия",
    "pyromancy":   "Пиромантия",
    "telekinesis": "Телекинез",
    "telepathy":   "Телепатия",
    "divination":  "Прорицание",
}

# Каждая сила: id -> {name, discipline, desc, cost, type, min_rating, ...}
PSY_POWERS = {
    # === БИОМАНТИЯ ===
    "iron_arm": {
        "name": "Железная плоть", "discipline": "biomancy",
        "desc": "+10 к Выносливости на следующую сцену.",
        "cost": 2, "type": "buff", "min_rating": 1,
        "buff": {"T": 10},
    },
    "swiftness": {
        "name": "Ускорение", "discipline": "biomancy",
        "desc": "+10 к Ловкости на следующую сцену.",
        "cost": 2, "type": "buff", "min_rating": 1,
        "buff": {"Ag": 10},
    },
    "endurance": {
        "name": "Живучесть", "discipline": "biomancy",
        "desc": "Восстанавливает 1d5 ран.",
        "cost": 2, "type": "heal", "min_rating": 1,
        "heal": "1d5",
    },
    "regenerate": {
        "name": "Регенерация", "discipline": "biomancy",
        "desc": "Восстанавливает 2d5 ран. Требует psy_rating 3+.",
        "cost": 4, "type": "heal", "min_rating": 3,
        "heal": "2d5",
    },
    "blood_boil": {
        "name": "Кровяное вскипание", "discipline": "biomancy",
        "desc": "Атака: 2d10+5 E. При провале — 1 рана себе.",
        "cost": 4, "type": "attack", "min_rating": 5,
        "damage": "2d10+5", "self_damage_on_fail": 1,
    },

    # === ПИРОМАНТИЯ ===
    "fireball": {
        "name": "Огненный шар", "discipline": "pyromancy",
        "desc": "Атака огнём: 1d10+5 E.",
        "cost": 2, "type": "attack", "min_rating": 1,
        "damage": "1d10+5",
    },
    "flame_storm": {
        "name": "Пламенный шторм", "discipline": "pyromancy",
        "desc": "Область огня: 2d10 E по всем врагам в зоне.",
        "cost": 3, "type": "attack", "min_rating": 3,
        "damage": "2d10",
    },
    "fire_shield": {
        "name": "Огненный щит", "discipline": "pyromancy",
        "desc": "+2 AP на следующую сцену.",
        "cost": 3, "type": "buff", "min_rating": 3,
        "buff": {"AP": 2},
    },
    "burning_blade": {
        "name": "Огненный клинок", "discipline": "pyromancy",
        "desc": "Оружие в руке воспламеняется: +1d10 E к урону.",
        "cost": 3, "type": "buff", "min_rating": 3,
        "buff": {"damage_bonus": "1d10 E"},
    },
    "inferno": {
        "name": "Инферно", "discipline": "pyromancy",
        "desc": "Мощный огненный взрыв: 3d10+10 E. Требует psy_rating 5+.",
        "cost": 6, "type": "attack", "min_rating": 5,
        "damage": "3d10+10",
    },

    # === ТЕЛЕКИНЕЗ ===
    "tele_blow": {
        "name": "Телекинетический удар", "discipline": "telekinesis",
        "desc": "Силовой удар: 1d10+5 I.",
        "cost": 2, "type": "attack", "min_rating": 1,
        "damage": "1d10+5",
    },
    "tele_shield": {
        "name": "Телекинетический щит", "discipline": "telekinesis",
        "desc": "+3 AP на следующую сцену.",
        "cost": 3, "type": "buff", "min_rating": 3,
        "buff": {"AP": 3},
    },
    "precision": {
        "name": "Точность", "discipline": "telekinesis",
        "desc": "+10 к BS на следующую атаку.",
        "cost": 2, "type": "buff", "min_rating": 1,
        "buff": {"BS": 10},
    },
    "flight": {
        "name": "Левитация", "discipline": "telekinesis",
        "desc": "Парение до сцены. В бою даёт +20 к манёвренности.",
        "cost": 3, "type": "utility", "min_rating": 3,
    },
    "push": {
        "name": "Телекинетический толчок", "discipline": "telekinesis",
        "desc": "Отбрасывает цель. Проверка S против воли цели.",
        "cost": 3, "type": "control", "min_rating": 3,
    },

    # === ТЕЛЕПАТИЯ ===
    "mind_link": {
        "name": "Мысленная связь", "discipline": "telepathy",
        "desc": "Телепатический контакт с одним существом.",
        "cost": 1, "type": "utility", "min_rating": 1,
    },
    "mind_scan": {
        "name": "Чтение мыслей", "discipline": "telepathy",
        "desc": "Читает поверхностные мысли цели.",
        "cost": 2, "type": "utility", "min_rating": 1,
    },
    "dominate": {
        "name": "Внушение", "discipline": "telepathy",
        "desc": "Подавляет волю цели, короткий приказ.",
        "cost": 4, "type": "control", "min_rating": 3,
    },
    "terrify": {
        "name": "Ужас", "discipline": "telepathy",
        "desc": "Наводит сверхъестественный страх.",
        "cost": 3, "type": "control", "min_rating": 3,
    },
    "astral_proj": {
        "name": "Астральная проекция", "discipline": "telepathy",
        "desc": "Дух покидает тело для разведки. Требует psy_rating 5+.",
        "cost": 5, "type": "utility", "min_rating": 5,
    },

    # === ПРОРИЦАНИЕ ===
    "foreboding": {
        "name": "Предчувствие", "discipline": "divination",
        "desc": "+20 к следующему броску.",
        "cost": 3, "type": "buff", "min_rating": 3,
        "buff": {"next_roll": 20},
    },
    "soul_sight": {
        "name": "Духовное зрение", "discipline": "divination",
        "desc": "Видит невидимое, духов и скрытые двери на сцене.",
        "cost": 2, "type": "utility", "min_rating": 1,
    },
    "fates_vision": {
        "name": "Взор судьбы", "discipline": "divination",
        "desc": "Показывает вероятный исход одной сцены.",
        "cost": 4, "type": "utility", "min_rating": 5,
    },
    "insight": {
        "name": "Прозрение", "discipline": "divination",
        "desc": "+10 к Интеллекту на сцену.",
        "cost": 2, "type": "buff", "min_rating": 1,
        "buff": {"Int": 10},
    },
}


# === ДОСТУП ===
def get_disciplines() -> dict:
    return dict(DISCIPLINES)


def get_powers(char: dict) -> list:
    """Возвращает список id доступных сил по psy_rating."""
    if not isinstance(char, dict):
        return []
    rating = int(char.get("psy_rating", 0) or 0)
    if rating <= 0:
        return []
    out = []
    for pid, p in PSY_POWERS.items():
        if int(p.get("min_rating", 1)) <= rating:
            out.append(pid)
    return out


def get_powers_by_discipline(discipline: str, rating: int) -> list:
    """Возвращает список id сил в дисциплине по рейтингу."""
    out = []
    for pid, p in PSY_POWERS.items():
        if p.get("discipline") != discipline:
            continue
        if int(p.get("min_rating", 1)) <= int(rating):
            out.append(pid)
    return out


def get_power(power_id: str):
    return PSY_POWERS.get(power_id)


# === ЗАРЯД ===
def get_charge(char: dict) -> int:
    if not isinstance(char, dict):
        return 0
    return int(char.get("psy_charge", 0) or 0)


def regen_charge(char: dict) -> None:
    if not isinstance(char, dict):
        return
    rating = int(char.get("psy_rating", 0) or 0)
    if rating > 0:
        char["psy_charge"] = rating * 3


# === БРОСОК ===
def _roll_damage(expr: str) -> int:
    """Парсит XdY+Z и возвращает результат."""
    m = re.match(r"(\d+)d(\d+)([+\-]\d+)?", str(expr))
    if not m:
        return 0
    n, f = int(m.group(1)), int(m.group(2))
    total = sum(random.randint(1, f) for _ in range(n))
    if m.group(3):
        total += int(m.group(3))
    return total


# === ПРИМЕНЕНИЕ ===
def cast(char: dict, power_key: str) -> dict:
    if not isinstance(char, dict):
        return {"ok": False, "reason": "нет персонажа"}
    if power_key not in PSY_POWERS:
        return {"ok": False, "reason": "неизвестная сила"}

    power = PSY_POWERS[power_key]
    rating = int(char.get("psy_rating", 0) or 0)
    if rating < int(power.get("min_rating", 1)):
        return {"ok": False, "reason": "недостаточный psy_rating"}

    cost = int(power.get("cost", 2))
    charge = get_charge(char)
    if charge < cost:
        return {"ok": False, "reason": "не хватает заряда",
                "charge": charge, "need": cost}

    # Проверка WP
    wp = int((char.get("characteristics") or {}).get("WP", 30))
    roll = random.randint(1, 100)
    success = roll <= wp
    char["psy_charge"] = charge - cost

    ptype = power.get("type", "utility")

    # === АТАКА ===
    if ptype == "attack":
        if success:
            dmg = _roll_damage(power.get("damage", "1d10"))
            return {
                "ok": True, "roll": roll, "success": True,
                "damage": dmg,
                "text": power["name"] + " бьёт на " + str(dmg) + " урона.",
            }
        # Провал
        self_dmg = int(power.get("self_damage_on_fail", 0))
        w = char.setdefault("wounds", {})
        cur = int(w.get("current", 0) or 0)
        if self_dmg > 0:
            w["current"] = max(0, cur - self_dmg)
        char["insanity"] = int(char.get("insanity", 0) or 0) + 1
        return {
            "ok": True, "roll": roll, "success": False, "damage": 0,
            "text": ("Сила сорвалась. +1 Безумие"
                     + (" и -" + str(self_dmg) + " рана." if self_dmg else ".")),
        }

    # === ЛЕЧЕНИЕ ===
    if ptype == "heal":
        if not success:
            char["insanity"] = int(char.get("insanity", 0) or 0) + 1
            return {
                "ok": True, "roll": roll, "success": False,
                "text": "Восстановление сорвалось. +1 Безумие.",
            }
        heal = _roll_damage(power.get("heal", "1d5"))
        w = char.setdefault("wounds", {})
        cur = int(w.get("current", 0) or 0)
        mx = int(w.get("max", cur) or cur)
        w["current"] = min(mx, cur + heal)
        return {
            "ok": True, "roll": roll, "success": True, "heal": heal,
            "text": power["name"] + ": +" + str(heal) + " ран.",
        }

    # === БАФФЫ ===
    if ptype == "buff":
        buffs = char.setdefault("psy_buffs", {})
        applied = power.get("buff", {}) or {}
        for k, v in applied.items():
            if k == "next_roll":
                buffs["next_roll"] = int(v)
            elif k == "AP":
                buffs["AP"] = int(buffs.get("AP", 0)) + int(v)
            elif k == "damage_bonus":
                buffs["damage_bonus"] = v
            else:
                # характеристика
                buffs[k] = int(buffs.get(k, 0)) + int(v)
        # Также увеличиваем саму характеристику
        chars = char.setdefault("characteristics", {})
        for k, v in applied.items():
            if k in ("WS", "BS", "S", "T", "Ag", "Int", "Per", "WP", "Fel"):
                chars[k] = int(chars.get(k, 0) or 0) + int(v)
        txt = power["name"]
        if applied:
            parts = []
            for k, v in applied.items():
                if k in ("WS", "BS", "S", "T", "Ag", "Int", "Per", "WP", "Fel"):
                    parts.append(k + "+" + str(v))
                elif k == "AP":
                    parts.append("AP+" + str(v))
                elif k == "next_roll":
                    parts.append("+ " + str(v) + " к след. броску")
                elif k == "damage_bonus":
                    parts.append("+" + str(v) + " к урону")
            txt += " (" + ", ".join(parts) + ")"
        return {"ok": True, "roll": roll, "success": True, "text": txt}

    # === КОНТРОЛЬ / УТИЛИТА ===
    if ptype in ("control", "utility"):
        if not success:
            char["insanity"] = int(char.get("insanity", 0) or 0) + 1
            return {
                "ok": True, "roll": roll, "success": False,
                "text": power["name"] + " сорвалась. +1 Безумие.",
            }
        return {
            "ok": True, "roll": roll, "success": True,
            "text": power["name"] + ": успех. " + power.get("desc", ""),
        }

    return {"ok": True, "roll": roll, "text": power["name"] + ": применено."}


# === КАТАЛОГ ДЛЯ UI ===
def full_catalog(rating: int = 10) -> dict:
    """Возвращает каталог по дисциплинам для UI."""
    out = {}
    for did, dname in DISCIPLINES.items():
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
