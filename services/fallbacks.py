# PATCH_21
"""services/fallbacks.py — справочники + прокси в data_loader."""
from __future__ import annotations

CHARACTERISTIC_KEYS = ["WS", "BS", "S", "T", "Ag", "Int", "Per", "WP", "Fel"]

CHARACTERISTIC_NAMES = {
    "WS": "Рукопашный бой", "BS": "Стрельба", "S": "Сила",
    "T": "Стойкость", "Ag": "Ловкость", "Int": "Интеллект",
    "Per": "Восприятие", "WP": "Воля", "Fel": "Общение",
}


HOME_WORLDS = {
    "hive": {"name": "Мир-Улей",
             "desc": "Гигантские города-ульи. Толпы, грязь, интриги.",
             "bonus": {"Fel": 5, "Per": 5}, "penalty": {"T": 5},
             "allowed_factions": ["imperium", "chaos", "genestealers"]},
    "feral": {"name": "Дикий мир",
              "desc": "Племена, звери, первобытная ярость.",
              "bonus": {"S": 5, "T": 5}, "penalty": {"Int": 5},
              "allowed_factions": ["imperium", "orks", "chaos"]},
    "forge": {"name": "Мир-Кузница",
              "desc": "Владения Адептус Механикус.",
              "bonus": {"Int": 5, "T": 5}, "penalty": {"Fel": 5},
              "allowed_factions": ["imperium", "chaos"]},
    "void": {"name": "Рождён в Пустоте",
             "desc": "Поколенческий корабль.",
             "bonus": {"WP": 5}, "penalty": {"S": 5},
             "allowed_factions": ["imperium", "chaos", "tau"]},
    "death": {"name": "Мир Смерти",
              "desc": "Всё хочет тебя убить.",
              "bonus": {"S": 5, "Per": 5}, "penalty": {"Fel": 5},
              "allowed_factions": ["imperium", "chaos", "orks", "tyranids"]},
    "feudal": {"name": "Феодальный мир",
               "desc": "Рыцари, замки, долг чести.",
               "bonus": {"WS": 5, "Int": 5}, "penalty": {"Ag": 5},
               "allowed_factions": ["imperium", "chaos"]},
    "frontier": {"name": "Пограничный мир",
                 "desc": "Край Империума.",
                 "bonus": {"BS": 5, "Per": 5}, "penalty": {"Int": 5},
                 "allowed_factions": ["imperium", "chaos", "tau", "orks"]},
    "schola": {"name": "Схола Прогениум",
               "desc": "Дисциплина Имперского культа.",
               "bonus": {"Int": 5, "WP": 5}, "penalty": {"Fel": 5},
               "allowed_factions": ["imperium"]},
    "noble": {"name": "Благородное происхождение",
              "desc": "Титул, состояние, обязанности.",
              "bonus": {"Fel": 5, "Int": 5}, "penalty": {"T": 5},
              "allowed_factions": ["imperium", "chaos"]},
    "ork_camp": {"name": "Стойбище",
                 "desc": "Дым, грохот, драка.",
                 "bonus": {"S": 5, "T": 5}, "penalty": {"Int": 10},
                 "allowed_factions": ["orks"]},
    "tau_sept": {"name": "Септ Тау",
                 "desc": "Кастовое общество.",
                 "bonus": {"BS": 5, "Int": 5}, "penalty": {"WP": 5},
                 "allowed_factions": ["tau"]},
    "tomb_world": {"name": "Мир-Гробница",
                   "desc": "Ты пробудился.",
                   "bonus": {"T": 5, "WP": 5}, "penalty": {"Ag": 5},
                   "allowed_factions": ["necrons"]},
    "cult_hive": {"name": "Культ в Улье",
                  "desc": "Ты рос среди тайных знаков.",
                  "bonus": {"Fel": 5, "WP": 5}, "penalty": {"T": 5},
                  "allowed_factions": ["genestealers", "chaos"]},
}


