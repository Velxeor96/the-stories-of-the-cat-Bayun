# fallbacks_currencies.py
# Валюты и стартовые ресурсы по фракциям.

CURRENCY_BY_FACTION = {
    "imperium": {
        "currency_name": "Троны",
        "currency_start": 200,
        "special_resources": {},
    },
    "chaos": {
        "currency_name": "Подношения",
        "currency_start": 100,
        "special_resources": {},
    },
    "eldar": {
        "currency_name": "Дары",
        "currency_start": 0,
        "special_resources": {"Камни Души": 1},
    },
    "orks": {
        "currency_name": "Зубы",
        "currency_start": 50,
        "special_resources": {},
    },
    "tau": {
        "currency_name": "Кредиты Тау",
        "currency_start": 500,
        "special_resources": {},
    },
    "necrons": {
        "currency_name": "Энергия",
        "currency_start": 0,
        "special_resources": {},
    },
    "tyranids": {
        "currency_name": "Биомасса",
        "currency_start": 0,
        "special_resources": {},
    },
}

DEFAULT_CURRENCY = {
    "currency_name": "Троны",
    "currency_start": 0,
    "special_resources": {},
}