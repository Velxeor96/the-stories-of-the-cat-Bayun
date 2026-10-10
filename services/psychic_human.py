"""services/psychic_human.py — человеческие психосилы.

5 основных дисциплин + Demonology (только Chaos).
"""
from __future__ import annotations
import random
import re

DISCIPLINES = {
    "biomancy":    "Биомантия",
    "pyromancy":   "Пиромантия",
    "telekinesis": "Телекинез",
    "telepathy":   "Телепатия",
    "divination":  "Прорицание",
    "demonology":  "Демонология (запретна для Империума)",
}

# Только для Chaos
CHAOS_ONLY_DISCIPLINES = {"demonology"}

# Для Астропатов — только эти дисциплины
ASTROPATH_DISCIPLINES = {"telepathy", "divination"}

PSY_POWERS = {
    # === БИОМАНТИЯ ===
    "iron_arm": {"name": "Железная плоть", "discipline": "biomancy",
        "desc": "+10 к Выносливости на сцену.", "cost": 2, "type": "buff", "min_rating": 1,
        "buff": {"T": 10}},
    "warp_speed": {"name": "Варп-скорость", "discipline": "biomancy",
        "desc": "+10 к Ловкости на сцену.", "cost": 2, "type": "buff", "min_rating": 1,
        "buff": {"Ag": 10}},
    "endurance": {"name": "Живучесть", "discipline": "biomancy",
        "desc": "Восстанавливает 1d5 ран.", "cost": 2, "type": "heal", "min_rating": 1,
        "heal": "1d5"},
    "regenerate": {"name": "Регенерация", "discipline": "biomancy",
        "desc": "Восстанавливает 2d5 ран.", "cost": 4, "type": "heal", "min_rating": 3,
        "heal": "2d5"},
    "blood_boil": {"name": "Кровяное вскипание", "discipline": "biomancy",
        "desc": "Атака: 2d10+5 E.", "cost": 4, "type": "attack", "min_rating": 5,
        "damage": "2d10+5", "self_damage_on_fail": 1},
    "haemorrhage": {"name": "Кровотечение", "discipline": "biomancy",
        "desc": "Атака: 3d10 E, вызывает длительное кровотечение.", "cost": 5, "type": "attack", "min_rating": 5,
        "damage": "3d10"},

    # === ПИРОМАНТИЯ ===
    "fireball": {"name": "Огненный шар", "discipline": "pyromancy",
        "desc": "Атака огнём: 1d10+5 E.", "cost": 2, "type": "attack", "min_rating": 1,
        "damage": "1d10+5"},
    "flame_storm": {"name": "Пламенный шторм", "discipline": "pyromancy",
        "desc": "Область огня: 2d10 E.", "cost": 3, "type": "attack", "min_rating": 3,
        "damage": "2d10"},
    "fire_shield": {"name": "Огненный щит", "discipline": "pyromancy",
        "desc": "+2 AP на сцену.", "cost": 3, "type": "buff", "min_rating": 3,
        "buff": {"AP": 2}},
    "burning_blade": {"name": "Огненный клинок", "discipline": "pyromancy",
        "desc": "+1d10 E к урону в рукопашной.", "cost": 3, "type": "buff", "min_rating": 3,
        "buff": {"damage_bonus": "1d10 E"}},
    "inferno": {"name": "Инферно", "discipline": "pyromancy",
        "desc": "Мощный огненный взрыв: 3d10+10 E.", "cost": 6, "type": "attack", "min_rating": 5,
        "damage": "3d10+10"},
    "molten_beam": {"name": "Расплавленный луч", "discipline": "pyromancy",
        "desc": "Атака: 2d10+8 E, игнорирует 4 AP.", "cost": 4, "type": "attack", "min_rating": 3,
        "damage": "2d10+8"},
    "sunburst": {"name": "Солнечный взрыв", "discipline": "pyromancy",
        "desc": "Область: 4d10 E, все в зоне получают урон.", "cost": 6, "type": "attack", "min_rating": 5,
        "damage": "4d10"},

    # === ТЕЛЕКИНЕЗ ===
    "tele_blow": {"name": "Телекинетический удар", "discipline": "telekinesis",
        "desc": "Силовой удар: 1d10+5 I.", "cost": 2, "type": "attack", "min_rating": 1,
        "damage": "1d10+5"},
    "tele_shield": {"name": "Телекинетический щит", "discipline": "telekinesis",
        "desc": "+3 AP на сцену.", "cost": 3, "type": "buff", "min_rating": 3,
        "buff": {"AP": 3}},
    "precision": {"name": "Точность", "discipline": "telekinesis",
        "desc": "+10 к BS на следующую атаку.", "cost": 2, "type": "buff", "min_rating": 1,
        "buff": {"BS": 10}},
    "flight": {"name": "Левитация", "discipline": "telekinesis",
        "desc": "Полёт до сцены.", "cost": 3, "type": "utility", "min_rating": 3},
    "push": {"name": "Телекинетический толчок", "discipline": "telekinesis",
        "desc": "Отбрасывает цель.", "cost": 3, "type": "control", "min_rating": 3},
    "objuration_mechanicum": {"name": "Запрет механизмов", "discipline": "telekinesis",
        "desc": "Отключает технику или оружие в радиусе.", "cost": 3, "type": "control", "min_rating": 3},

    # === ТЕЛЕПАТИЯ ===
    "mind_link": {"name": "Мысленная связь", "discipline": "telepathy",
        "desc": "Телепатический контакт.", "cost": 1, "type": "utility", "min_rating": 1},
    "mind_scan": {"name": "Чтение мыслей", "discipline": "telepathy",
        "desc": "Читает поверхностные мысли.", "cost": 2, "type": "utility", "min_rating": 1},
    "dominate": {"name": "Внушение", "discipline": "telepathy",
        "desc": "Подавляет волю цели.", "cost": 4, "type": "control", "min_rating": 3},
    "terrify": {"name": "Ужас", "discipline": "telepathy",
        "desc": "Наводит сверхъестественный страх.", "cost": 3, "type": "control", "min_rating": 3},
    "astral_proj": {"name": "Астральная проекция", "discipline": "telepathy",
        "desc": "Дух покидает тело для разведки.", "cost": 5, "type": "utility", "min_rating": 5},
    "psychic_shriek": {"name": "Психический вопль", "discipline": "telepathy",
        "desc": "Атака: 2d10+5 I, оглушает.", "cost": 3, "type": "attack", "min_rating": 3,
        "damage": "2d10+5"},
    "puppet_master": {"name": "Кукловод", "discipline": "telepathy",
        "desc": "Полный контроль над целью на раунд.", "cost": 6, "type": "control", "min_rating": 5},

    # === ПРОРИЦАНИЕ ===
    "foreboding": {"name": "Предчувствие", "discipline": "divination",
        "desc": "+20 к следующему броску.", "cost": 3, "type": "buff", "min_rating": 3,
        "buff": {"next_roll": 20}},
    "soul_sight": {"name": "Духовное зрение", "discipline": "divination",
        "desc": "Видит невидимое, духов, скрытое.", "cost": 2, "type": "utility", "min_rating": 1},
    "fates_vision": {"name": "Взор судьбы", "discipline": "divination",
        "desc": "Показывает вероятный исход.", "cost": 4, "type": "utility", "min_rating": 5},
    "insight": {"name": "Прозрение", "discipline": "divination",
        "desc": "+10 к Интеллекту на сцену.", "cost": 2, "type": "buff", "min_rating": 1,
        "buff": {"Int": 10}},
    "precognition": {"name": "Предвидение", "discipline": "divination",
        "desc": "+10 к инициативе и уклонению.", "cost": 3, "type": "buff", "min_rating": 3,
        "buff": {"Ag": 10}},
    "misfortune": {"name": "Злой рок", "discipline": "divination",
        "desc": "Цель получает -20 на все броски.", "cost": 4, "type": "control", "min_rating": 5},

    # === ДЕМОНОЛОГИЯ (только Chaos) ===
    "summon_daemon": {"name": "Призыв демона", "discipline": "demonology",
        "desc": "Призывает малого демона. Опасно.", "cost": 5, "type": "utility", "min_rating": 3,
        "corruption": 1},
    "banish_daemon": {"name": "Изгнание демона", "discipline": "demonology",
        "desc": "Изгоняет демоническую сущность.", "cost": 5, "type": "control", "min_rating": 5},
    "corruption_bolt": {"name": "Луч порчи", "discipline": "demonology",
        "desc": "Атака: 3d10+8 E, заражает Порчей.", "cost": 5, "type": "attack", "min_rating": 5,
        "damage": "3d10+8", "corruption": 1},
}


