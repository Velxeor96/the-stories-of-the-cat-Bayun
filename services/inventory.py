# PATCH_24A
"""services/inventory.py — категоризированный инвентарь."""
from __future__ import annotations

CATEGORIES = ["weapons", "armour", "consumables", "artefacts", "quest"]
CATEGORY_RU = {"weapons": "Оружие", "armour": "Броня",
               "consumables": "Расходники", "artefacts": "Артефакты",
               "quest": "Квестовое"}

KW = {
    "weapons": ["пистолет", "винтовка", "катапульта", "меч", "клинок",
                "нож", "топор", "болтер", "лазган", "лазпистолет",
                "сюрикен", "копьё", "копье", "молот", "посох", "пика"],
    "armour": ["броня", "бодисьют", "доспех", "щит", "шлем", "плащ",
               "карапас", "манти"],
    "consumables": ["аптечка", "зелье", "стим", "стимул", "фляга",
                    "паёк", "паек", "провизия", "боеприпас", "магазин",
                    "патрон"],
    "artefacts": ["камень", "руна", "диадема", "амулет", "талисман",
                  "сфера", "артефакт", "реликвия", "кристалл", "оже"],
    "quest": ["документ", "грамота", "ключ", "карта", "письмо",
              "пропуск", "жетон", "печать"],
}


def _auto_category(name: str) -> str:
    low = (name or "").lower()
    for cat in ("weapons", "armour", "quest", "artefacts", "consumables"):
        for kw in KW[cat]:
            if kw in low:
                return cat
    return "consumables"


def get_inventory(char: dict) -> dict:
    if not isinstance(char, dict):
        return {c: [] for c in CATEGORIES}
    inv = char.get("inventory")
    if not isinstance(inv, dict):
        inv = {c: [] for c in CATEGORIES}
        char["inventory"] = inv
        for it in (char.get("equipment") or []):
            nm = it.get("name") if isinstance(it, dict) else str(it)
            cat = _auto_category(nm)
            inv[cat].append({"name": nm, "qty": 1})
    for c in CATEGORIES:
        if c not in inv:
            inv[c] = []
    return inv


def add_item(char, name, qty=1, category=""):
    inv = get_inventory(char)
    cat = category if category in CATEGORIES else _auto_category(name)
    for it in inv[cat]:
        if it.get("name") == name:
            it["qty"] = int(it.get("qty", 1)) + int(qty)
            return
    inv[cat].append({"name": name, "qty": int(qty)})


def remove_item(char, name, qty=1):
    inv = get_inventory(char)
    for cat in CATEGORIES:
        for i, it in enumerate(inv[cat]):
            if it.get("name") == name:
                cur = int(it.get("qty", 1))
                if cur <= qty:
                    inv[cat].pop(i)
                else:
                    it["qty"] = cur - qty
                return True
    return False


def total_items(char) -> int:
    inv = get_inventory(char)
    return sum(len(inv[c]) for c in CATEGORIES)