CAREERS = {
    "rogue_trader": {"name": "Вольный Торговец",
                     "desc": "Торговец, исследователь, дипломат.",
                     "bonus": {"Fel": 5, "Int": 5, "Per": 5},
                     "penalty": {}, "allowed_factions": ["imperium"]},
    "arch_militant": {"name": "Арх-Милитант",
                      "desc": "Мастер клинка и болтера.",
                      "bonus": {"WS": 5, "BS": 5, "S": 5, "T": 5},
                      "penalty": {"Int": 5},
                      "allowed_factions": ["imperium", "chaos"]},
    "explorator": {"name": "Эксплоратор",
                   "desc": "Техножрец.",
                   "bonus": {"Int": 10, "T": 5}, "penalty": {"Fel": 5},
                   "allowed_factions": ["imperium"]},
    "astropath": {"name": "Астропат",
                  "desc": "Телепат.",
                  "bonus": {"WP": 5, "Per": 5, "Int": 5},
                  "penalty": {"T": 5}, "allowed_factions": ["imperium"]},
    "navigator": {"name": "Навигатор",
                  "desc": "Третий глаз видит Варп.",
                  "bonus": {"WP": 5, "Int": 5, "Per": 5},
                  "penalty": {}, "allowed_factions": ["imperium"]},
    "seneschal": {"name": "Сенешаль",
                  "desc": "Управляющий.",
                  "bonus": {"Int": 5, "Fel": 5, "Per": 5},
                  "penalty": {}, "allowed_factions": ["imperium"]},
    "void_master": {"name": "Владыка Пустоты",
                    "desc": "Пилот.",
                    "bonus": {"Ag": 5, "Int": 5, "Per": 5},
                    "penalty": {}, "allowed_factions": ["imperium"]},
    "missionary": {"name": "Миссионер",
                   "desc": "Голос Императора.",
                   "bonus": {"Fel": 5, "WP": 5, "S": 5},
                   "penalty": {}, "allowed_factions": ["imperium"]},
    "chaos_marine": {"name": "Космодесантник Хаоса",
                     "desc": "Проклятый. Одержимый.",
                     "bonus": {"WS": 5, "BS": 5, "S": 5, "T": 5},
                     "penalty": {"Fel": 10}, "allowed_factions": ["chaos"]},
    "kabalite": {"name": "Кабалит",
                 "desc": "Воин-друхкари.",
                 "bonus": {"Ag": 5, "WS": 5, "Per": 5},
                 "penalty": {"Fel": 5}, "allowed_factions": ["drukhari"]},
    "wych": {"name": "Ведьма Арены",
             "desc": "Гладиатор Комморрага.",
             "bonus": {"Ag": 10, "WS": 5}, "penalty": {"Int": 5},
             "allowed_factions": ["drukhari"]},
    "freebooter": {"name": "Фрибутер",
                   "desc": "Орк-наёмник.",
                   "bonus": {"S": 5, "T": 5, "BS": 5},
                   "penalty": {"Int": 5}, "allowed_factions": ["orks"]},
    "fire_warrior": {"name": "Воин Огня",
                     "desc": "Каста Огня.",
                     "bonus": {"BS": 5, "Ag": 5, "WP": 5},
                     "penalty": {"S": 5}, "allowed_factions": ["tau"]},
    "necron_lord": {"name": "Лорд Некрон",
                    "desc": "Властелин династии.",
                    "bonus": {"S": 5, "T": 5, "WP": 5},
                    "penalty": {"Ag": 5}, "allowed_factions": ["necrons"]},
    "magus": {"name": "Магус",
              "desc": "Голос Патриарха.",
              "bonus": {"Fel": 5, "WP": 5, "Int": 5},
              "penalty": {"S": 5}, "allowed_factions": ["genestealers"]},
}


ELDAR_CRAFTWORLDS = {
    "alaitoc": {"name": "Алайток", "desc": "Строгие Пути, много Рейнджеров.",
                "bonus": {"Per": 3}, "penalty": {}},
    "biel_tan": {"name": "Биэль-Тан", "desc": "Самый воинственный.",
                 "bonus": {"BS": 3}, "penalty": {}},
    "iyanden": {"name": "Иянден", "desc": "Опора — призрачные конструкты.",
                "bonus": {"Int": 3}, "penalty": {}},
    "saim_hann": {"name": "Саим-Ханн", "desc": "Дикие, все на байках.",
                  "bonus": {"Ag": 3}, "penalty": {}},
    "ulthwe": {"name": "Ультвэ", "desc": "У Ока Ужаса. Много псайкеров.",
               "bonus": {"WP": 3}, "penalty": {}},
    "altansar": {"name": "Альтансар", "desc": "Был в Оке Ужаса. Выжил.",
                 "bonus": {"WP": 3}, "penalty": {}},
    "lugganath": {"name": "Луганат", "desc": "Связи с Арлекинами.",
                  "bonus": {"Fel": 3}, "penalty": {}},
    "kaelor": {"name": "Кейлор", "desc": "Осторожные прагматики.",
               "bonus": {"Per": 3}, "penalty": {}},
}


