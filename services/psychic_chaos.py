"""services/psychic_chaos.py — Chaos психосилы + благосклонность бога.

МЕХАНИКА FAVOR (PATCH_81):
- Поле chaos_god_favor = {"tzeentch": N, ...}
- Пороги: [0, 3, 6, 10, 15, 21] -> уровни 0..5
- Начисление: успех +1, крит.успех (roll <= WP//5) +2, крит.провал (roll >= 96) -1
- Кхорн НЕ имеет психосил.
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

GOD_DISCIPLINE = {
    "tzeentch": "tzeentch",
    "nurgle":   "nurgle",
    "slaanesh": "slaanesh",
}

SORCERER_ALL = {"tzeentch", "nurgle", "slaanesh", "undivided", "demonology"}

FAVOR_THRESHOLDS = [0, 3, 6, 10, 15, 21]
FAVOR_DISCIPLINES = {"tzeentch", "nurgle", "slaanesh", "undivided", "demonology"}


PSY_POWERS = {
    # ============ TZEENTCH (15) ============
    "doombolt": {"name": "Стрела Рока", "discipline": "tzeentch", "favor_level": 0,
        "desc": "Атака: 1d10+7 E, игнорирует щиты.", "cost": 2, "type": "attack",
        "min_rating": 1, "damage": "1d10+7", "corruption": 1},
    "twist_fate": {"name": "Изгиб Судьбы", "discipline": "tzeentch", "favor_level": 0,
        "desc": "+10 к следующему броску.", "cost": 2, "type": "buff", "min_rating": 1,
        "buff": {"next_roll": 10}, "corruption": 1},
    "warp_gaze": {"name": "Взор Варпа", "discipline": "tzeentch", "favor_level": 0,
        "desc": "Видит истинную природу вещей.", "cost": 2, "type": "utility",
        "min_rating": 1, "corruption": 1},
    "boon_of_mutation": {"name": "Дар Мутации", "discipline": "tzeentch", "favor_level": 1,
        "desc": "Даёт союзнику мутацию +10 T.", "cost": 3, "type": "buff",
        "min_rating": 3, "buff": {"T": 10}, "corruption": 1},
    "tzeentch_shroud": {"name": "Покров Тзинча", "discipline": "tzeentch", "favor_level": 1,
        "desc": "+10 Ag на сцену.", "cost": 3, "type": "buff", "min_rating": 3,
        "buff": {"Ag": 10}, "corruption": 1},
    "pink_fire": {"name": "Розовый Огонь Тзинча", "discipline": "tzeentch", "favor_level": 1,
        "desc": "Атака: 2d10+5 E, оглушает.", "cost": 3, "type": "attack",
        "min_rating": 3, "damage": "2d10+5", "corruption": 1},
    "bolt_of_change": {"name": "Стрела Перемен", "discipline": "tzeentch", "favor_level": 2,
        "desc": "Атака: 2d10+8 E.", "cost": 4, "type": "attack", "min_rating": 3,
        "damage": "2d10+8", "corruption": 1},
    "gift_of_tzeentch": {"name": "Дар Тзинча", "discipline": "tzeentch", "favor_level": 2,
        "desc": "+10 Int, +10 WP на сцену.", "cost": 3, "type": "buff",
        "min_rating": 3, "buff": {"Int": 10, "WP": 10}, "corruption": 1},
    "ghostfire": {"name": "Огонь Призраков", "discipline": "tzeentch", "favor_level": 2,
        "desc": "Атака: 2d10+6 E, игнорирует броню.", "cost": 4, "type": "attack",
        "min_rating": 3, "damage": "2d10+6", "corruption": 1},
    "infernal_flames": {"name": "Адское Пламя", "discipline": "tzeentch", "favor_level": 3,
        "desc": "Атака: 2d10+6 E, длительное горение.", "cost": 4, "type": "attack",
        "min_rating": 3, "damage": "2d10+6", "corruption": 1},
    "breath_of_chaos": {"name": "Дыхание Хаоса", "discipline": "tzeentch", "favor_level": 3,
        "desc": "Атака: 2d10 E, разъедает броню.", "cost": 3, "type": "attack",
        "min_rating": 3, "damage": "2d10", "corruption": 1},
    "master_fortune": {"name": "Повелитель Фортуны", "discipline": "tzeentch", "favor_level": 3,
        "desc": "Перебрасывает один провальный бросок.", "cost": 4, "type": "utility",
        "min_rating": 5, "corruption": 2},
    "tzeentch_firestorm": {"name": "Огненный Шторм Тзинча", "discipline": "tzeentch", "favor_level": 4,
        "desc": "Атака: 3d10+7 E по всем врагам.", "cost": 5, "type": "attack",
        "min_rating": 5, "damage": "3d10+7", "corruption": 2},
    "coruscating_blast": {"name": "Сияющий Взрыв", "discipline": "tzeentch", "favor_level": 4,
        "desc": "Атака: 3d10+5 E, ослепляет.", "cost": 5, "type": "attack",
        "min_rating": 5, "damage": "3d10+5", "corruption": 2},
    "treason_tzeentch": {"name": "Предательство Тзинча", "discipline": "tzeentch", "favor_level": 5,
        "desc": "Враги атакуют друг друга.", "cost": 5, "type": "control",
        "min_rating": 5, "corruption": 2},

    # ============ NURGLE (15) ============
    "gift_of_nurgle": {"name": "Дар Нургла", "discipline": "nurgle", "favor_level": 0,
        "desc": "+10 T на сцену.", "cost": 2, "type": "buff", "min_rating": 1,
        "buff": {"T": 10}, "corruption": 1},
    "miasma_pestilence": {"name": "Миазмы Чумы", "discipline": "nurgle", "favor_level": 0,
        "desc": "Атака областью: 1d10+3 E.", "cost": 2, "type": "attack",
        "min_rating": 1, "damage": "1d10+3", "corruption": 1},
    "pestilent_vapours": {"name": "Заразные Испарения", "discipline": "nurgle", "favor_level": 0,
        "desc": "Атака областью: 1d10+4 E.", "cost": 2, "type": "attack",
        "min_rating": 1, "damage": "1d10+4", "corruption": 1},
    "stream_corruption": {"name": "Поток Гнили", "discipline": "nurgle", "favor_level": 1,
        "desc": "Атака: 2d10+5 E, отравляет.", "cost": 3, "type": "attack",
        "min_rating": 3, "damage": "2d10+5", "corruption": 1},
    "withering_touch": {"name": "Иссушающее Касание", "discipline": "nurgle", "favor_level": 1,
        "desc": "Атака: 2d10+5 E, -1 T.", "cost": 3, "type": "attack",
        "min_rating": 3, "damage": "2d10+5", "corruption": 1},
    "bountiful_blight": {"name": "Щедрая Порча", "discipline": "nurgle", "favor_level": 1,
        "desc": "Восстанавливает 1d5 ран за ход.", "cost": 4, "type": "heal",
        "min_rating": 3, "heal": "1d5", "corruption": 1},
    "flesh_rot": {"name": "Гниль Плоти", "discipline": "nurgle", "favor_level": 2,
        "desc": "Атака: 1d10+6 E, длительная гниль.", "cost": 3, "type": "attack",
        "min_rating": 3, "damage": "1d10+6", "corruption": 1},
    "curse_leper": {"name": "Проклятие Прокажённого", "discipline": "nurgle", "favor_level": 2,
        "desc": "-20 T цели.", "cost": 3, "type": "control", "min_rating": 3, "corruption": 1},
    "rotting_flesh": {"name": "Гниющая Плоть", "discipline": "nurgle", "favor_level": 2,
        "desc": "+5 AP, -5 Fel.", "cost": 3, "type": "buff", "min_rating": 3,
        "buff": {"AP": 5, "Fel": -5}, "corruption": 1},
    "plague_wind": {"name": "Ветер Чумы", "discipline": "nurgle", "favor_level": 3,
        "desc": "Атака областью: 2d10+4 E.", "cost": 4, "type": "attack",
        "min_rating": 3, "damage": "2d10+4", "corruption": 2},
    "grandfather_blessing": {"name": "Благословение Дедушки", "discipline": "nurgle", "favor_level": 3,
        "desc": "Лечит 2d5 ран.", "cost": 4, "type": "heal",
        "min_rating": 3, "heal": "2d5", "corruption": 2},
    "plague_bearer": {"name": "Носитель Чумы", "discipline": "nurgle", "favor_level": 3,
        "desc": "Цель становится носителем болезни.", "cost": 4, "type": "control",
        "min_rating": 5, "corruption": 2},
    "nurgle_rot": {"name": "Гниль Нургла", "discipline": "nurgle", "favor_level": 4,
        "desc": "Атака: 2d10+8 E, заразно.", "cost": 5, "type": "attack",
        "min_rating": 5, "damage": "2d10+8", "corruption": 2},
    "breath_plaguefather": {"name": "Дыхание Чумного Отца", "discipline": "nurgle", "favor_level": 4,
        "desc": "Атака: 3d10+6 E, длительное заражение.", "cost": 5, "type": "attack",
        "min_rating": 5, "damage": "3d10+6", "corruption": 2},
    "baleful_transmog": {"name": "Зловещее Превращение", "discipline": "nurgle", "favor_level": 5,
        "desc": "Превращает цель в хаос-спавна.", "cost": 6, "type": "control",
        "min_rating": 5, "corruption": 3},

    # ============ SLAANESH (15) ============
    "delightful_pain": {"name": "Восхитительная Боль", "discipline": "slaanesh", "favor_level": 0,
        "desc": "Атака: 1d10+5 E, оглушает.", "cost": 2, "type": "attack",
        "min_rating": 1, "damage": "1d10+5", "corruption": 1},
    "pavane_of_slaanesh": {"name": "Павана Слаанеш", "discipline": "slaanesh", "favor_level": 0,
        "desc": "Привлекает внимание всех.", "cost": 2, "type": "control",
        "min_rating": 1, "corruption": 1},
    "vain_beauty": {"name": "Тщеславная Красота", "discipline": "slaanesh", "favor_level": 0,
        "desc": "+10 Fel, -5 T.", "cost": 2, "type": "buff", "min_rating": 1,
        "buff": {"Fel": 10, "T": -5}, "corruption": 1},
    "sirens_call": {"name": "Зов Сирены", "discipline": "slaanesh", "favor_level": 1,
        "desc": "Цель идёт к вам против воли.", "cost": 3, "type": "control",
        "min_rating": 3, "corruption": 1},
    "excessive_endurance": {"name": "Чрезмерная Выносливость", "discipline": "slaanesh", "favor_level": 1,
        "desc": "+10 T на сцену.", "cost": 2, "type": "buff", "min_rating": 1,
        "buff": {"T": 10}, "corruption": 1},
    "transfixing_gaze": {"name": "Пронзающий Взор", "discipline": "slaanesh", "favor_level": 1,
        "desc": "Цель замирает.", "cost": 3, "type": "control", "min_rating": 3, "corruption": 1},
    "lash_submission": {"name": "Плеть Подчинения", "discipline": "slaanesh", "favor_level": 2,
        "desc": "Подчиняет цель на раунд.", "cost": 4, "type": "control",
        "min_rating": 3, "corruption": 1},
    "symphony_of_pain": {"name": "Симфония Боли", "discipline": "slaanesh", "favor_level": 2,
        "desc": "Атака областью: 2d10+6 E.", "cost": 4, "type": "attack",
        "min_rating": 3, "damage": "2d10+6", "corruption": 1},
    "daemonic_visage": {"name": "Демонический Лик", "discipline": "slaanesh", "favor_level": 2,
        "desc": "+10 Fel на сцену.", "cost": 3, "type": "buff", "min_rating": 3,
        "buff": {"Fel": 10}, "corruption": 1},
    "cacophonic_caress": {"name": "Какофоническая Ласка", "discipline": "slaanesh", "favor_level": 3,
        "desc": "Атака: 2d10+7 E, оглушает.", "cost": 4, "type": "attack",
        "min_rating": 3, "damage": "2d10+7", "corruption": 1},
    "blades_of_remorse": {"name": "Клинки Раскаяния", "discipline": "slaanesh", "favor_level": 3,
        "desc": "Атака: 2d10+8 E.", "cost": 4, "type": "attack",
        "min_rating": 3, "damage": "2d10+8", "corruption": 1},
    "hysterical_laughter": {"name": "Истерический Смех", "discipline": "slaanesh", "favor_level": 3,
        "desc": "Все враги теряют действие.", "cost": 4, "type": "control",
        "min_rating": 5, "corruption": 2},
    "ecstatic_oblivion": {"name": "Экстатическое Забвение", "discipline": "slaanesh", "favor_level": 4,
        "desc": "Атака: 3d10+5 E, цель теряет сознание.", "cost": 5, "type": "attack",
        "min_rating": 5, "damage": "3d10+5", "corruption": 2},
    "acquiescence": {"name": "Покорность", "discipline": "slaanesh", "favor_level": 4,
        "desc": "Цель покорна на сцену.", "cost": 5, "type": "control",
        "min_rating": 5, "corruption": 2},
    "hysterical_frenzy": {"name": "Истерическое Безумие", "discipline": "slaanesh", "favor_level": 5,
        "desc": "Цель атакует всех вокруг.", "cost": 5, "type": "control",
        "min_rating": 5, "corruption": 2},

    # ============ UNDIVIDED (12) ============
    "doombolt_u": {"name": "Стрела Рока", "discipline": "undivided", "favor_level": 0,
        "desc": "Атака: 1d10+7 E.", "cost": 2, "type": "attack",
        "min_rating": 1, "damage": "1d10+7", "corruption": 1},
    "sacrifice": {"name": "Жертва", "discipline": "undivided", "favor_level": 0,
        "desc": "Отдаёт свои раны союзнику.", "cost": 2, "type": "heal",
        "min_rating": 1, "heal": "1d5", "corruption": 1},
    "corruption_gift": {"name": "Дар Порчи", "discipline": "undivided", "favor_level": 0,
        "desc": "+2 к характеристике за Порчу.", "cost": 2, "type": "buff",
        "min_rating": 1, "buff": {"WS": 2}, "corruption": 2},
    "warptime": {"name": "Время Варпа", "discipline": "undivided", "favor_level": 1,
        "desc": "+10 Ag, +1 реакция.", "cost": 3, "type": "buff",
        "min_rating": 3, "buff": {"Ag": 10}, "corruption": 1},
    "infernal_gaze": {"name": "Адский Взор", "discipline": "undivided", "favor_level": 1,
        "desc": "Атака: 2d10+5 E.", "cost": 3, "type": "attack",
        "min_rating": 3, "damage": "2d10+5", "corruption": 1},
    "daemonbolt": {"name": "Стрела Демона", "discipline": "undivided", "favor_level": 1,
        "desc": "Атака: 2d10+6 E.", "cost": 3, "type": "attack",
        "min_rating": 3, "damage": "2d10+6", "corruption": 1},
    "gift_of_chaos": {"name": "Дар Хаоса", "discipline": "undivided", "favor_level": 2,
        "desc": "Мутация: +10 S.", "cost": 3, "type": "buff", "min_rating": 3,
        "buff": {"S": 10}, "corruption": 2},
    "daemonic_strength": {"name": "Демоническая Сила", "discipline": "undivided", "favor_level": 2,
        "desc": "+15 S на сцену.", "cost": 3, "type": "buff", "min_rating": 3,
        "buff": {"S": 15}, "corruption": 1},
    "soul_harvest": {"name": "Жатва Душ", "discipline": "undivided", "favor_level": 2,
        "desc": "Атака: 2d10+6 E, лечит на половину.", "cost": 4, "type": "attack",
        "min_rating": 3, "damage": "2d10+6", "corruption": 1},
    "wind_of_chaos": {"name": "Ветер Хаоса", "discipline": "undivided", "favor_level": 3,
        "desc": "Атака областью: 2d10+8 E.", "cost": 5, "type": "attack",
        "min_rating": 5, "damage": "2d10+8", "corruption": 2},
    "warp_malefic": {"name": "Варп-Злоба", "discipline": "undivided", "favor_level": 3,
        "desc": "Отключает способность цели.", "cost": 4, "type": "control",
        "min_rating": 5, "corruption": 2},
    "warp_rift": {"name": "Разрыв Варпа", "discipline": "undivided", "favor_level": 4,
        "desc": "Атака: 3d10+8 E, редкий.", "cost": 6, "type": "attack",
        "min_rating": 5, "damage": "3d10+8", "corruption": 3},

    # ============ DEMONOLOGY (8) ============
    "corruption_bolt": {"name": "Луч Порчи", "discipline": "demonology", "favor_level": 0,
        "desc": "Атака: 3d10+8 E, накладывает Порчу.", "cost": 5, "type": "attack",
        "min_rating": 5, "damage": "3d10+8", "corruption": 2},
    "summon_daemon": {"name": "Призыв демона", "discipline": "demonology", "favor_level": 1,
        "desc": "Призывает малого демона.", "cost": 5, "type": "utility",
        "min_rating": 3, "corruption": 2},
    "hellfire": {"name": "Адский Огонь", "discipline": "demonology", "favor_level": 1,
        "desc": "Атака: 3d10+6 E, игнорирует 8 AP.", "cost": 5, "type": "attack",
        "min_rating": 5, "damage": "3d10+6", "corruption": 2},
    "banish_daemon": {"name": "Изгнание демона", "discipline": "demonology", "favor_level": 2,
        "desc": "Изгоняет демоническую сущность.", "cost": 5, "type": "control",
        "min_rating": 5, "corruption": 2},
    "pact_with_daemon": {"name": "Пакт с демоном", "discipline": "demonology", "favor_level": 2,
        "desc": "+20 WP за 3 Порчи.", "cost": 4, "type": "buff",
        "min_rating": 5, "buff": {"WP": 20}, "corruption": 3},
    "summon_greater": {"name": "Призыв Великого", "discipline": "demonology", "favor_level": 3,
        "desc": "Призывает Великого демона.", "cost": 8, "type": "utility",
        "min_rating": 7, "corruption": 4},
    "possession": {"name": "Демоническая Одержимость", "discipline": "demonology", "favor_level": 3,
        "desc": "Вселяется в цель на сцену.", "cost": 7, "type": "control",
        "min_rating": 7, "corruption": 3},
    "warp_banishment": {"name": "Варп-Изгнание", "discipline": "demonology", "favor_level": 4,
        "desc": "Изгоняет цель в Варп.", "cost": 7, "type": "control",
        "min_rating": 7, "corruption": 3},
}


# ==================== FAVOR API ====================

def get_favor_level(char: dict, god: str) -> int:
    if not isinstance(char, dict):
        return 0
    favor = char.get("chaos_god_favor") or {}
    value = int(favor.get(god, 0) or 0)
    level = 0
    for i, threshold in enumerate(FAVOR_THRESHOLDS):
        if value >= threshold:
            level = i
        else:
            break
    return min(level, len(FAVOR_THRESHOLDS) - 1)


def add_favor(char: dict, god: str, amount: int) -> None:
    if not isinstance(char, dict):
        return
    if god not in FAVOR_DISCIPLINES:
        return
    favor = char.setdefault("chaos_god_favor", {})
    favor[god] = max(0, int(favor.get(god, 0) or 0) + int(amount))


def get_all_favor(char: dict) -> dict:
    return {
        "tzeentch": get_favor_level(char, "tzeentch"),
        "nurgle": get_favor_level(char, "nurgle"),
        "slaanesh": get_favor_level(char, "slaanesh"),
        "undivided": get_favor_level(char, "undivided"),
        "demonology": get_favor_level(char, "demonology"),
    }


# ==================== ACCESS ====================

def get_disciplines() -> dict:
    return dict(DISCIPLINES)


def _discipline_access(char: dict) -> set:
    if not isinstance(char, dict):
        return set()

    god = str(char.get("chaos_god", "") or "").lower()
    career_id = str(char.get("career_id", "") or "").lower()
    career_name = str(char.get("career_name", "") or "").lower()
    subfaction = str(char.get("subfaction_id", "") or "").lower()

    if god == "khorne" or "khorn" in god or "berserk" in career_id or "берсерк" in career_name or "кхорн" in career_name:
        return set()

    if god in GOD_DISCIPLINE:
        return {GOD_DISCIPLINE[god], "undivided", "demonology"}

    if "sorcerer" in career_id or "колдун" in career_name or "сорцерер" in career_name:
        return set(SORCERER_ALL)

    if subfaction == "chaos_marine":
        return {"undivided", "demonology", "tzeentch"}

    if subfaction == "dark_mechanicum":
        return {"tzeentch", "undivided", "demonology"}

    if subfaction in ("cultist", "renegade"):
        return {"undivided", "demonology"}

    return {"undivided", "demonology"}


def _check_power_access(char: dict, power: dict, allowed: set) -> tuple:
    disc = power.get("discipline", "")
    if disc not in allowed:
        return False, "дисциплина недоступна вашей фракции"

    rating = int(char.get("psy_rating", 0) or 0)
    if rating < int(power.get("min_rating", 1)):
        return False, "недостаточный psy_rating"

    god = disc if disc in ("tzeentch", "nurgle", "slaanesh") else "undivided"
    favor_lvl = get_favor_level(char, god)
    if int(power.get("favor_level", 0)) > favor_lvl:
        return False, ("недостаточная благосклонность бога (нужно "
                       + str(power.get("favor_level", 0)) + ", есть " + str(favor_lvl) + ")")
    return True, ""


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
        ok, _ = _check_power_access(char, p, allowed)
        if ok:
            out.append(pid)
    return out


def get_power(pid: str):
    return PSY_POWERS.get(pid)


# ==================== CAST ====================

def _roll_damage(expr: str) -> int:
    m = re.match(r"(\d+)d(\d+)([+\-]\d+)?", str(expr))
    if not m:
        return 0
    n, f = int(m.group(1)), int(m.group(2))
    total = sum(random.randint(1, f) for _ in range(n))
    if m.group(3):
        total += int(m.group(3))
    return total


def _award_favor(char: dict, power: dict, roll: int, wp: int, success: bool) -> dict:
    disc = power.get("discipline", "")
    god = disc if disc in ("tzeentch", "nurgle", "slaanesh") else "undivided"
    delta = 0
    if success:
        if roll <= max(1, wp // 5):
            delta = 2
        else:
            delta = 1
    elif roll >= 96:
        delta = -1
    if delta != 0:
        add_favor(char, god, delta)
    return {"god": god, "delta": delta, "level": get_favor_level(char, god)}


def cast(char: dict, power_key: str) -> dict:
    if not isinstance(char, dict):
        return {"ok": False, "reason": "нет персонажа"}
    power = PSY_POWERS.get(power_key)
    if not power:
        return {"ok": False, "reason": "неизвестная сила"}

    allowed = _discipline_access(char)
    ok, reason = _check_power_access(char, power, allowed)
    if not ok:
        return {"ok": False, "reason": reason}

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

    favor_info = _award_favor(char, power, roll, wp, success)
    favor_txt = ""
    if favor_info["delta"] != 0:
        sign = "+" if favor_info["delta"] > 0 else ""
        favor_txt = " [" + favor_info["god"] + " " + sign + str(favor_info["delta"]) + "]"

    ptype = power.get("type", "utility")

    if ptype == "attack":
        if success:
            dmg = _roll_damage(power.get("damage", "1d10"))
            txt = power["name"] + " бьёт на " + str(dmg) + " урона"
            if corruption > 0:
                txt += " (+" + str(corruption) + " Порчи)"
            txt += favor_txt
            return {"ok": True, "roll": roll, "success": True, "damage": dmg,
                    "text": txt, "favor": favor_info}
        char["insanity"] = int(char.get("insanity", 0) or 0) + 1
        return {"ok": True, "roll": roll, "success": False, "damage": 0,
                "text": power["name"] + " сорвалась. +1 Безумие." + favor_txt,
                "favor": favor_info}

    if ptype == "heal":
        if not success:
            char["insanity"] = int(char.get("insanity", 0) or 0) + 1
            return {"ok": True, "roll": roll, "success": False,
                    "text": power["name"] + " сорвалась. +1 Безумие." + favor_txt,
                    "favor": favor_info}
        heal = _roll_damage(power.get("heal", "1d5"))
        w = char.setdefault("wounds", {})
        cur = int(w.get("current", 0) or 0)
        mx = int(w.get("max", cur) or cur)
        w["current"] = min(mx, cur + heal)
        txt = power["name"] + ": +" + str(heal) + " ран"
        if corruption > 0:
            txt += " (+" + str(corruption) + " Порчи)"
        txt += favor_txt
        return {"ok": True, "roll": roll, "success": True, "heal": heal,
                "text": txt, "favor": favor_info}

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
        txt = power["name"] + ": применено"
        if corruption > 0:
            txt += " (+" + str(corruption) + " Порчи)"
        txt += favor_txt
        return {"ok": True, "roll": roll, "success": True, "text": txt, "favor": favor_info}

    if ptype in ("control", "utility"):
        if not success:
            char["insanity"] = int(char.get("insanity", 0) or 0) + 1
            return {"ok": True, "roll": roll, "success": False,
                    "text": power["name"] + " сорвалась. +1 Безумие." + favor_txt,
                    "favor": favor_info}
        return {"ok": True, "roll": roll, "success": True,
                "text": power["name"] + ": " + power.get("desc", "") + favor_txt,
                "favor": favor_info}

    return {"ok": True, "roll": roll, "text": power["name"] + ": применено." + favor_txt,
            "favor": favor_info}


def full_catalog(rating: int = 10, char: dict = None) -> dict:
    char = char or {}
    allowed = _discipline_access(char)
    out = {}
    for did, dname in DISCIPLINES.items():
        if did not in allowed:
            continue
        powers = []
        god = did if did in ("tzeentch", "nurgle", "slaanesh") else "undivided"
        favor_lvl = get_favor_level(char, god)
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
                "favor_level": p.get("favor_level", 0),
                "corruption": p.get("corruption", 0),
                "available": (int(p.get("min_rating", 1)) <= int(rating)
                              and int(p.get("favor_level", 0)) <= favor_lvl),
            })
        out[did] = {"name": dname, "powers": powers, "favor_level": favor_lvl}
    return out
