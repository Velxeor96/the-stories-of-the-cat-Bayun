"""services/psychic_eldar.py — психосилы Эльдар (Аэльдари).

ДИСЦИПЛИНЫ (6):
- runes_of_fate (12)         — Фарсиры
- runes_of_battle (10)       — Варлоки, Спиритсиры
- runes_of_restoration (8)   — Спиритсиры, целители
- runes_of_warding (8)       — Все псайкеры Эльдар
- runes_of_concealment (8)   — Рейнджеры, Арлекины
- runes_of_war (10)          — Аспектные воины, Автархи
"""
from __future__ import annotations
import random
import re

DISCIPLINES = {
    "runes_of_fate":         "Руны Судьбы (Фарсиры)",
    "runes_of_battle":       "Руны Битвы (Варлоки)",
    "runes_of_restoration":  "Руны Восстановления (Спиритсиры)",
    "runes_of_warding":      "Руны Защиты",
    "runes_of_concealment":  "Руны Сокрытия (Арлекины, Рейнджеры)",
    "runes_of_war":          "Руны Войны (Аспекты, Автархи)",
}


PSY_POWERS = {
    # ============ RUNES OF FATE (12) ============
    "eldar_rune_fate_guide": {"name": "Наставление", "discipline": "runes_of_fate",
        "min_rating": 1, "cost": 2, "type": "buff",
        "desc": "Союзник получает реролл на попадание.",
        "buff": {"next_roll": 10}},
    "eldar_rune_fate_doom": {"name": "Обречение", "discipline": "runes_of_fate",
        "min_rating": 2, "cost": 3, "type": "control",
        "desc": "Враг рероллит успешные спас-броски."},
    "eldar_rune_fate_fortune": {"name": "Фортуна", "discipline": "runes_of_fate",
        "min_rating": 2, "cost": 3, "type": "buff",
        "desc": "Отряд получает 5+ Feel No Pain.",
        "buff": {"T": 5}},
    "eldar_rune_fate_witch_strike": {"name": "Ведьмин Удар", "discipline": "runes_of_fate",
        "min_rating": 2, "cost": 3, "type": "attack",
        "desc": "Атака: 1d10+5 E.", "damage": "1d10+5"},
    "eldar_rune_fate_ghostwalk": {"name": "Призрачный Шаг", "discipline": "runes_of_fate",
        "min_rating": 3, "cost": 3, "type": "utility",
        "desc": "Отряд проходит сквозь препятствия."},
    "eldar_rune_fate_executioner": {"name": "Палач", "discipline": "runes_of_fate",
        "min_rating": 3, "cost": 4, "type": "attack",
        "desc": "Атака: 2d10+6 E через психическую проекцию.",
        "damage": "2d10+6"},
    "eldar_rune_fate_will_of_asuryan": {"name": "Воля Азуриана", "discipline": "runes_of_fate",
        "min_rating": 3, "cost": 4, "type": "buff",
        "desc": "Отряд получает Fearless и Adamantium Will.",
        "buff": {"WP": 10}},
    "eldar_rune_fate_mind_war": {"name": "Война Разумов", "discipline": "runes_of_fate",
        "min_rating": 4, "cost": 5, "type": "attack",
        "desc": "Атака: 3d10+6 E в разум врага.", "damage": "3d10+6"},
    "eldar_rune_fate_eldritch_storm": {"name": "Эльдрический Шторм", "discipline": "runes_of_fate",
        "min_rating": 4, "cost": 5, "type": "attack",
        "desc": "Атака областью: 2d10+6 E.", "damage": "2d10+6"},
    "eldar_rune_fate_crushing_orb": {"name": "Дробящая Сфера", "discipline": "runes_of_fate",
        "min_rating": 4, "cost": 4, "type": "attack",
        "desc": "Атака: 3d10+5 E.", "damage": "3d10+5"},
    "eldar_rune_fate_fate_divergence": {"name": "Расхождение Судеб", "discipline": "runes_of_fate",
        "min_rating": 5, "cost": 5, "type": "special",
        "desc": "Фарсир меняет исход одного события (мастер решает)."},
    "eldar_rune_fate_phoenix_spirit": {"name": "Дух Феникса", "discipline": "runes_of_fate",
        "min_rating": 5, "cost": 6, "type": "buff",
        "desc": "Отряд получает регенерацию и иммунитет к страху.",
        "buff": {"T": 10, "WP": 10}},

    # ============ RUNES OF BATTLE (10) ============
    "eldar_rune_battle_conceal_reveal": {"name": "Сокрытие / Разоблачение", "discipline": "runes_of_battle",
        "min_rating": 1, "cost": 2, "type": "buff",
        "desc": "Союзники +2 к укрытию, враг теряет Stealth."},
    "eldar_rune_battle_destructor_renewer": {"name": "Разрушитель / Обновитель", "discipline": "runes_of_battle",
        "min_rating": 1, "cost": 3, "type": "attack",
        "desc": "Атака: 2d10+5 E, либо лечит 1 рану.", "damage": "2d10+5"},
    "eldar_rune_battle_embolden_horrify": {"name": "Воодушевление / Ужас", "discipline": "runes_of_battle",
        "min_rating": 1, "cost": 2, "type": "buff",
        "desc": "Союзники +1 Ld, враг -1 Ld."},
    "eldar_rune_battle_enhance_drain": {"name": "Усиление / Истощение", "discipline": "runes_of_battle",
        "min_rating": 2, "cost": 3, "type": "buff",
        "desc": "Союзники +1 S и I, враг -1 S и I.",
        "buff": {"S": 10}},
    "eldar_rune_battle_protect_jinx": {"name": "Защита / Порча", "discipline": "runes_of_battle",
        "min_rating": 2, "cost": 3, "type": "buff",
        "desc": "Союзники +1 к спас-броску, враг -1."},
    "eldar_rune_battle_quicken_restrain": {"name": "Ускорение / Сдерживание", "discipline": "runes_of_battle",
        "min_rating": 2, "cost": 3, "type": "buff",
        "desc": "Союзники +3 дюйма движения, враг -3 дюйма."},
    "eldar_rune_battle_empower_enervate": {"name": "Вдохновение / Обессиливание", "discipline": "runes_of_battle",
        "min_rating": 3, "cost": 4, "type": "buff",
        "desc": "Союзники +1 A, враг -1 A."},
    "eldar_rune_battle_executioner": {"name": "Палач Варлока", "discipline": "runes_of_battle",
        "min_rating": 3, "cost": 4, "type": "attack",
        "desc": "Атака: 2d10+7 E.", "damage": "2d10+7"},
    "eldar_rune_battle_psychic_lock": {"name": "Психический Замок", "discipline": "runes_of_battle",
        "min_rating": 4, "cost": 5, "type": "control",
        "desc": "Враг не может двигаться (1 раунд)."},
    "eldar_rune_battle_eldritch_storm": {"name": "Эльдрический Шторм Варлока", "discipline": "runes_of_battle",
        "min_rating": 4, "cost": 5, "type": "attack",
        "desc": "Атака областью: 2d10+7 E.", "damage": "2d10+7"},

    # ============ RUNES OF RESTORATION (8) ============
    "eldar_rune_restore_heal": {"name": "Исцеление", "discipline": "runes_of_restoration",
        "min_rating": 1, "cost": 2, "type": "heal",
        "desc": "Восстанавливает 2d10 ран.", "heal": "2d10"},
    "eldar_rune_restore_renew": {"name": "Обновление", "discipline": "runes_of_restoration",
        "min_rating": 2, "cost": 3, "type": "heal",
        "desc": "Восстанавливает 1 рану всем союзникам.", "heal": "1d5"},
    "eldar_rune_restore_purify": {"name": "Очищение", "discipline": "runes_of_restoration",
        "min_rating": 2, "cost": 3, "type": "utility",
        "desc": "Снимает все негативные эффекты с союзника."},
    "eldar_rune_restore_wraithsight": {"name": "Призрачное Зрение", "discipline": "runes_of_restoration",
        "min_rating": 3, "cost": 4, "type": "buff",
        "desc": "Союзник-призрак получает полноценные действия."},
    "eldar_rune_restore_bonesing": {"name": "Пение Кости", "discipline": "runes_of_restoration",
        "min_rating": 3, "cost": 4, "type": "heal",
        "desc": "Восстанавливает 2d10 структуры техники или призрака.", "heal": "2d10"},
    "eldar_rune_restore_revive": {"name": "Возрождение", "discipline": "runes_of_restoration",
        "min_rating": 4, "cost": 6, "type": "heal",
        "desc": "Возвращает павшего союзника к жизни (1 раз за бой).", "heal": "3d10"},
    "eldar_rune_restore_life_ward": {"name": "Жизненный Оберег", "discipline": "runes_of_restoration",
        "min_rating": 4, "cost": 4, "type": "buff",
        "desc": "Союзник получает 5+ Feel No Pain.", "buff": {"T": 5}},
    "eldar_rune_restore_soul_keep": {"name": "Хранение Души", "discipline": "runes_of_restoration",
        "min_rating": 5, "cost": 6, "type": "special",
        "desc": "Душа эльдар сохраняется от Слаанеш после смерти."},

    # ============ RUNES OF WARDING (8) ============
    "eldar_rune_ward_shield": {"name": "Щит Рун", "discipline": "runes_of_warding",
        "min_rating": 1, "cost": 2, "type": "buff",
        "desc": "Союзники +1 к спас-броску."},
    "eldar_rune_ward_nullification": {"name": "Обнуление", "discipline": "runes_of_warding",
        "min_rating": 2, "cost": 3, "type": "control",
        "desc": "Отменяет одну психосилу врага."},
    "eldar_rune_ward_witnessing": {"name": "Свидетельство", "discipline": "runes_of_warding",
        "min_rating": 2, "cost": 3, "type": "buff",
        "desc": "Реролл провальных психотестов.", "buff": {"WP": 10}},
    "eldar_rune_ward_bastion": {"name": "Бастион Воли", "discipline": "runes_of_warding",
        "min_rating": 3, "cost": 4, "type": "buff",
        "desc": "Союзники получают Adamantium Will.", "buff": {"WP": 15}},
    "eldar_rune_ward_psychic_veil": {"name": "Психическая Завеса", "discipline": "runes_of_warding",
        "min_rating": 3, "cost": 4, "type": "buff",
        "desc": "Вражеские психосилы -2 к броскам."},
    "eldar_rune_ward_soul_shield": {"name": "Щит Души", "discipline": "runes_of_warding",
        "min_rating": 4, "cost": 5, "type": "buff",
        "desc": "Иммунитет к психическому урону на 1 раунд."},
    "eldar_rune_ward_runes_of_ash": {"name": "Руны Пепла", "discipline": "runes_of_warding",
        "min_rating": 4, "cost": 5, "type": "control",
        "desc": "Враг не может использовать психосилы (1 раунд)."},
    "eldar_rune_ward_ghosthelm": {"name": "Призрачный Шлем", "discipline": "runes_of_warding",
        "min_rating": 5, "cost": 6, "type": "buff",
        "desc": "Полный иммунитет к психосилам на 1 раунд."},

    # ============ RUNES OF CONCEALMENT (8) ============
    "eldar_rune_conceal_shroud": {"name": "Покров", "discipline": "runes_of_concealment",
        "min_rating": 1, "cost": 2, "type": "buff",
        "desc": "Союзники получают Stealth."},
    "eldar_rune_conceal_shadow": {"name": "Тень", "discipline": "runes_of_concealment",
        "min_rating": 2, "cost": 3, "type": "buff",
        "desc": "Союзники получают Shrouded."},
    "eldar_rune_conceal_veil": {"name": "Завеса Тумана", "discipline": "runes_of_concealment",
        "min_rating": 2, "cost": 3, "type": "control",
        "desc": "Враг получает -2 к BS."},
    "eldar_rune_conceal_silence": {"name": "Тишина", "discipline": "runes_of_concealment",
        "min_rating": 3, "cost": 4, "type": "buff",
        "desc": "Отряд не может быть обнаружен (1 раунд)."},
    "eldar_rune_conceal_mirage": {"name": "Мираж", "discipline": "runes_of_concealment",
        "min_rating": 3, "cost": 4, "type": "control",
        "desc": "Враг атакует иллюзию."},
    "eldar_rune_conceal_ghostwalk": {"name": "Призрачный Путь", "discipline": "runes_of_concealment",
        "min_rating": 4, "cost": 4, "type": "utility",
        "desc": "Отряд проходит сквозь стены."},
    "eldar_rune_conceal_harlequin": {"name": "Маска Арлекина", "discipline": "runes_of_concealment",
        "min_rating": 4, "cost": 5, "type": "buff",
        "desc": "Союзник получает 3+ инвульнерабл."},
    "eldar_rune_conceal_webway": {"name": "Паутина", "discipline": "runes_of_concealment",
        "min_rating": 5, "cost": 6, "type": "utility",
        "desc": "Телепортация отряда на любое расстояние."},

    # ============ RUNES OF WAR (10) ============
    "eldar_rune_war_battle_focus": {"name": "Боевой Фокус", "discipline": "runes_of_war",
        "min_rating": 1, "cost": 2, "type": "buff",
        "desc": "Союзники могут бежать и стрелять."},
    "eldar_rune_war_blade": {"name": "Клинок Войны", "discipline": "runes_of_war",
        "min_rating": 2, "cost": 3, "type": "attack",
        "desc": "Атака: 1d10+5 E.", "damage": "1d10+5"},
    "eldar_rune_war_fury": {"name": "Ярость", "discipline": "runes_of_war",
        "min_rating": 2, "cost": 3, "type": "buff",
        "desc": "Союзники +1 A.", "buff": {"S": 5}},
    "eldar_rune_war_doom": {"name": "Рок", "discipline": "runes_of_war",
        "min_rating": 3, "cost": 4, "type": "control",
        "desc": "Враг рероллит успешные спас-броски."},
    "eldar_rune_war_tempest": {"name": "Буря", "discipline": "runes_of_war",
        "min_rating": 3, "cost": 4, "type": "attack",
        "desc": "Атака областью: 2d10+6 E.", "damage": "2d10+6"},
    "eldar_rune_war_psychic_blast": {"name": "Психический Взрыв", "discipline": "runes_of_war",
        "min_rating": 3, "cost": 4, "type": "attack",
        "desc": "Атака: 2d10+7 E.", "damage": "2d10+7"},
    "eldar_rune_war_aspect": {"name": "Аспект", "discipline": "runes_of_war",
        "min_rating": 4, "cost": 5, "type": "buff",
        "desc": "Союзник получает способности Аспектного Воина.",
        "buff": {"WS": 15, "BS": 15}},
    "eldar_rune_war_storm_of_blades": {"name": "Буря Клинков", "discipline": "runes_of_war",
        "min_rating": 4, "cost": 5, "type": "attack",
        "desc": "Атака областью: 3d10+5 E.", "damage": "3d10+5"},
    "eldar_rune_war_phoenix": {"name": "Феникс", "discipline": "runes_of_war",
        "min_rating": 5, "cost": 6, "type": "special",
        "desc": "Автоматическое возрождение при смерти (1 раз за бой)."},
    "eldar_rune_war_asuryan": {"name": "Азуриан", "discipline": "runes_of_war",
        "min_rating": 5, "cost": 7, "type": "attack",
        "desc": "Мощнейший психический удар: 3d10+8 E по всем врагам.",
        "damage": "3d10+8"},
}


def get_disciplines() -> dict:
    return dict(DISCIPLINES)


def _discipline_access(char: dict) -> set:
    if not isinstance(char, dict):
        return set()
    fid = str(char.get("faction_id", "")).lower()
    if fid == "eldar":
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

    ptype = power.get("type", "utility")

    if ptype == "attack":
        if success:
            dmg = _roll_damage(power.get("damage", "1d10"))
            return {"ok": True, "roll": roll, "success": True, "damage": dmg,
                    "text": power["name"] + " бьёт на " + str(dmg) + " урона"}
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
            elif k == "next_roll":
                buffs["next_roll"] = int(v)
        return {"ok": True, "roll": roll, "success": True,
                "text": power["name"] + ": применено"}

    if ptype in ("control", "utility", "special"):
        if not success and ptype != "special":
            char["insanity"] = int(char.get("insanity", 0) or 0) + 1
            return {"ok": True, "roll": roll, "success": False,
                    "text": power["name"] + " сорвалась. +1 Безумие."}
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