ELDAR_PATHS = {
    "path_seer": {"name": "Путь Провидца",
                  "desc": "Усиленный психический потенциал.",
                  "bonus": {"Int": 5}, "penalty": {},
                  "skills": ["Запретные знания (Эльдар)", "Психознание"],
                  "talents": ["Предвидение"],
                  "weapons": [{"name": "Сюрикен-пистолет",
                               "stats": "30м, О/3/-, 1d10+2 R, Пробой 3",
                               "weight": "1.5 кг", "notes": "Надёжное"}],
                  "equipment": ["Камень Души", "Рунный посох", "Мантия Провидца"]},
    "path_bonesinger": {"name": "Путь Костопевца",
                        "desc": "Психический инженер.",
                        "bonus": {"Fel": 5}, "penalty": {},
                        "skills": ["Ремесло (Оружейник)"],
                        "talents": ["Одарённый (Обаяние)"],
                        "weapons": [{"name": "Сюрикен-пистолет",
                                     "stats": "30м, О/3/-, 1d10+2 R, Пробой 3",
                                     "weight": "1.5 кг", "notes": "Надёжное"}],
                        "equipment": ["Камень Души", "Инструменты Костопевца"]},
    "path_warrior": {"name": "Путь Воина",
                     "desc": "Аспектный Воин.",
                     "bonus": {"WS": 5}, "penalty": {},
                     "skills": ["Уклонение"],
                     "talents": ["Амбидекстрия", "Мастер боя"],
                     "weapons": [
                         {"name": "Сюрикен-катапульта",
                          "stats": "60м, О/3/-, 1d10+4 R, Пробой 3",
                          "weight": "2.5 кг", "notes": "Надёжное"},
                         {"name": "Эльдарский силовой меч",
                          "stats": "Ближний бой, 1d10+4 E, Пробой 6",
                          "weight": "2 кг",
                          "notes": "Сбалансированное, Силовое поле"},
                     ],
                     "equipment": ["Камень Души", "Аспектная броня",
                                   "Шлем Аспекта"]},
    "path_corsair": {"name": "Путь Корсара",
                     "desc": "Пират и рейдер.",
                     "bonus": {"Ag": 5}, "penalty": {},
                     "skills": ["Командование", "Навигация (Звёздная)"],
                     "talents": [],
                     "weapons": [{"name": "Сюрикен-пистолет",
                                  "stats": "30м, О/3/-, 1d10+2 R, Пробой 3",
                                  "weight": "1.5 кг", "notes": "Надёжное"}],
                     "equipment": ["Камень Души", "Плащ-хамелеолин",
                                   "Вокс-кастер"]},
    "path_dreamer": {"name": "Путь Сновидений",
                     "desc": "Медитативный Путь.",
                     "bonus": {"WP": 5}, "penalty": {},
                     "skills": ["Запретные знания (Варп)", "Психознание"],
                     "talents": ["Душевный покой"],
                     "weapons": [{"name": "Сюрикен-пистолет",
                                  "stats": "30м, О/3/-, 1d10+2 R, Пробой 3",
                                  "weight": "1.5 кг", "notes": "Надёжное"}],
                     "equipment": ["Камень Души", "Сфера сновидений"]},
    "path_healer": {"name": "Путь Целителя",
                    "desc": "Врач, хирург.",
                    "bonus": {"Int": 3}, "penalty": {},
                    "skills": ["Медицина", "Химия"],
                    "talents": ["Переброс Медицины"],
                    "weapons": [{"name": "Сюрикен-пистолет",
                                 "stats": "30м, О/3/-, 1d10+2 R, Пробой 3",
                                 "weight": "1.5 кг", "notes": "Надёжное"}],
                    "equipment": ["Камень Души", "Эльдарская аптечка"]},
    "path_mariner": {"name": "Путь Морехода",
                     "desc": "Офицер флота.",
                     "bonus": {"Per": 3}, "penalty": {},
                     "skills": ["Командование", "Пилотирование (Космические корабли)"],
                     "talents": ["Переброс пустотных тестов"],
                     "weapons": [{"name": "Сюрикен-пистолет",
                                  "stats": "30м, О/3/-, 1d10+2 R, Пробой 3",
                                  "weight": "1.5 кг", "notes": "Надёжное"}],
                     "equipment": ["Камень Души", "Пустотный скафандр"]},
    "path_scholar": {"name": "Путь Учёного",
                     "desc": "Хранитель знаний.",
                     "bonus": {"Int": 5}, "penalty": {},
                     "skills": ["Схоластические знания (История)", "Логика"],
                     "talents": ["Переброс Знаний"],
                     "weapons": [{"name": "Сюрикен-пистолет",
                                  "stats": "30м, О/3/-, 1d10+2 R, Пробой 3",
                                  "weight": "1.5 кг", "notes": "Надёжное"}],
                     "equipment": ["Камень Души", "Инфопланшет"]},
    "path_service": {"name": "Путь Служения",
                     "desc": "Ремесленник.",
                     "bonus": {"Fel": 3}, "penalty": {},
                     "skills": ["Ремесло (любое)", "Обаяние"],
                     "talents": ["Переброс ремесла"],
                     "weapons": [{"name": "Сюрикен-пистолет",
                                  "stats": "30м, О/3/-, 1d10+2 R, Пробой 3",
                                  "weight": "1.5 кг", "notes": "Надёжное"}],
                     "equipment": ["Камень Души", "Рабочие инструменты"]},
    "path_command": {"name": "Путь Командования",
                     "desc": "Будущий Автарх.",
                     "bonus": {"Fel": 3}, "penalty": {},
                     "skills": ["Командование", "Проницательность"],
                     "talents": ["Переброс Взаимодействия"],
                     "weapons": [{"name": "Сюрикен-пистолет",
                                  "stats": "30м, О/3/-, 1d10+2 R, Пробой 3",
                                  "weight": "1.5 кг", "notes": "Надёжное"}],
                     "equipment": ["Камень Души", "Аспектная броня"]},
}


