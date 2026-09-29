# PATCH_25
"""services/trade.py — торговля и реквизиция."""
from __future__ import annotations
import random

CATALOG = [
    {"name": "Аптечка", "price": 80, "cat": "consumables"},
    {"name": "Патроны (ящик)", "price": 120, "cat": "consumables"},
    {"name": "Лазпистолет", "price": 300, "cat": "weapons"},
    {"name": "Болтер", "price": 800, "cat": "weapons"},
    {"name": "Флак-броня", "price": 500, "cat": "armour"},
    {"name": "Карапас", "price": 900, "cat": "armour"},
    {"name": "Респиратор", "price": 150, "cat": "consumables"},
    {"name": "Реликварий", "price": 2000, "cat": "artefacts"},
    {"name": "Стимул", "price": 250, "cat": "consumables"},
    {"name": "Вокс-кастер", "price": 400, "cat": "consumables"},
]


def get_price(item: dict, fel: int = 30) -> int:
    base = int(item.get("price", 100))
    discount = max(0, (fel - 30) // 5) * 5
    return max(10, base - base * discount // 100)


def try_buy(char: dict, item: dict, fel: int = 30) -> dict:
    price = get_price(item, fel)
    money = int(char.get("money", 0) or 0)
    if money < price:
        return {"ok": False, "reason": "Не хватает денег",
                "price": price, "money": money}
    char["money"] = money - price
    try:
        from services.inventory import add_item
        add_item(char, item["name"], 1, item.get("cat", ""))
    except Exception:
        pass
    return {"ok": True, "price": price, "money": char["money"]}


def sell_item(char: dict, item_name: str, fel: int = 30) -> dict:
    try:
        from services.inventory import remove_item
        removed = remove_item(char, item_name, 1)
    except Exception:
        removed = False
    if not removed:
        return {"ok": False, "reason": "Нет такого предмета"}
    price = random.randint(30, 150)
    char["money"] = int(char.get("money", 0) or 0) + price
    return {"ok": True, "price": price, "money": char["money"]}
