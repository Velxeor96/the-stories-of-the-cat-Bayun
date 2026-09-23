"""services/fallbacks.py — статические справочники для создания персонажа.

Данные перенесены из старого проекта в читаемом виде. Не импортируем
_reference_from_old, чтобы новый проект был самодостаточным.
"""
from __future__ import annotations

# ============================================================
# Характеристики
# ============================================================
CHARACTERISTIC_KEYS = ["WS", "BS", "S", "T", "Ag", "Int", "Per", "WP", "Fel"]

CHARACTERISTIC_NAMES = {
    "WS":  "Рукопашный бой",
    "BS":  "Стрельба",
    "S":   "Сила",
    "T":   "Стойкость",
    "Ag":  "Ловкость",
    "Int": "Интеллект",
    "Per": "Восприятие",
    "WP":  "Воля",
    "Fel": "Общительность",
}


# ============================================================
# Фракции → человекочитаемые названия и сабфракции
# ============================================================
FACTIONS = {
    "imperium": {
        "name": "Империум Человечества",
        "subfactions": ["rogue_trader", "space_marine", "imperial_guard",
                        "mechanicus", "sororitas", "arbites"],
    },
    "chaos": {
        "name": "Силы Хаоса",
        "subfactions": ["chaos_marine", "dark_mechanicum", "cultist"],
    },
    "eldar": {
        "name": "Эльдары",
        "subfactions": ["asuryani", "harlequin", "exodite"],
    },
    "drukhari": {
        "name": "Друкхари",
        "subfactions": ["drukhari"],
    },
    "orks": {
        "name": "Орки",
        "subfactions": ["freebooter"],
    },
    "tau": {
        "name": "Тау",
        "subfactions": ["tau"],
    },
    "necrons": {
        "name": "Некроны",
        "subfactions": ["necron"],
    },
    "genestealers": {
        "name": "Генокрады",
        "subfactions": ["genestealer"],
    },
}


SUBFACTION_NAMES = {
    "rogue_trader":     "Вольный Торговец",
    "space_marine":     "Космодесантник",
    "imperial_guard":   "Имперская Гвардия",
    "mechanicus":       "Механикус",
    "sororitas":        "Сестра Битвы",
    "arbites":          "Арбитр",
    "chaos_marine":     "Космодесантник Хаоса",
    "dark_mechanicum":  "Тёмный Механикум",
    "cultist":          "Культист",
    "asuryani":         "Асуряни",
    "harlequin":        "Арлекин",
    "exodite":          "Экзодит",
    "drukhari":         "Друкари",
    "freebooter":       "Орк-флибустьер",
    "tau":              "Тау",
    "necron":           "Некрон",
    "genestealer":      "Генокрад",
}


DEFAULT_ARCHETYPE = {
    "imperium":     "captain",
    "chaos":        "champion",
    "eldar":        "warrior",
    "drukhari":     "kabalite",
    "orks":         "freebooter",
    "tau":          "firewarrior",
    "necrons":      "lord",
    "genestealers": "magus",
}


# ============================================================
# Броня / раны / судьба / таланты / оружие / снаряжение
# ============================================================
ULTIMATE_FALLBACK = {
    "armour": {
        "head": 4, "body": 4, "arms": 4, "legs": 4,
        "notes": "Стандартная броня",
    },
    "wounds": 12,
    "fate": 2,
    "talents": ["Обострённые чувства (Зрение)", "Молниеносные рефлексы"],
    "weapons": [{
        "name": "Лазган",
        "stats": "100м, О/3/-, 1d10+3 E, Пробой 0",
        "weight": "2 кг",
        "notes": "Надёжное",
    }],
    "equipment": ["Флак-броня", "Респиратор", "Рюкзак", "Фляга"],
}


SUBFACTION_FALLBACKS = {
    "rogue_trader": {
        "armour": {"head": 4, "body": 4, "arms": 3, "legs": 3,
                   "notes": "Флак-броня с нагрудником"},
        "wounds": 12,
        "fate": 3,
        "talents": [
            "Обострённые чувства (Зрение)",
            "Молниеносные рефлексы",
            "Сопротивление (Страх)",
            "Аура власти",
        ],
        "weapons": [
            {"name": "Лазпистолет",
             "stats": "30м, О/3/-, 1d10+2 E, Пробой 0",
             "weight": "1.5 кг", "notes": "Надёжное"},
            {"name": "Силовой меч",
             "stats": "Ближний бой, 1d10+5 E, Пробой 6",
             "weight": "3 кг", "notes": "Сбалансированное, Силовое поле"},
        ],
        "equipment": ["Плащ-хамелеолин", "Вокс-кастер",
                      "Инфопланшет", "Медальон династии"],
    },
}


# ============================================================
# Репутация
# ============================================================
REPUTATION_FACTIONS = [
    "Империум", "Механикус", "Инквизиция", "Эльдары", "Друкари",
    "Орки", "Тау", "Некроны", "Хаос", "Тираниды",
]

# === PATCH_13_FACTION_FIX: дополнить отсутствующие субфракции ===
def _ensure_subfaction_names():
    global SUBFACTION_NAMES
    defaults = {
        # imperium
        "rogue_trader": "Вольный Торговец",
        "space_marine": "Космодесантник",
        "imperial_guard": "Имперская Гвардия",
        "mechanicus": "Механикус",
        "sororitas": "Сестра Битвы",
        "arbites": "Арбитр",
        # chaos
        "chaos_marine": "Космодесантник Хаоса",
        "dark_mechanicum": "Тёмный Механикум",
        "cultist": "Культист",
        # eldar
        "asuryani": "Асуряни",
        "harlequin": "Арлекин",
        "exodite": "Экзодит",
        # drukhari
        "drukhari": "Друкхари",
        # orks
        "freebooter": "Фрибутер",
        # tau
        "tau": "Тау",
        # necrons
        "necron": "Некрон",
        # genestealers
        "genestealer": "Генокрад",
    }
    for k, v in defaults.items():
        if k not in SUBFACTION_NAMES:
            SUBFACTION_NAMES[k] = v


_ensure_subfaction_names()
try:
    del _ensure_subfaction_names
except NameError:
    pass