def get_disciplines() -> dict:
    return dict(DISCIPLINES)


def get_powers(char: dict, *, chaos_only: bool = False,
               astropath_only: bool = False) -> list:
    """Возвращает id доступных сил."""
    if not isinstance(char, dict):
        return []
    rating = int(char.get("psy_rating", 0) or 0)
    if rating <= 0:
        return []
    out = []
    for pid, p in PSY_POWERS.items():
        disc = p.get("discipline", "")
        if disc in CHAOS_ONLY_DISCIPLINES and not chaos_only:
            continue
        if astropath_only and disc not in ASTROPATH_DISCIPLINES:
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


def cast(char: dict, power_key: str, *, chaos_only: bool = False,
         astropath_only: bool = False) -> dict:
    """Применяет силу к персонажу."""
    if not isinstance(char, dict):
        return {"ok": False, "reason": "нет персонажа"}
    power = PSY_POWERS.get(power_key)
    if not power:
        return {"ok": False, "reason": "неизвестная сила"}

    disc = power.get("discipline", "")
    if disc in CHAOS_ONLY_DISCIPLINES and not chaos_only:
        return {"ok": False, "reason": "дисциплина запретна для вашей фракции"}
    if astropath_only and disc not in ASTROPATH_DISCIPLINES:
        return {"ok": False, "reason": "недоступно для Астропата"}

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

    # Порча от демонологии — вне зависимости от успеха
    if int(power.get("corruption", 0)) > 0:
        char["corruption"] = int(char.get("corruption", 0) or 0) + int(power["corruption"])

    ptype = power.get("type", "utility")

    if ptype == "attack":
        if success:
            dmg = _roll_damage(power.get("damage", "1d10"))
            return {"ok": True, "roll": roll, "success": True, "damage": dmg,
                    "text": power["name"] + " бьёт на " + str(dmg) + " урона."}
        self_dmg = int(power.get("self_damage_on_fail", 0))
        w = char.setdefault("wounds", {})
        cur = int(w.get("current", 0) or 0)
        if self_dmg > 0:
            w["current"] = max(0, cur - self_dmg)
        char["insanity"] = int(char.get("insanity", 0) or 0) + 1
        return {"ok": True, "roll": roll, "success": False, "damage": 0,
                "text": "Сила сорвалась. +1 Безумие."}

    if ptype == "heal":
        if not success:
            char["insanity"] = int(char.get("insanity", 0) or 0) + 1
            return {"ok": True, "roll": roll, "success": False,
                    "text": "Восстановление сорвалось. +1 Безумие."}
        heal = _roll_damage(power.get("heal", "1d5"))
        w = char.setdefault("wounds", {})
        cur = int(w.get("current", 0) or 0)
        mx = int(w.get("max", cur) or cur)
        w["current"] = min(mx, cur + heal)
        return {"ok": True, "roll": roll, "success": True, "heal": heal,
                "text": power["name"] + ": +" + str(heal) + " ран."}

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
            elif k == "next_roll":
                buffs["next_roll"] = int(v)
            elif k == "damage_bonus":
                buffs["damage_bonus"] = v
        return {"ok": True, "roll": roll, "success": True,
                "text": power["name"] + ": применено."}

    if ptype in ("control", "utility"):
        if not success:
            char["insanity"] = int(char.get("insanity", 0) or 0) + 1
            return {"ok": True, "roll": roll, "success": False,
                    "text": power["name"] + " сорвалась. +1 Безумие."}
        return {"ok": True, "roll": roll, "success": True,
                "text": power["name"] + ": " + power.get("desc", "")}

    return {"ok": True, "roll": roll, "text": power["name"] + ": применено."}


def full_catalog(rating: int = 10, *, chaos_only: bool = False,
                 astropath_only: bool = False) -> dict:
    out = {}
    for did, dname in DISCIPLINES.items():
        if did in CHAOS_ONLY_DISCIPLINES and not chaos_only:
            continue
        if astropath_only and did not in ASTROPATH_DISCIPLINES:
            continue
        powers = []
        for pid, p in PSY_POWERS.items():
            if p.get("discipline") != did:
                continue
            powers.append({
                "id": pid, "name": p.get("name", pid),
                "desc": p.get("desc", ""), "cost": p.get("cost", 2),
                "type": p.get("type", "utility"),
                "min_rating": p.get("min_rating", 1),
                "available": int(p.get("min_rating", 1)) <= int(rating),
            })
        out[did] = {"name": dname, "powers": powers}
    return out
