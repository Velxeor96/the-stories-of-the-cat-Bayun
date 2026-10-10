"""services/psychic_chaos.py — Chaos психосилы (Rogue Trader Tomes).

Источники: Tome of Fate (Tzeentch), Tome of Decay (Nurgle),
Tome of Excess (Slaanesh), основная книга Rogue Trader.

ПРАВИЛА:
- Каждая сила даёт Порчу (corruption) при использовании.
- Кхорн НЕ имеет психосил — варп-магия запрещена.
- Доступ зависит от бога и архетипа.
"""
from __future__ import annotations
import random
import re

DISCIPLINES = {
    "tzeentch":   "Пути Тзинча (Tome of Fate)",
    "nurgle":     "Дары Нургла (Tome of Decay)",
    "slaanesh":   "Искусства Слаанеш (Tome of Excess)",
    "undivided":  "Хаос Неделимый",
    "demonology": "Демонология",
}

# Какие дисциплины связаны с каким богом
GOD_DISCIPLINE = {
    "tzeentch": "tzeentch",
    "nurgle":   "nurgle",
    "slaanesh": "slaanesh",
}

# Только для Sorcerer-классов
SORCERER_ALL = {"tzeentch", "nurgle", "slaanesh", "undivided", "demonology"}

PSY_POWERS = {
    # ============ TZEENTCH (15) ============
    "bolt_of_change": {"name": "Стрела Перемен", "discipline": "tzeentch",
        "desc": "Атака: 2d10+8 E, может превратить цель в хаос-спавна.",
        "cost": 4, "type": "attack", "min_rating": 3,
        "damage": "2d10+8", "corruption": 1},
    "boon_of_mutation": {"name": "Дар Мутации", "discipline": "tzeentch",
        "desc": "Даёт союзнику мутацию или +10 к характеристике.",
        "cost": 3, "type": "buff", "min_rating": 3,
        "buff": {"T": 10}, "corruption": 1},
    "doombolt": {"name": "Стрела Рока", "discipline": "tzeentch",
        "desc": "Атака: 1d10+7 E, игнорирует щиты цели.",
        "cost": 2, "type": "attack", "min_rating": 1,
        "damage": "1d10+7", "corruption": 1},
    "gift_of_tzeentch": {"name": "Дар Тзинча", "discipline": "tzeentch",
        "desc": "+20 к Интеллекту и Силе воли на сцену.",
        "cost": 3, "type": "buff", "min_rating": 3,
        "buff": {"Int": 10, "WP": 10}, "corruption": 1},
    "tzeentch_firestorm": {"name": "Огненный Шторм Тзинча", "discipline": "tzeentch",
        "desc": "Атака: 3d10+7 E по всем врагам в области.",
        "cost": 5, "type": "attack", "min_rating": 5,
        "damage": "3d10+7", "corruption": 2},
    "treason_tzeentch": {"name": "Предательство Тзинча", "discipline": "tzeentch",
        "desc": "Заставляет врагов атаковать друг друга.",
        "cost": 5, "type": "control", "min_rating": 5, "corruption": 2},
    "warp_gaze": {"name": "Взор Варпа", "discipline": "tzeentch",
        "desc": "Видит истинную природу вещей, скрытые символы.",
        "cost": 2, "type": "utility", "min_rating": 1, "corruption": 1},
    "tzeentch_shroud": {"name": "Покров Тзинча", "discipline": "tzeentch",
        "desc": "+20 к Скрытности на сцену.",
        "cost": 3, "type": "buff", "min_rating": 3,
        "buff": {"Ag": 10}, "corruption": 1},
    "ghostfire": {"name": "Огонь Призраков", "discipline": "tzeentch",
        "desc": "Атака: 2d10+6 E, игнорирует броню.",
        "cost": 4, "type": "attack", "min_rating": 3,
        "damage": "2d10+6", "corruption": 1},
    "pink_fire": {"name": "Розовый Огонь Тзинча", "discipline": "tzeentch",
        "desc": "Атака: 2d10+5 E, оглушает.",
        "cost": 3, "type": "attack", "min_rating": 3,
        "damage": "2d10+5", "corruption": 1},
    "master_fortune": {"name": "Повелитель Фортуны", "discipline": "tzeentch",
        "desc": "Перебрасывает один провальный бросок.",
        "cost": 4, "type": "utility", "min_rating": 5, "corruption": 2},
    "twist_fate": {"name": "Изгиб Судьбы", "discipline": "tzeentch",
        "desc": "+10 к следующему броску.",
        "cost": 2, "type": "buff", "min_rating": 1,
        "buff": {"next_roll": 10}, "corruption": 1},
    "infernal_flames": {"name": "Адское Пламя", "discipline": "tzeentch",
        "desc": "Атака: 2d10+6 E, длительное горение.",
        "cost": 4, "type": "attack", "min_rating": 3,
        "damage": "2d10+6", "corruption": 1},
    "breath_of_chaos": {"name": "Дыхание Хаоса", "discipline": "tzeentch",
        "desc": "Атака: 2d10 E, разъедает броню (-2 AP).",
        "cost": 3, "type": "attack", "min_rating": 3,
        "damage": "2d10", "corruption": 1},
    "coruscating_blast": {"name": "Сияющий Взрыв", "discipline": "tzeentch",
        "desc": "Атака: 3d10+5 E, ослепляет цель.",
        "cost": 5, "type": "attack", "min_rating": 5,
        "damage": "3d10+5", "corruption": 2},

    # ============ NURGLE (15) ============
    "gift_of_nurgle": {"name": "Дар Нургла", "discipline": "nurgle",
        "desc": "+10 к Выносливости на сцену.",
        "cost": 2, "type": "buff", "min_rating": 1,
        "buff": {"T": 10}, "corruption": 1},
    "stream_corruption": {"name": "Поток Гнили", "discipline": "nurgle",
        "desc": "Атака: 2d10+5 E, отравляет.",
        "cost": 3, "type": "attack", "min_rating": 3,
        "damage": "2d10+5", "corruption": 1},
    "miasma_pestilence": {"name": "Миазмы Чумы", "discipline": "nurgle",
        "desc": "Атака областью: 1d10+3 E.",
        "cost": 2, "type": "attack", "min_rating": 1,
        "damage": "1d10+3", "corruption": 1},
    "plague_wind": {"name": "Ветер Чумы", "discipline": "nurgle",
        "desc": "Атака областью: 2d10+4 E, заражает всех в зоне.",
        "cost": 4, "type": "attack", "min_rating": 3,
        "damage": "2d10+4", "corruption": 2},
    "flesh_rot": {"name": "Гниль Плоти", "discipline": "nurgle",
        "desc": "Атака: 1d10+6 E, длительная гниль.",
        "cost": 3, "type": "attack", "min_rating": 3,
        "damage": "1d10+6", "corruption": 1},
    "nurgle_rot": {"name": "Гниль Нургла", "discipline": "nurgle",
        "desc": "Атака: 2d10+8 E, заразно для ближних.",
        "cost": 5, "type": "attack", "min_rating": 5,
        "damage": "2d10+8", "corruption": 2},
    "grandfather_blessing": {"name": "Благословение Дедушки", "discipline": "nurgle",
        "desc": "Лечит 2d5 ран ценой Порчи.",
        "cost": 4, "type": "heal", "min_rating": 3,
        "heal": "2d5", "corruption": 2},
    "curse_leper": {"name": "Проклятие Прокажённого", "discipline": "nurgle",
        "desc": "Цель получает -20 к T на сцену.",
        "cost": 3, "type": "control", "min_rating": 3, "corruption": 1},
    "breath_plaguefather": {"name": "Дыхание Чумного Отца", "discipline": "nurgle",
        "desc": "Атака: 3d10+6 E, длительное заражение.",
        "cost": 5, "type": "attack", "min_rating": 5,
        "damage": "3d10+6", "corruption": 2},
    "pestilent_vapours": {"name": "Заразные Испарения", "discipline": "nurgle",
        "desc": "Атака областью: 1d10+4 E.",
        "cost": 2, "type": "attack", "min_rating": 1,
        "damage": "1d10+4", "corruption": 1},
    "withering_touch": {"name": "Иссушающее Касание", "discipline": "nurgle",
        "desc": "Атака: 2d10+5 E, цель теряет 1 T.",
        "cost": 3, "type": "attack", "min_rating": 3,
        "damage": "2d10+5", "corruption": 1},
    "baleful_transmog": {"name": "Зловещее Превращение", "discipline": "nurgle",
        "desc": "Превращает цель в хаос-спавна (редко).",
        "cost": 6, "type": "control", "min_rating": 5, "corruption": 3},
    "bountiful_blight": {"name": "Щедрая Порча", "discipline": "nurgle",
        "desc": "Восстанавливает 1d5 ран за ход.",
        "cost": 4, "type": "heal", "min_rating": 3,
        "heal": "1d5", "corruption": 1},
    "plague_bearer": {"name": "Носитель Чумы", "discipline": "nurgle",
        "desc": "Цель становится носителем болезни.",
        "cost": 4, "type": "control", "min_rating": 5, "corruption": 2},
    "rotting_flesh": {"name": "Гниющая Плоть", "discipline": "nurgle",
        "desc": "+5 AP, но -5 Fel на сцену.",
        "cost": 3, "type": "buff", "min_rating": 3,
        "buff": {"AP": 5, "Fel": -5}, "corruption": 1},

    # ============ SLAANESH (15) ============
    "lash_submission": {"name": "Плеть Подчинения", "discipline": "slaanesh",
        "desc": "Подчиняет цель на раунд.",
        "cost": 4, "type": "control", "min_rating": 3, "corruption": 1},
    "delightful_pain": {"name": "Восхитительная Боль", "discipline": "slaanesh",
        "desc": "Атака: 1d10+5 E, оглушает от боли.",
        "cost": 2, "type": "attack", "min_rating": 1,
        "damage": "1d10+5", "corruption": 1},
    "hysterical_frenzy": {"name": "Истерическое Безумие", "discipline": "slaanesh",
        "desc": "Цель атакует всех вокруг.",
        "cost": 5, "type": "control", "min_rating": 5, "corruption": 2},
    "pavane_of_slaanesh": {"name": "Павана Слаанеш", "discipline": "slaanesh",
        "desc": "Привлекает внимание всех в зоне к себе.",
        "cost": 2, "type": "control", "min_rating": 1, "corruption": 1},
    "sirens_call": {"name": "Зов Сирены", "discipline": "slaanesh",
        "desc": "Цель идёт к вам против воли.",
        "cost": 3, "type": "control", "min_rating": 3, "corruption": 1},
    "symphony_of_pain": {"name": "Симфония Боли", "discipline": "slaanesh",
        "desc": "Атака областью: 2d10+6 E.",
        "cost": 4, "type": "attack", "min_rating": 3,
        "damage": "2d10+6", "corruption": 1},
    "ecstatic_oblivion": {"name": "Экстатическое Забвение", "discipline": "slaanesh",
        "desc": "Атака: 3d10+5 E, цель теряет сознание.",
        "cost": 5, "type": "attack", "min_rating": 5,
        "damage": "3d10+5", "corruption": 2},
    "cacophonic_caress": {"name": "Какофоническая Ласка", "discipline": "slaanesh",
        "desc": "Атака: 2d10+7 E, оглушает.",
        "cost": 4, "type": "attack", "min_rating": 3,
        "damage": "2d10+7", "corruption": 1},
    "acquiescence": {"name": "Покорность", "discipline": "slaanesh",
        "desc": "Цель становится покорной на сцену.",
        "cost": 5, "type": "control", "min_rating": 5, "corruption": 2},
    "blades_of_remorse": {"name": "Клинки Раскаяния", "discipline": "slaanesh",
        "desc": "Атака: 2d10+8 E, раскаяние мучает цель.",
        "cost": 4, "type": "attack", "min_rating": 3,
        "damage": "2d10+8", "corruption": 1},
    "transfixing_gaze": {"name": "Пронзающий Взор", "discipline": "slaanesh",
        "desc": "Цель замирает, не может действовать.",
        "cost": 3, "type": "control", "min_rating": 3, "corruption": 1},
    "vain_beauty": {"name": "Тщеславная Красота", "discipline": "slaanesh",
        "desc": "+10 к Fel, но -5 к T на сцену.",
        "cost": 2, "type": "buff", "min_rating": 1,
        "buff": {"Fel": 10, "T": -5}, "corruption": 1},
    "excessive_endurance": {"name": "Чрезмерная Выносливость", "discipline": "slaanesh",
        "desc": "+10 к T на сцену.",
        "cost": 2, "type": "buff", "min_rating": 1,
        "buff": {"T": 10}, "corruption": 1},
    "daemonic_visage": {"name": "Демонический Лик", "discipline": "slaanesh",
        "desc": "+20 к Запугиванию на сцену.",
        "cost": 3, "type": "buff", "min_rating": 3,
        "buff": {"Fel": 10}, "corruption": 1},
    "hysterical_laughter": {"name": "Истерический Смех", "discipline": "slaanesh",
        "desc": "Все враги в зоне теряют действие.",
        "cost": 4, "type": "control", "min_rating": 5, "corruption": 2},

    # ============ UNDIVIDED (12) ============
    "doombolt_u": {"name": "Стрела Рока", "discipline": "undivided",
        "desc": "Атака: 1d10+7 E, игнорирует щиты.",
        "cost": 2, "type": "attack", "min_rating": 1,
        "damage": "1d10+7", "corruption": 1},
    "warptime": {"name": "Время Варпа", "discipline": "undivided",
        "desc": "+10 к Ag, +1 реакция на сцену.",
        "cost": 3, "type": "buff", "min_rating": 3,
        "buff": {"Ag": 10}, "corruption": 1},
    "wind_of_chaos": {"name": "Ветер Хаоса", "discipline": "undivided",
        "desc": "Атака областью: 2d10+8 E.",
        "cost": 5, "type": "attack", "min_rating": 5,
        "damage": "2d10+8", "corruption": 2},
    "gift_of_chaos": {"name": "Дар Хаоса", "discipline": "undivided",
        "desc": "Даёт мутацию: +10 к любой характеристике.",
        "cost": 3, "type": "buff", "min_rating": 3,
        "buff": {"S": 10}, "corruption": 2},
    "infernal_gaze": {"name": "Адский Взор", "discipline": "undivided",
        "desc": "Атака: 2d10+5 E.",
        "cost": 3, "type": "attack", "min_rating": 3,
        "damage": "2d10+5", "corruption": 1},
    "sacrifice": {"name": "Жертва", "discipline": "undivided",
        "desc": "Отдаёт свои раны союзнику.",
        "cost": 2, "type": "heal", "min_rating": 1,
        "heal": "1d5", "corruption": 1},
    "soul_harvest": {"name": "Жатва Душ", "discipline": "undivided",
        "desc": "Атака: 2d10+6 E, лечит вас на половину урона.",
        "cost": 4, "type": "attack", "min_rating": 3,
        "damage": "2d10+6", "corruption": 1},
    "daemonic_strength": {"name": "Демоническая Сила", "discipline": "undivided",
        "desc": "+15 к Силе на сцену.",
        "cost": 3, "type": "buff", "min_rating": 3,
        "buff": {"S": 15}, "corruption": 1},
    "warp_rift": {"name": "Разрыв Варпа", "discipline": "undivided",
        "desc": "Атака: 3d10+8 E, редкий.",
        "cost": 6, "type": "attack", "min_rating": 5,
        "damage": "3d10+8", "corruption": 3},
    "daemonbolt": {"name": "Стрела Демона", "discipline": "undivided",
        "desc": "Атака: 2d10+6 E.",
        "cost": 3, "type": "attack", "min_rating": 3,
        "damage": "2d10+6", "corruption": 1},
    "warp_malefic": {"name": "Варп-Злоба", "discipline": "undivided",
        "desc": "Отключает цели одну способность.",
        "cost": 4, "type": "control", "min_rating": 5, "corruption": 2},
    "corruption_gift": {"name": "Дар Порчи", "discipline": "undivided",
        "desc": "+2 к любой характеристике за Порчу.",
        "cost": 2, "type": "buff", "min_rating": 1,
        "buff": {"WS": 2}, "corruption": 2},

    # ============ DEMONOLOGY (8) ============
    "summon_daemon": {"name": "Призыв демона", "discipline": "demonology",
        "desc": "Призывает малого демона.",
        "cost": 5, "type": "utility", "min_rating": 3, "corruption": 2},
    "summon_greater": {"name": "Призыв Великого", "discipline": "demonology",
        "desc": "Призывает Великого демона. Требует psy_rating 7+.",
        "cost": 8, "type": "utility", "min_rating": 7, "corruption": 4},
    "banish_daemon": {"name": "Изгнание демона", "discipline": "demonology",
        "desc": "Изгоняет демоническую сущность.",
        "cost": 5, "type": "control", "min_rating": 5, "corruption": 2},
    "corruption_bolt": {"name": "Луч Порчи", "discipline": "demonology",
        "desc": "Атака: 3d10+8 E, накладывает Порчу.",
        "cost": 5, "type": "attack", "min_rating": 5,
        "damage": "3d10+8", "corruption": 2},
    "pact_with_daemon": {"name": "Пакт с демоном", "discipline": "demonology",
        "desc": "Заключает пакт: +20 к статам за 3 Порчи.",
        "cost": 4, "type": "buff", "min_rating": 5,
        "buff": {"WP": 20}, "corruption": 3},
    "possession": {"name": "Демоническая Одержимость", "discipline": "demonology",
        "desc": "Вселяется в цель на сцену.",
        "cost": 7, "type": "control", "min_rating": 7, "corruption": 3},
    "warp_banishment": {"name": "Варп-Изгнание", "discipline": "demonology",
        "desc": "Изгоняет цель в Варп.",
        "cost": 7, "type": "control", "min_rating": 7, "corruption": 3},
    "hellfire": {"name": "Адский Огонь", "discipline": "demonology",
        "desc": "Атака: 3d10+6 E, игнорирует 8 AP.",
        "cost": 5, "type": "attack", "min_rating": 5,
        "damage": "3d10+6", "corruption": 2},
}


