# scripts/patch.py — PATCH_44: правильный character_creation.py
from __future__ import annotations
import ast, shutil, sys
from pathlib import Path

TAG = "PATCH_44"
ROOT = Path(__file__).resolve().parent.parent
if not (ROOT / "app.py").exists():
    print("[ERROR] app.py не найден.")
    sys.exit(1)

r = {"created": [], "modified": [], "errors": []}


NEW_CC = r'''# PATCH_44
"""services/character_creation.py — генерация и сборка листа по фракции."""
from __future__ import annotations
import random
from datetime import datetime

from services.fallbacks import (
    CHARACTERISTIC_KEYS, FACTIONS, REPUTATION_FACTIONS,
    SUBFACTION_NAMES,
)
from services.faction_starting import (
    get_starting_kit, get_home_world_bonuses, get_career_bonuses,
)


def roll_pool(rng=None):
    r = rng or random.Random()
    return [r.randint(1, 10) + r.randint(1, 10) + 20 for _ in range(9)]


def roll_characteristics(rng=None):
    pool = roll_pool(rng)
    return {k: v for k, v in zip(CHARACTERISTIC_KEYS, pool)}


def auto_distribute(pool):
    ordered = sorted(pool)
    return {k: ordered[i] for i, k in enumerate(CHARACTERISTIC_KEYS)}


def _apply_bonuses(stats, bonus, penalty):
    result = dict(stats)
    for k, v in (bonus or {}).items():
        if k in result:
            result[k] = int(result[k]) + int(v)
    for k, v in (penalty or {}).items():
        if k in result:
            result[k] = int(result[k]) - int(v)
    return result


def _safe_display(fn_name, faction_id, key):
    try:
        from services import fallbacks as _fb
        fn = getattr(_fb, fn_name, None)
        if fn and key:
            return fn(faction_id, key)
    except Exception:
        pass
    return key or ""


def build_character(
    *, name, gender, age, appearance, user_background,
    faction_id, subfaction_id=None,
    home_world_id=None, career_id=None,
    characteristics=None,
):
    if faction_id not in FACTIONS:
        raise ValueError("Неизвестная фракция: " + str(faction_id))

    # 1) Базовые характеристики
    base = characteristics or roll_characteristics()

    # 2) Названия родного мира и карьеры
    hw_name = _safe_display("home_world_display_name", faction_id, home_world_id)
    cr_name = _safe_display("career_display_name", faction_id, career_id)

    # 3) Бонусы от родного мира и карьеры (для не-некронов)
    hw_b = get_home_world_bonuses(faction_id, hw_name)
    cr_b = get_career_bonuses(faction_id, cr_name)
    stats = _apply_bonuses(base, hw_b["bonus"], hw_b["penalty"])
    stats = _apply_bonuses(stats, cr_b["bonus"], cr_b["penalty"])

    # 4) Стартовый набор
    weapons = []
    armour = {"head": 4, "body": 4, "arms": 4, "legs": 4, "notes": "Стандарт"}
    equipment = []
    talents = []
    skills = []
    money = 100
    currency = "Троны"

    if faction_id == "necrons":
        try:
            from services.necrons import get_archetype
            arch = get_archetype(career_id or "")
            if arch:
                # Бонусы к характеристикам
                bonus = arch.get("bonus_characteristics", {}) or {}
                for k, v in bonus.items():
                    if k in stats:
                        stats[k] = int(stats[k]) + int(v)

                # Навыки
                skills = list(arch.get("starting_skills", []))

                # Таланты (только names, ID через реестр)
                for t_id in arch.get("starting_talents", []):
                    talents.append({"id": t_id, "name": t_id})

                # Оружие
                for w_id in arch.get("starting_weapons", []):
                    weapons.append({
                        "id": w_id,
                        "name": w_id,
                        "stats": ""
                    })

                # Броня
                arm_id = arch.get("starting_armour", "")
                if arm_id:
                    armour = {
                        "head": 10, "body": 10, "arms": 10, "legs": 10,
                        "notes": arm_id
                    }

                equipment = ["resurrection_orb"]
                money = 0
                currency = "Нет"

            # Обогащаем именами из data/necrons.json
            try:
                from services.necrons import get_weapon, get_armour_item
                for w in weapons:
                    info = get_weapon(w.get("id"))
                    if info:
                        w["name"] = info.get("name", w["id"])
                        w["stats"] = info.get("damage", "") + " · " + info.get("special", "")
                if armour.get("notes"):
                    arm_info = get_armour_item(armour["notes"])
                    if arm_info:
                        armour["notes"] = arm_info.get("name", armour["notes"])
                        armour["head"] = arm_info.get("all_ap", 10)
                        armour["body"] = arm_info.get("all_ap", 10)
                        armour["arms"] = arm_info.get("all_ap", 10)
                        armour["legs"] = arm_info.get("all_ap", 10)
            except Exception as _e:
                print("[creation] necron names: " + type(_e).__name__)
        except Exception as e:
            print("[creation] necron block fail: " + type(e).__name__ + ": " + str(e))

    else:
        kit = get_starting_kit(faction_id)
        weapons = [dict(w) for w in kit.get("weapons", [])]
        armour = dict(kit.get("armour", armour))
        equipment = list(kit.get("equipment", []))
        talents = [{"id": t, "name": t} for t in kit.get("talents", [])]
        skills = list(kit.get("skills", []))
        money = int(kit.get("money", 100) or 100)
        currency = kit.get("currency", "Троны")

    # 5) Раны и судьба
    tb = stats.get("T", 30) // 10
    wounds_max = random.randint(1, 5) + 1 + 2 * tb
    fate_max = 2 if random.randint(1, 10) >= 8 else 1
    if faction_id == "necrons":
        wounds_max += 3  # Некроны крепче

    # 6) Субфракция
    faction = FACTIONS[faction_id]
    sub_key = subfaction_id
    if sub_key and sub_key not in faction.get("subfactions", []):
        sub_key = None
    sub_display = SUBFACTION_NAMES.get(sub_key, sub_key or "")

    # 7) Архетип для некронов
    archetype_id = career_id if faction_id == "necrons" else None
    if archetype_id:
        try:
            from services.necrons import get_archetype
            arch = get_archetype(archetype_id) or {}
            cr_name = arch.get("name", cr_name)
        except Exception:
            pass

    now = datetime.now().isoformat(timespec="microseconds")

    necron_traits = []
    if faction_id == "necrons":
        try:
            from services.necrons import get_faction_traits
            necron_traits = list(get_faction_traits().keys())
        except Exception:
            pass

    return {
        "name": name, "gender": gender, "age": age,
        "appearance": appearance,
        "user_background": user_background,
        "background": user_background or "(не задано)",
        "faction": faction["name"], "faction_id": faction_id,
        "subfaction": sub_display, "subfaction_id": sub_key or "",
        "home_world_id": home_world_id or "",
        "home_world_name": hw_name,
        "career_id": career_id or "",
        "career_name": cr_name,
        "archetype": archetype_id or "",
        "archetype_id": archetype_id or "",
        "extra_choices": {},
        "characteristics": stats,
        "bonuses": {k: 0 for k in CHARACTERISTIC_KEYS},
        "skills": skills,
        "talents": talents,
        "weapons": weapons,
        "equipment": equipment,
        "armour": armour,
        "wounds": {"current": wounds_max, "max": wounds_max},
        "fate_points": {"current": fate_max, "max": fate_max},
        "psy_rating": 2 if faction_id == "eldar" and "Провидца" in cr_name else 0,
        "psychic_powers": [],
        "corruption": 0, "insanity": 0,
        "money": money, "currency": currency,
        "special_resources": {},
        "extra_currencies": {},
        "ship": {"name": "", "class": "", "type": "", "description": "",
                 "hull": "", "crew": "", "weapons": [], "features": [],
                 "status": ""},
        "location": "", "game_date": "Начало приключения",
        "quests": [], "npcs": [], "effects": [], "companions": [],
        "goals": [], "journal": [], "notes": "",
        "player_notes": [],
        "reputation": {f: 0 for f in REPUTATION_FACTIONS},
        "generation_method": "roll+distribute",
        "xp": 300, "rank": 1, "created_at": now,
        "necron_traits": necron_traits,
    }
'''


def _bk(p):
    b = p.with_suffix(p.suffix + ".bak_pre_" + TAG)
    if not b.exists() and p.exists():
        try:
            shutil.copy2(p, b)
        except Exception:
            pass


p = ROOT / "services" / "character_creation.py"
try:
    ast.parse(NEW_CC)
except SyntaxError as e:
    r["errors"].append("NEW_CC syntax: " + str(e))
    print("=== PATCH " + TAG + " ===")
    for e in r["errors"]:
        print("  [ERROR] " + e)
    sys.exit(1)

_bk(p)
p.write_text(NEW_CC, encoding="utf-8")
r["modified"].append("services/character_creation.py (полная перезапись)")

print("=== PATCH " + TAG + " ===")
for k in ("created", "modified"):
    for x in r[k]:
        print("  [" + k.upper() + "] " + x)
for e in r["errors"]:
    print("  [ERROR] " + e)
print("DONE" if not r["errors"] else "DONE (with errors)")