# scripts/patch.py — PATCH_82: Tyranids + Orks + blocked factions
from __future__ import annotations
import ast, shutil, sys
from pathlib import Path

TAG = "PATCH_82"
ROOT = Path(__file__).resolve().parent.parent
if not (ROOT / "app.py").exists():
    print("[ERROR] app.py не найден.")
    sys.exit(1)

r = {"modified": [], "errors": []}


def _bk(p):
    b = p.with_suffix(p.suffix + ".bak_pre_" + TAG)
    if not b.exists() and p.exists():
        try:
            shutil.copy2(p, b)
        except Exception:
            pass


def _write_module(rel, content):
    p = ROOT / rel
    _bk(p)
    p.write_text(content, encoding="utf-8")
    try:
        ast.parse(content)
        r["modified"].append(rel + " — записан")
    except SyntaxError as e:
        r["errors"].append(rel + " syntax: " + str(e) + " (line " + str(e.lineno) + ")")


# ============================================================
# 1) services/psychic_tyranid.py — 24 силы Тиранидов
# ============================================================
PSY_TYRANID = '''"""services/psychic_tyranid.py — психосилы Тиранидов (Hive Mind).

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
    m = re.match(r"(\\d+)d(\\d+)([+\\-]\\d+)?", str(expr))
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
'''
_write_module("services/psychic_tyranid.py", PSY_TYRANID)


