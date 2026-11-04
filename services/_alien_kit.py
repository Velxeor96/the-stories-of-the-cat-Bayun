"""services/_alien_kit.py — универсальный сборщик стартового кита alien-фракций.

Используется для DLC-фракций (некроны, тираниды и любые будущие).
Ожидает от модуля services.<faction_id>:
  - get_archetype(id) -> dict
  - get_weapon(id) -> dict
  - get_armour_item(id) -> dict
  - get_faction_traits() -> dict
Опционально: get_talent(id) -> dict

Если модуль сам предоставляет build_starting_kit(career_id, faction_id) —
диспетчер в character_creation.py вызовет его вместо этого generic-билдера.
"""

# Fallback-экипировка для обратной совместимости с уже написанными модулями.
# Когда modules получат archetype["starting_equipment"] — этот словарь станет
# неиспользуемым.
_FALLBACK_EQUIPMENT = {
    "necrons": ["resurrection_orb"],
    "tyranids": ["adrenal_gland"],
}


def build_kit(svc, career_id, faction_id):
    out = {
        "skills": [],
        "talents": [],
        "weapons": [],
        "armour": {},
        "equipment": [],
        "traits": [],
        "archetype_name": career_id or "",
        "wounds_bonus": 0,
        "bonus_characteristics": {},
        "money": 0,
        "currency": "Нет",
    }

    try:
        arch = svc.get_archetype(career_id or "")
    except Exception:
        arch = None

    if not arch:
        out["equipment"] = list(_FALLBACK_EQUIPMENT.get(faction_id, []))
        return out

    out["archetype_name"] = arch.get("name", career_id or "")
    out["bonus_characteristics"] = dict(arch.get("bonus_characteristics", {}) or {})
    out["skills"] = list(arch.get("starting_skills", []))

    for t_id in arch.get("starting_talents", []):
        t_obj = None
        if hasattr(svc, "get_talent"):
            try:
                t_obj = svc.get_talent(t_id)
            except Exception:
                t_obj = None
        out["talents"].append({
            "id": t_id,
            "name": (t_obj or {}).get("name", t_id),
        })

    for w_id in arch.get("starting_weapons", []):
        try:
            w = svc.get_weapon(w_id)
        except Exception:
            w = None
        if w:
            out["weapons"].append({
                "id": w_id,
                "name": w.get("name", w_id),
                "stats": str(w.get("damage", "")) + " · " + str(w.get("special", "")),
            })
        else:
            out["weapons"].append({"id": w_id, "name": w_id, "stats": ""})

    arm_id = arch.get("starting_armour", "")
    if arm_id:
        try:
            arm = svc.get_armour_item(arm_id)
        except Exception:
            arm = None
        if arm:
            ap = arm.get("all_ap", 8)
            out["armour"] = {
                "head": ap, "body": ap, "arms": ap, "legs": ap,
                "notes": arm.get("name", "Карапас"),
            }

    try:
        out["traits"] = list(svc.get_faction_traits().keys())
    except Exception:
        pass

    out["wounds_bonus"] = int(arch.get("wounds_bonus", 0) or 0)

    if arch.get("starting_equipment"):
        out["equipment"] = list(arch["starting_equipment"])
    else:
        out["equipment"] = list(_FALLBACK_EQUIPMENT.get(faction_id, []))

    return out