FACTIONS = {
    "imperium": {"name": "Империум Человечества",
                 "subfactions": ["rogue_trader", "space_marine",
                                 "imperial_guard", "mechanicus",
                                 "sororitas", "arbites"]},
    "chaos": {"name": "Силы Хаоса",
              "subfactions": ["chaos_marine", "dark_mechanicum", "cultist"]},
    "eldar": {"name": "Эльдары",
              "subfactions": ["asuryani", "harlequin", "exodite"]},
    "drukhari": {"name": "Друхкари", "subfactions": ["drukhari"]},
    "orks": {"name": "Орки", "subfactions": ["freebooter"]},
    "tau": {"name": "Тау", "subfactions": ["tau"]},
    "necrons": {"name": "Некроны", "subfactions": ["necron"]},
    "genestealers": {"name": "Генокрады", "subfactions": ["genestealer"]},
}


SUBFACTION_NAMES = {
    "rogue_trader": "Вольный Торговец", "space_marine": "Космодесантник",
    "imperial_guard": "Имперская Гвардия", "mechanicus": "Механикус",
    "sororitas": "Сестра Битвы", "arbites": "Арбитр",
    "chaos_marine": "Космодесантник Хаоса", "dark_mechanicum": "Тёмный Механикум",
    "cultist": "Культист",
    "asuryani": "Асуряни", "harlequin": "Арлекин", "exodite": "Экзодит",
    "drukhari": "Друхкари", "freebooter": "Фрибутер",
    "tau": "Тау", "necron": "Некрон", "genestealer": "Генокрад",
}


DEFAULT_ARCHETYPE = {
    "imperium": "rogue_trader", "chaos": "chaos_marine",
    "eldar": "path_warrior", "drukhari": "kabalite",
    "orks": "freebooter", "tau": "fire_warrior",
    "necrons": "necron_lord", "genestealers": "magus",
}


REPUTATION_FACTIONS = [
    "Империум", "Механикус", "Инквизиция", "Эльдары", "Друхкари",
    "Орки", "Тау", "Некроны", "Хаос", "Тираниды",
]


ULTIMATE_FALLBACK = {
    "armour": {"head": 4, "body": 4, "arms": 4, "legs": 4,
               "notes": "Стандартная броня"},
    "wounds": 12, "fate": 2,
    "talents": ["Обострённые чувства (Зрение)", "Молниеносные рефлексы"],
    "weapons": [{"name": "Лазган",
                 "stats": "100м, О/3/-, 1d10+3 E, Пробой 0",
                 "weight": "2 кг", "notes": "Надёжное"}],
    "equipment": ["Флак-броня", "Респиратор", "Рюкзак", "Фляга"],
}