# ============================================================
# 2) services/psychic_ork.py — 16 сил Орков (WAAAGH!)
# ============================================================
PSY_ORK = '''"""services/psychic_ork.py — психосилы Орков (WAAAGH!).

Орочьи психосилы = WAAAGH!-энергия. Чем больше орков рядом,
тем сильнее Вирдбой. Никакой Порчи, никакого Безумия —
только зелёная ярость.

ДИСЦИПЛИНЫ (2):
- waaagh (8)     — классические силы Вирдбоя
- mork_gork (8)  — силы Морка и Горка (Вуррбой, Психобой)
"""
from __future__ import annotations
import random
import re

DISCIPLINES = {
    "waaagh":    "WAAAGH! (Вирдбой)",
    "mork_gork": "Силы Морка и Горка (Вуррбой)",
}


PSY_POWERS = {
    # ============ WAAAGH (8) ============
    "ork_eadbanger": {"name": "Мозголом", "discipline": "waaagh",
        "min_rating": 1, "cost": 2, "type": "attack",
        "desc": "Атака: 2d10+5 E в разум одной цели.", "damage": "2d10+5"},
    "ork_frazzle": {"name": "Фраззл", "discipline": "waaagh",
        "min_rating": 1, "cost": 2, "type": "attack",
        "desc": "Атака: 2d10+4 E, оглушает цель.", "damage": "2d10+4"},
    "ork_da_jump": {"name": "Прыжок", "discipline": "waaagh",
        "min_rating": 2, "cost": 3, "type": "utility",
        "desc": "Телепортирует отряд орков в любую точку поля."},
    "ork_warpath": {"name": "Тропа Войны", "discipline": "waaagh",
        "min_rating": 2, "cost": 3, "type": "buff",
        "desc": "Все орки в зоне получают +1 A и ярость.",
        "buff": {"S": 10}},
    "ork_gift_of_waaagh": {"name": "Дар WAAAGH!", "discipline": "waaagh",
        "min_rating": 3, "cost": 3, "type": "buff",
        "desc": "Один орк получает +20 S на сцену.",
        "buff": {"S": 20}},
    "ork_psychic_vomit": {"name": "Психическая Блевотина", "discipline": "waaagh",
        "min_rating": 3, "cost": 4, "type": "attack",
        "desc": "Атака областью: 2d10+6 E, отравляет.", "damage": "2d10+6"},
    "ork_roar_of_mork": {"name": "Рёв Морка", "discipline": "waaagh",
        "min_rating": 4, "cost": 4, "type": "control",
        "desc": "Враги в зоне теряют действие от рёва."},
    "ork_blood_axe": {"name": "Кровавый Топор", "discipline": "waaagh",
        "min_rating": 5, "cost": 5, "type": "attack",
        "desc": "Призрачный топор Горка: 3d10+8 R по всем врагам.",
        "damage": "3d10+8"},

    # ============ MORK_GORK (8) ============
    "ork_power_vomit": {"name": "Мощная Блевотина", "discipline": "mork_gork",
        "min_rating": 1, "cost": 2, "type": "attack",
        "desc": "Атака: 2d10+5 E, сбивает с ног.", "damage": "2d10+5"},
    "ork_morks_roar": {"name": "Рёв Морка (Усиленный)", "discipline": "mork_gork",
        "min_rating": 2, "cost": 3, "type": "control",
        "desc": "Все враги в зоне получают -20 Ld и бегут."},
    "ork_ere_we_go": {"name": "Вперёд, парни!", "discipline": "mork_gork",
        "min_rating": 2, "cost": 3, "type": "buff",
        "desc": "Отряд орков получает +3 дюйма к движению и реролл чарджа."},
    "ork_waaagh_shout": {"name": "Крик WAAAGH!", "discipline": "mork_gork",
        "min_rating": 3, "cost": 4, "type": "buff",
        "desc": "Все орки в радиусе получают +1 A и Fearless.",
        "buff": {"S": 5, "WP": 5}},
    "ork_bash": {"name": "Затрещина", "discipline": "mork_gork",
        "min_rating": 3, "cost": 3, "type": "attack",
        "desc": "Атака: 2d10+6 I, игнорирует броню.", "damage": "2d10+6"},
    "ork_kunnin_plan": {"name": "Хитрая Мысль", "discipline": "mork_gork",
        "min_rating": 4, "cost": 4, "type": "utility",
        "desc": "Даёт оркам реролл одного броска в сцене."},
    "ork_bigga_brains": {"name": "Огромные Мозги", "discipline": "mork_gork",
        "min_rating": 4, "cost": 4, "type": "buff",
        "desc": "+15 Int, +15 WP на сцену.",
        "buff": {"Int": 15, "WP": 15}},
    "ork_warphead": {"name": "Варпоголовый", "discipline": "mork_gork",
        "min_rating": 5, "cost": 6, "type": "special",
        "desc": "Открывает варп-разлом: 3d10+7 E по всем врагам в зоне.",
        "damage": "3d10+7"},
}


def get_disciplines() -> dict:
    return dict(DISCIPLINES)


def _discipline_access(char: dict) -> set:
    if not isinstance(char, dict):
        return set()
    fid = str(char.get("faction_id", "")).lower()
    cid = str(char.get("career_id", "")).lower()
    if fid in ("ork", "orks", "orc"):
        return set(DISCIPLINES.keys())
    if "weirdboy" in cid or "wurrboy" in cid or "psyk" in cid:
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
    m = re.match(r"(\\d+)d(\\d+)([+\\-]\\d+)?", str(expr))
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

    wp = int((char.get("characteristics") or {}).get("WP", 30))
    roll = random.randint(1, 100)
    # У орков психотест: roll <= WP, крит.успех = дубль (11, 22, ...)
    success = roll <= wp
    crit_success = roll % 11 == 0 and roll <= 88  # дубли до 88
    crit_fail = roll >= 96
    char["psy_charge"] = charge - cost
    # Провал у орков = Перильная голова (урон себе), а не Безумие
    headbang_txt = ""
    if not success:
        dmg_self = random.randint(1, 5)
        w = char.setdefault("wounds", {})
        cur = int(w.get("current", 0) or 0)
        w["current"] = max(0, cur - dmg_self)
        headbang_txt = " [Перильная голова: -" + str(dmg_self) + " ран]"

    ptype = power.get("type", "utility")

    if ptype == "attack":
        if success:
            dmg = _roll_damage(power.get("damage", "1d10"))
            if crit_success:
                dmg *= 2
                return {"ok": True, "roll": roll, "success": True, "damage": dmg,
                        "text": power["name"] + " КРИТ! " + str(dmg) + " урона!"}
            return {"ok": True, "roll": roll, "success": True, "damage": dmg,
                    "text": power["name"] + " бьёт на " + str(dmg) + " урона"}
        return {"ok": True, "roll": roll, "success": False, "damage": 0,
                "text": power["name"] + " сорвалась." + headbang_txt}

    if ptype == "heal":
        if not success:
            return {"ok": True, "roll": roll, "success": False,
                    "text": power["name"] + " сорвалась." + headbang_txt}
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
        return {"ok": True, "roll": roll, "success": True,
                "text": power["name"] + ": применено"}

    if ptype in ("control", "utility", "special"):
        if not success and ptype != "special":
            return {"ok": True, "roll": roll, "success": False,
                    "text": power["name"] + " сорвалась." + headbang_txt}
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
'''
_write_module("services/psychic_ork.py", PSY_ORK)