def get_disciplines() -> dict:
    return dict(DISCIPLINES)


def _discipline_access(char: dict) -> set:
    """Определяет набор доступных дисциплин для персонажа."""
    if not isinstance(char, dict):
        return set()

    god = str(char.get("chaos_god", "") or "").lower()
    career_id = str(char.get("career_id", "") or "").lower()
    career_name = str(char.get("career_name", "") or "").lower()
    subfaction = str(char.get("subfaction_id", "") or "").lower()

    # Кхорн — никогда
    if god == "khorne" or "khorn" in god or "berserk" in career_id or "берсерк" in career_name or "кхорн" in career_name:
        return set()

    # Явно выбран бог
    if god in GOD_DISCIPLINE:
        return {GOD_DISCIPLINE[god], "undivided", "demonology"}

    # Sorcerer — все
    if "sorcerer" in career_id or "колдун" in career_name or "сорцерер" in career_name:
        return set(SORCERER_ALL)

    # Chaos Space Marine (без Sorcerer) — Undivided + Demonology + 1 бог (по умолчанию Tzeentch)
    if subfaction == "chaos_marine":
        return {"undivided", "demonology", "tzeentch"}

    # Dark Mechanicum — Tzeentch + Undivided + Demonology
    if subfaction == "dark_mechanicum":
        return {"tzeentch", "undivided", "demonology"}

    # Cultist / Renegade — Undivided + Demonology
    if subfaction in ("cultist", "renegade"):
        return {"undivided", "demonology"}

    # Fallback для Chaos
    return {"undivided", "demonology"}


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
        return {"ok": False, "reason": "дисциплина недоступна вашей фракции"}

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

    corruption = int(power.get("corruption", 0))
    if corruption > 0:
        char["corruption"] = int(char.get("corruption", 0) or 0) + corruption

    ptype = power.get("type", "utility")

    if ptype == "attack":
        if success:
            dmg = _roll_damage(power.get("damage", "1d10"))
            txt = power["name"] + " бьёт на " + str(dmg) + " урона"
            if corruption > 0:
                txt += " (+" + str(corruption) + " Порчи)"
            return {"ok": True, "roll": roll, "success": True, "damage": dmg, "text": txt}
        char["insanity"] = int(char.get("insanity", 0) or 0) + 1
        return {"ok": True, "roll": roll, "success": False, "damage": 0,
                "text": power["name"] + " сорвалась. +1 Безумие."}

    if ptype == "heal":
        if not success:
            char["insanity"] = int(char.get("insanity", 0) or 0) + 1
            return {"ok": True, "roll": roll, "success": False,
                    "text": power["name"] + " сорвалась. +1 Безумие."}
        heal = _roll_damage(power.get("heal", "1d5"))
        w = char.setdefault("wounds", {})
        cur = int(w.get("current", 0) or 0)
        mx = int(w.get("max", cur) or cur)
        w["current"] = min(mx, cur + heal)
        txt = power["name"] + ": +" + str(heal) + " ран"
        if corruption > 0:
            txt += " (+" + str(corruption) + " Порчи)"
        return {"ok": True, "roll": roll, "success": True, "heal": heal, "text": txt}

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
        return {"ok": True, "roll": roll, "success": True,
                "text": power["name"] + ": применено" + (" (+" + str(corruption) + " Порчи)" if corruption > 0 else "")}

    if ptype in ("control", "utility"):
        if not success:
            char["insanity"] = int(char.get("insanity", 0) or 0) + 1
            return {"ok": True, "roll": roll, "success": False,
                    "text": power["name"] + " сорвалась. +1 Безумие."}
        return {"ok": True, "roll": roll, "success": True,
                "text": power["name"] + ": " + power.get("desc", "")}

    return {"ok": True, "roll": roll, "text": power["name"] + ": применено."}


def full_catalog(rating: int = 10, char: dict = None) -> dict:
    allowed = _discipline_access(char or {})
    out = {}
    for did, dname in DISCIPLINES.items():
        if did not in allowed:
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
                "corruption": p.get("corruption", 0),
                "available": int(p.get("min_rating", 1)) <= int(rating),
            })
        out[did] = {"name": dname, "powers": powers}
    return out