ELDAR_FALLBACK = {
    "armour": {"head": 6, "body": 6, "arms": 6, "legs": 6,
               "notes": "Эльдарский сетчатый бодисьют (Все AP 6)"},
    "wounds": 11, "fate": 2,
    "talents": ["Обострённые чувства (Зрение)", "Обострённые чувства (Слух)",
                "Тёмное зрение", "Падение с высоты", "Спринт",
                "Сверхъестественная ловкость (x2)"],
    "weapons": [{"name": "Сюрикен-пистолет",
                 "stats": "30м, О/3/-, 1d10+2 R, Пробой 3",
                 "weight": "1.5 кг", "notes": "Надёжное"}],
    "equipment": ["Камень Души", "Плащ-хамелеолин"],
    "skills": ["Общие знания (Эльдар)", "Разговорный язык (Эльдар)", "Обаяние"],
}


SUBFACTION_FALLBACKS = {
    "rogue_trader": {
        "armour": {"head": 4, "body": 4, "arms": 3, "legs": 3,
                   "notes": "Флак-броня с нагрудником"},
        "wounds": 12, "fate": 3,
        "talents": ["Обострённые чувства (Зрение)", "Молниеносные рефлексы",
                    "Сопротивление (Страх)", "Аура власти"],
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


def _loader_hw(faction_id):
    try:
        from services.data_loader import list_home_world_ids
        return list_home_world_ids(faction_id) or []
    except Exception as e:
        print("[fallbacks] loader hw: " + str(e))
        return []


def _loader_careers(faction_id):
    try:
        from services.data_loader import list_career_ids
        return list_career_ids(faction_id) or []
    except Exception as e:
        print("[fallbacks] loader careers: " + str(e))
        return []


def home_worlds_for(faction_id: str) -> list:
    ids = _loader_hw(faction_id)
    if ids:
        return ids
    if faction_id == "eldar":
        return list(ELDAR_CRAFTWORLDS.keys())
    out = []
    for key, data in HOME_WORLDS.items():
        allowed = data.get("allowed_factions") or []
        if not allowed or faction_id in allowed:
            out.append(key)
    return out


def careers_for(faction_id: str) -> list:
    ids = _loader_careers(faction_id)
    if ids:
        return ids
    if faction_id == "eldar":
        return list(ELDAR_PATHS.keys())
    out = []
    for key, data in CAREERS.items():
        allowed = data.get("allowed_factions") or []
        if not allowed or faction_id in allowed:
            out.append(key)
    return out


def home_world_display_name(faction_id: str, key: str) -> str:
    if faction_id == "eldar" and key in ELDAR_CRAFTWORLDS:
        return ELDAR_CRAFTWORLDS[key]["name"]
    try:
        from services.data_loader import get_home_world
        d = get_home_world(faction_id, key)
        if d and d.get("name"):
            return d["name"]
    except Exception:
        pass
    if key in HOME_WORLDS:
        return HOME_WORLDS[key].get("name", key)
    return key


def career_display_name(faction_id: str, key: str) -> str:
    if faction_id == "eldar" and key in ELDAR_PATHS:
        return ELDAR_PATHS[key]["name"]
    try:
        from services.data_loader import get_career
        d = get_career(faction_id, key)
        if d and d.get("name"):
            return d["name"]
    except Exception:
        pass
    if key in CAREERS:
        return CAREERS[key].get("name", key)
    return key


def home_world_data(faction_id: str, key: str) -> dict:
    if faction_id == "eldar" and key in ELDAR_CRAFTWORLDS:
        d = dict(ELDAR_CRAFTWORLDS[key])
        d["id"] = key
        return d
    if key in HOME_WORLDS:
        d = dict(HOME_WORLDS[key])
        d["id"] = key
        return d
    try:
        from services.data_loader import get_home_world
        d = get_home_world(faction_id, key)
        if d:
            d["id"] = key
            return d
    except Exception:
        pass
    return {}


def career_data(faction_id: str, key: str) -> dict:
    if faction_id == "eldar" and key in ELDAR_PATHS:
        d = dict(ELDAR_PATHS[key])
        d["id"] = key
        return d
    if key in CAREERS:
        d = dict(CAREERS[key])
        d["id"] = key
        return d
    try:
        from services.data_loader import get_career
        d = get_career(faction_id, key)
        if d:
            d["id"] = key
            return d
    except Exception:
        pass
    return {}


def apply_creation_bonuses(stats: dict, home_key: str, career_key: str) -> dict:
    result = dict(stats)
    for key in (home_key, career_key):
        if not key:
            continue
        for source in (HOME_WORLDS, CAREERS, ELDAR_CRAFTWORLDS, ELDAR_PATHS):
            if key in source:
                data = source[key]
                for k, v in (data.get("bonus") or {}).items():
                    result[k] = result.get(k, 0) + v
                for k, v in (data.get("penalty") or {}).items():
                    result[k] = result.get(k, 0) - v
                break
    return result