# ============================================================
# 3) services/psychic.py — диспетчер с tyranid, ork, blocked
# ============================================================
PSY_DISPATCHER = '''"""services/psychic.py — диспетчер пси-сил по фракциям.

Модули:
- human     — Империум (Astropath / Sanctioned Psyker и др.)
- navigator — Навигатор (Imperium)
- chaos     — Хаос (5 дисциплин, favor-механика)
- eldar     — Эльдар (6 рунических дисциплин)
- tyranid   — Тираниды (Hive Mind / Broodmind / Biomancy)
- ork       — Орки (WAAAGH! / Mork & Gork)

Заблокированы (нет псайкеров по лору):
- necron    — используют технологии, не Варп
- drukhari  — Слаанеш пожирает их души при психосиле
- tau       — нет врождённых псайкеров
"""
from __future__ import annotations

from services import psychic_human
from services import psychic_navigator
from services import psychic_chaos
from services import psychic_eldar
from services import psychic_tyranid
from services import psychic_ork


_HUMAN_ASTROPATH_CAREERS = {"astropath", "астропат"}
_HUMAN_NAVIGATOR_CAREERS = {"navigator", "навигатор"}

# Фракции без психосил
_BLOCKED_FACTIONS = {"necron", "necrons", "drukhari", "dark_eldar", "tau", "t_au"}

# Русские названия для UI
_BLOCKED_REASONS = {
    "necron": "Некроны не используют Варп — только технологии Ка'тан.",
    "necrons": "Некроны не используют Варп — только технологии Ка'тан.",
    "drukhari": "Друкхари не могут использовать психосилы: Слаанеш пожирает их души.",
    "dark_eldar": "Тёмные Эльдар не могут использовать психосилы: Слаанеш пожирает их души.",
    "tau": "У Тау нет врождённых псайкеров.",
    "t_au": "У Тау нет врождённых псайкеров.",
}


def _classify(char: dict) -> dict:
    fid = str(char.get("faction_id", "")).lower()
    sfid = str(char.get("subfaction_id", "")).lower()
    cid = str(char.get("career_id", "")).lower()
    cname = str(char.get("career_name", ""))
    rating = int(char.get("psy_rating", 0) or 0)

    out = {"module": None, "chaos_only": False, "astropath_only": False,
           "has_psy": rating > 0, "blocked": False, "blocked_reason": ""}

    # === ЗАБЛОКИРОВАННЫЕ ===
    if fid in _BLOCKED_FACTIONS:
        out["blocked"] = True
        out["blocked_reason"] = _BLOCKED_REASONS.get(
            fid, "Эта фракция не имеет психосил.")
        return out

    if fid == "imperium":
        if cid in _HUMAN_NAVIGATOR_CAREERS or cname in _HUMAN_NAVIGATOR_CAREERS:
            out["module"] = "navigator"
            return out
        if cid in _HUMAN_ASTROPATH_CAREERS or cname in _HUMAN_ASTROPATH_CAREERS:
            out["module"] = "human"
            out["astropath_only"] = True
            return out
        out["module"] = "human"
        return out

    if fid == "chaos":
        out["module"] = "chaos"
        return out

    if fid in ("eldar", "aeldari"):
        out["module"] = "eldar"
        return out

    if fid in ("tyranid", "tyranids"):
        out["module"] = "tyranid"
        return out

    if fid in ("ork", "orks", "orc"):
        out["module"] = "ork"
        return out

    return out


def is_blocked(char: dict) -> bool:
    """True, если фракция принципиально не имеет психосил."""
    if not isinstance(char, dict):
        return False
    return _classify(char).get("blocked", False)


def get_blocked_reason(char: dict) -> str:
    if not isinstance(char, dict):
        return ""
    return _classify(char).get("blocked_reason", "")


def get_disciplines(char: dict = None) -> dict:
    if not char:
        return {}
    info = _classify(char)
    m = info["module"]
    if m == "human":
        return psychic_human.get_disciplines()
    if m == "navigator":
        return psychic_navigator.get_disciplines()
    if m == "chaos":
        return psychic_chaos.get_disciplines()
    if m == "eldar":
        return psychic_eldar.get_disciplines()
    if m == "tyranid":
        return psychic_tyranid.get_disciplines()
    if m == "ork":
        return psychic_ork.get_disciplines()
    return {}


def get_powers(char: dict) -> list:
    info = _classify(char)
    m = info["module"]
    if m == "human":
        return psychic_human.get_powers(
            char, chaos_only=info["chaos_only"],
            astropath_only=info["astropath_only"])
    if m == "navigator":
        return psychic_navigator.get_powers(char)
    if m == "chaos":
        return psychic_chaos.get_powers(char)
    if m == "eldar":
        return psychic_eldar.get_powers(char)
    if m == "tyranid":
        return psychic_tyranid.get_powers(char)
    if m == "ork":
        return psychic_ork.get_powers(char)
    return []


def get_power(power_id: str):
    for mod in (psychic_human, psychic_navigator, psychic_chaos,
                psychic_eldar, psychic_tyranid, psychic_ork):
        p = mod.get_power(power_id)
        if p:
            return p
    return None


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


def cast(char: dict, power_key: str) -> dict:
    info = _classify(char)
    m = info["module"]
    if info["blocked"]:
        return {"ok": False, "reason": info["blocked_reason"]}
    if not m:
        return {"ok": False, "reason": "нет доступа к психосилам"}
    if m == "human":
        return psychic_human.cast(
            char, power_key, chaos_only=info["chaos_only"],
            astropath_only=info["astropath_only"])
    if m == "navigator":
        return psychic_navigator.cast(char, power_key)
    if m == "chaos":
        return psychic_chaos.cast(char, power_key)
    if m == "eldar":
        return psychic_eldar.cast(char, power_key)
    if m == "tyranid":
        return psychic_tyranid.cast(char, power_key)
    if m == "ork":
        return psychic_ork.cast(char, power_key)
    return {"ok": False, "reason": "нет доступа"}


def full_catalog(char: dict) -> dict:
    info = _classify(char)
    rating = int(char.get("psy_rating", 0) or 0)
    m = info["module"]
    if info["blocked"] or not m:
        return {}
    if m == "human":
        return psychic_human.full_catalog(
            rating, chaos_only=info["chaos_only"],
            astropath_only=info["astropath_only"])
    if m == "navigator":
        return psychic_navigator.full_catalog(rating)
    if m == "chaos":
        return psychic_chaos.full_catalog(rating, char=char)
    if m == "eldar":
        return psychic_eldar.full_catalog(rating, char=char)
    if m == "tyranid":
        return psychic_tyranid.full_catalog(rating, char=char)
    if m == "ork":
        return psychic_ork.full_catalog(rating, char=char)
    return {}


def has_access(char: dict) -> bool:
    if not isinstance(char, dict):
        return False
    info = _classify(char)
    if info["blocked"]:
        return False
    return bool(info["module"]) and int(char.get("psy_rating", 0) or 0) > 0


# ================ FAVOR (Chaos) ================

def get_favor_level(char: dict, god: str) -> int:
    return psychic_chaos.get_favor_level(char, god)


def add_favor(char: dict, god: str, amount: int) -> None:
    psychic_chaos.add_favor(char, god, amount)


def get_all_favor(char: dict) -> dict:
    return psychic_chaos.get_all_favor(char)
'''
_write_module("services/psychic.py", PSY_DISPATCHER)


print("=== PATCH " + TAG + " ===")
for m in r["modified"]:
    print("  [MODIFIED] " + m)
for e in r["errors"]:
    print("  [ERROR] " + e)
print("DONE" if not r["errors"] else "DONE (with errors)")