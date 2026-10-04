# PATCH_41
"""services/talents_registry.py — универсальный реестр талантов.

Собирает таланты из разных источников (некроны, тираниды, общие).
"""
from __future__ import annotations


def _sources_for(faction_id: str) -> list:
    """Возвращает список источников (модулей) для фракции."""
    sources = []
    if faction_id == "necrons":
        try:
            from services import necrons
            sources.append(necrons)
        except Exception as e:
            print("[talents_registry] necrons: " + str(e))
    # Тираниды — TODO
    # if faction_id == "tyranids":
    #     from services import tyranids
    #     sources.append(tyranids)
    return sources


def get_talent(talent_id: str):
    """Ищет талант во всех зарегистрированных источниках."""
    try:
        from services import necrons
        t = necrons.get_talent(talent_id)
        if t:
            return t
    except Exception:
        pass
    return None


def list_talents_for_faction(faction_id: str) -> list:
    """Все таланты, доступные фракции."""
    out = []
    for src in _sources_for(faction_id):
        getter = getattr(src, "get_talents", None)
        if callable(getter):
            out.extend(getter())
    return out


def is_talent_owned(char: dict, talent_id: str) -> bool:
    """Проверяет, куплен ли уже талант."""
    owned = char.get("talents", []) or []
    for t in owned:
        if isinstance(t, dict):
            if t.get("id") == talent_id:
                return True
        elif str(t) == talent_id:
            return True
    # Проверка по имени
    tal = get_talent(talent_id)
    if tal:
        name = tal.get("name", "")
        for t in owned:
            if isinstance(t, dict) and t.get("name") == name:
                return True
            elif str(t) == name:
                return True
    return False


def check_prerequisites(char: dict, talent_id: str) -> tuple:
    """Проверка требований. Делегирует источнику, если он умеет."""
    try:
        from services import necrons
        if necrons.get_talent(talent_id):
            return necrons.check_talent_prerequisites(char, talent_id)
    except Exception:
        pass
    return True, ""


def buy_talent(char: dict, talent_id: str) -> tuple:
    """Универсальная покупка."""
    try:
        from services import necrons
        if necrons.get_talent(talent_id):
            return necrons.buy_talent(char, talent_id)
    except Exception as e:
        return False, "Ошибка: " + str(e)
    return False, "Источник таланта не найден."


def list_available(char: dict) -> list:
    """Возвращает список талантов с их статусом для UI.
    
    Каждый элемент:
        {
            "id": str, "name": str, "cost": int, "tier": int,
            "category": str, "description": str, "effect": str,
            "available": bool, "reason": str, "owned": bool,
        }
    """
    faction_id = str(char.get("faction_id", "") or "")
    out = []
    for t in list_talents_for_faction(faction_id):
        tid = t.get("id")
        if not tid:
            continue
        owned = is_talent_owned(char, tid)
        if owned:
            out.append({
                "id": tid, "name": t.get("name", tid),
                "cost": int(t.get("cost", 0)),
                "tier": int(t.get("tier", 1)),
                "category": t.get("category", "other"),
                "description": t.get("description", ""),
                "effect": t.get("effect", ""),
                "available": False,
                "reason": "Уже изучен",
                "owned": True,
            })
            continue
        ok, reason = check_prerequisites(char, tid)
        xp = int(char.get("xp", 0) or 0)
        cost = int(t.get("cost", 0))
        if ok and xp < cost:
            ok = False
            reason = "Нужно XP: " + str(cost) + " (есть " + str(xp) + ")"
        out.append({
            "id": tid, "name": t.get("name", tid),
            "cost": cost,
            "tier": int(t.get("tier", 1)),
            "category": t.get("category", "other"),
            "description": t.get("description", ""),
            "effect": t.get("effect", ""),
            "available": ok,
            "reason": reason if not ok else "",
            "owned": False,
        })
    # Сортировка: доступные сверху, потом по tier, потом по имени
    out.sort(key=lambda x: (x["owned"], not x["available"], x["tier"], x["name"]))
    return out


if __name__ == "__main__":
    # Простая проверка
    fake = {
        "faction_id": "necrons",
        "rank": 1,
        "xp": 800,
        "characteristics": {"WS": 40, "BS": 40, "T": 40, "WP": 40},
        "talents": [],
        "skills": [],
    }
    print("Талантов для некрона:", len(list_available(fake)))
    for t in list_available(fake)[:5]:
        status = "✓ доступен" if t["available"] else ("★ изучен" if t["owned"] else "✗ " + t["reason"])
        print(f"  [{t['tier']}] {t['name']} — {t['cost']} XP — {status}")
