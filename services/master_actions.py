"""services/master_actions.py — применение изменений от ГМ-а к персонажу."""
from __future__ import annotations

def acquire_ship(char: dict, reason: str = "") -> str:
    char["has_ship"] = True
    char.setdefault("journal", []).append({
        "type": "ship_acquired",
        "reason": reason or "Получен корабль",
        "turn": char.get("turn", 0),
    })
    return "Корабль получен."

def lose_ship(char: dict, reason: str = "") -> str:
    char["has_ship"] = False
    char.pop("ship", None)
    char.setdefault("journal", []).append({
        "type": "ship_lost",
        "reason": reason or "Корабль потерян",
    })
    return "Корабль потерян."

def add_item(char: dict, item_id: str, qty: int = 1) -> None:
    inv = char.setdefault("inventory", [])
    for e in inv:
        if e.get("id") == item_id:
            e["qty"] = int(e.get("qty", 0)) + qty
            return
    inv.append({"id": item_id, "qty": qty})

def remove_item(char: dict, item_id: str, qty: int = 1) -> None:
    inv = char.get("inventory", [])
    for e in list(inv):
        if e.get("id") == item_id:
            e["qty"] = int(e.get("qty", 1)) - qty
            if e["qty"] <= 0:
                inv.remove(e)
            return

def set_flag(char: dict, key: str, value) -> None:
    char.setdefault("flags", {})[key] = value

def award_xp(char: dict, amount: int) -> None:
    char["xp"] = int(char.get("xp", 0) or 0) + int(amount)

def apply_changes(char: dict, changes: dict) -> list:
    log = []
    if not isinstance(changes, dict):
        return ["invalid"]
    if changes.get("acquire_ship"):
        reason = changes["acquire_ship"].get("reason", "") if isinstance(changes["acquire_ship"], dict) else str(changes["acquire_ship"])
        acquire_ship(char, reason); log.append("acquire_ship")
    if changes.get("lose_ship"):
        lose_ship(char, str(changes["lose_ship"])); log.append("lose_ship")
    for it in (changes.get("inventory_add") or []):
        add_item(char, it.get("id", ""), int(it.get("qty", 1)))
        log.append("add:" + str(it.get("id", "")))
    for it in (changes.get("inventory_remove") or []):
        remove_item(char, it.get("id", ""), int(it.get("qty", 1)))
        log.append("remove:" + str(it.get("id", "")))
    for k, v in (changes.get("flags_set") or {}).items():
        set_flag(char, k, v); log.append("flag:" + str(k))
    if changes.get("xp_award"):
        award_xp(char, int(changes["xp_award"])); log.append("xp:" + str(changes["xp_award"]))
    if changes.get("journal"):
        char.setdefault("journal", []).append({
            "type": "event", "text": str(changes["journal"]), "turn": char.get("turn", 0)
        })
        log.append("journal")
    return log
