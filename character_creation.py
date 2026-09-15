# character_creation.py
# Логика создания персонажа: генерация характеристик, сборка листа через LLM+RAG,
# сохранение/загрузка JSON.
# Использует модель GigaChat-2-Pro.
#
# ВАЖНО:
# - armour, wounds, fate_points, talents, weapons, equipment ВСЕГДА берутся из fallback.
# - GigaChat генерирует только skills и background (он тут справляется лучше).
# - Есть починка JSON и ретрай при ошибке парсинга.

import os
import json
import random
import re
from datetime import datetime

import streamlit as st

from gigachat import GigaChat
from gigachat.models import Chat, Messages, MessagesRole


# ============================================================
# НАСТРОЙКИ
# ============================================================
try:
    API_KEY = st.secrets["GIGACHAT_API_KEY"]
except Exception:
    API_KEY = "MDFhMDk2NGMtZGQ0Yi03NGJiLTkzNWEtODgzMWEwNjZjZDYzOjBkNDViZDZmLTYxYzQtNGYyNC1hYzFlLTczZGY5OWI5MDZiMw=="

MODEL_NAME = "GigaChat-2-Pro"

CHARACTERS_DIR = "characters"

CHARACTERISTICS = ["WS", "BS", "S", "T", "Ag", "Int", "Per", "WP", "Fel"]

CHARACTERISTIC_NAMES_RU = {
    "WS": "Ближний бой (WS)",
    "BS": "Дальний бой (BS)",
    "S":  "Сила (S)",
    "T":  "Выносливость (T)",
    "Ag": "Ловкость (Ag)",
    "Int":"Интеллект (Int)",
    "Per":"Восприятие (Per)",
    "WP": "Сила воли (WP)",
    "Fel":"Обаяние (Fel)",
}


# ============================================================
# ГЕНЕРАЦИЯ ХАРАКТЕРИСТИК
# ============================================================
def roll_2d10():
    return random.randint(1, 10) + random.randint(1, 10)


def generate_by_dice(dice_modifier: int) -> dict:
    return {ch: roll_2d10() + dice_modifier for ch in CHARACTERISTICS}


def generate_by_pointbuy(start: int = 25, total_points: int = 100) -> dict:
    return {ch: start for ch in CHARACTERISTICS}


def reroll_one(chars: dict, characteristic: str, dice_modifier: int) -> dict:
    chars = dict(chars)
    chars[characteristic] = roll_2d10() + dice_modifier
    return chars


def char_bonus(value: int) -> int:
    return value // 10


# ============================================================
# СОХРАНЕНИЕ / ЗАГРУЗКА
# ============================================================
def ensure_characters_dir():
    os.makedirs(CHARACTERS_DIR, exist_ok=True)


def save_character(character: dict):
    ensure_characters_dir()
    safe_name = "".join(c for c in character["name"] if c.isalnum() or c in "-_ ").strip()
    if not safe_name:
        safe_name = "unnamed"
    path = os.path.join(CHARACTERS_DIR, safe_name + ".json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(character, f, ensure_ascii=False, indent=2)
    return path


def list_characters() -> list:
    ensure_characters_dir()
    items = []
    for fname in sorted(os.listdir(CHARACTERS_DIR)):
        if not fname.endswith(".json"):
            continue
        path = os.path.join(CHARACTERS_DIR, fname)
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            items.append({
                "path": path,
                "name": data.get("name", fname),
                "faction": data.get("faction", "?"),
                "subfaction": data.get("subfaction", ""),
                "archetype": data.get("archetype", ""),
            })
        except Exception:
            continue
    return items


def load_character(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def delete_character(path: str):
    try:
        os.remove(path)
    except Exception:
        pass


# ============================================================
# ПСАЙКЕРЫ
# ============================================================
PSYKER_ARCHETYPES = {
    "astropath":   2,
    "sorcerer":    2,
    "seer":        2,
    "dreamer":     2,
    "worldsinger": 2,
    "shadowseer":  2,
    "weirdboy":    1,
    "navigator":   1,
}

PSYKER_PSYCHIC_POWERS = {
    "astropath":   ["Мысленная связь", "Астро-телепатия", "Внушение"],
    "sorcerer":    ["Разрушитель", "Ободрение", "Усиление"],
    "seer":        ["Фортуна", "Боевая Судьба", "Погибель"],
    "dreamer":     ["Режущий Свет", "Щит Духа", "Сканирование Души"],
    "worldsinger": ["Щит Духа", "Ободрение", "Сокрытие"],
    "shadowseer":  ["Сокрытие", "Палач", "Усиление"],
    "weirdboy":    ["Da Jump", "Fists of Gork", "Warpath"],
    "navigator":   ["Распахнутый взор", "Взгляд в бездну"],
}


# ============================================================
# FALLBACK-ДАННЫЕ ПО СУБФРАКЦИЯМ
# ============================================================
FALLBACK_BY_SUBFACTION = {

    "rogue_trader": {
        "armour": {"head": 4, "body": 4, "arms": 3, "legs": 3, "notes": "Флак-броня с нагрудником"},
        "wounds": 12, "fate": 3,
        "talents": ["Обострённые чувства (Зрение)", "Молниеносные рефлексы", "Сопротивление (Страх)", "Аура власти"],
        "weapons": [
            {"name": "Лазпистолет", "stats": "30м, О/3/-, 1d10+2 E, Пробой 0", "weight": "1.5 кг", "notes": "Надёжное"},
            {"name": "Силовой меч", "stats": "Ближний бой, 1d10+5 E, Пробой 6", "weight": "3 кг", "notes": "Сбалансированное, Силовое поле"},
        ],
        "equipment": ["Плащ-хамелеолин", "Вокс-кастер", "Инфопланшет", "Медальон династии"],
    },

    "space_marine": {
        "armour": {"head": 8, "body": 8, "arms": 8, "legs": 8, "notes": "Силовая броня Астартес, Марк VII"},
        "wounds": 22, "fate": 3,
        "talents": ["Обострённые чувства (Зрение, Слух)", "Амбидекстрия", "Сопротивление (Страх)", "Сопротивление (Психика)", "Стальные нервы", "Быстрое выхватывание"],
        "weapons": [
            {"name": "Болтер Астартес", "stats": "100м, О/3/-, 1d10+9 X, Пробой 5", "weight": "7 кг", "notes": "Разрывающее"},
            {"name": "Боевой нож Астартес", "stats": "Ближний бой, 1d10+2 R, Пробой 0", "weight": "1 кг", "notes": "—"},
        ],
        "equipment": ["Силовая броня Марк VII", "4 магазина к болтеру", "3 фраг-гранаты", "3 крак-гранаты", "Ремонтная паста"],
    },

    "imperial_guard": {
        "armour": {"head": 2, "body": 4, "arms": 2, "legs": 2, "notes": "Флак-броня Имперской Гвардии"},
        "wounds": 13, "fate": 2,
        "talents": ["Молниеносные рефлексы", "Сопротивление (Страх)", "Крепкое телосложение"],
        "weapons": [
            {"name": "Лазган", "stats": "100м, О/3/-, 1d10+3 E, Пробой 0", "weight": "2 кг", "notes": "Надёжное"},
            {"name": "Боевой нож", "stats": "Ближний бой, 1d10+2 R, Пробой 0", "weight": "1 кг", "notes": "—"},
        ],
        "equipment": ["Флак-броня", "Шлем с вокс-связью", "3 осколочных гранаты", "Фляга"],
    },

    "mechanicus": {
        "armour": {"head": 5, "body": 6, "arms": 5, "legs": 5, "notes": "Карапасная броня Механикус с имплантами"},
        "wounds": 13, "fate": 2,
        "talents": ["Технический удар", "Ремесленник", "Полное воспоминание", "Железная воля"],
        "weapons": [
            {"name": "Силовая секира", "stats": "Ближний бой, 1d10+7 E, Пробой 8", "weight": "6 кг", "notes": "Силовое поле, Медленное"},
            {"name": "Лазпистолет", "stats": "30м, О/-/-, 1d10+2 E, Пробой 0", "weight": "1 кг", "notes": "Надёжное"},
        ],
        "equipment": ["Роба Механикус", "Механодендрит (утилитарный)", "Набор инструментов", "Дата-планшет", "Фиал Священного Машинного Масла"],
    },

    "sororitas": {
        "armour": {"head": 8, "body": 8, "arms": 8, "legs": 8, "notes": "Силовая броня Сороритас"},
        "wounds": 14, "fate": 3,
        "talents": ["Чистая вера", "Литания Ненависти", "Сопротивление (Страх)", "Сопротивление (Психика)"],
        "weapons": [
            {"name": "Болтер Годвин-Де'аз", "stats": "100м, О/3/-, 1d10+9 X, Пробой 5", "weight": "7 кг", "notes": "Разрывающее"},
            {"name": "Цепной меч", "stats": "Ближний бой, 1d10+3 R, Пробой 3", "weight": "6 кг", "notes": "Цепное, Разрывающее"},
        ],
        "equipment": ["Силовая броня Сороритас", "Розарий", "3 фраг-гранаты", "Молитвенник"],
    },

    "arbites": {
        "armour": {"head": 6, "body": 7, "arms": 6, "legs": 6, "notes": "Карапасная броня Адептус Арбитрес"},
        "wounds": 13, "fate": 2,
        "talents": ["Сопротивление (Страх)", "Железная воля", "Точный выстрел", "Непреклонная воля"],
        "weapons": [
            {"name": "Боевой дробовик", "stats": "30м, О/3/-, 1d10+4 I, Пробой 0", "weight": "6 кг", "notes": "Надёжное, Разброс"},
            {"name": "Силовой молот", "stats": "Ближний бой, 1d10+5 E, Пробой 6", "weight": "5 кг", "notes": "Силовое поле, Шоковое (2)"},
        ],
        "equipment": ["Карапасная броня", "Щит Адептус Арбитрес", "Наручники", "Печать Арбитрес"],
    },

    "chaos_marine": {
        "armour": {"head": 8, "body": 9, "arms": 8, "legs": 8, "notes": "Силовая броня Космодесанта Хаоса, осквернённая"},
        "wounds": 22, "fate": 3,
        "talents": ["Обострённые чувства (Зрение, Слух)", "Амбидекстрия", "Сопротивление (Страх)", "Мастер боя", "Стальные нервы", "Быстрое выхватывание"],
        "weapons": [
            {"name": "Болтер Хаоса", "stats": "100м, О/3/-, 1d10+9 X, Пробой 5", "weight": "7 кг", "notes": "Разрывающее, Осквернённое"},
            {"name": "Цепной топор", "stats": "Ближний бой, 1d10+5 R, Пробой 3", "weight": "8 кг", "notes": "Цепное, Разрывающее"},
        ],
        "equipment": ["Силовая броня Хаоса", "4 магазина к болтеру", "Трофейный череп", "Метка Хаоса"],
    },

    "dark_mechanicum": {
        "armour": {"head": 6, "body": 7, "arms": 6, "legs": 6, "notes": "Тёмная броня Тёмного Механикума"},
        "wounds": 13, "fate": 2,
        "talents": ["Технический удар", "Ремесленник", "Запретные знания (Варп)", "Железная воля"],
        "weapons": [
            {"name": "Демонический механодендрит", "stats": "Ближний бой, 1d10+5 E, Пробой 5", "weight": "3 кг", "notes": "Силовое поле"},
            {"name": "Плазменный пистолет", "stats": "30м, О/-/-, 2d10+6 E, Пробой 5", "weight": "4 кг", "notes": "Опасное (Overheats)"},
        ],
        "equipment": ["Роба Тёмного Механикума", "Механодендрит (оружие)", "Набор запретных инструментов", "Дата-планшет"],
    },

    "cultist": {
        "armour": {"head": 3, "body": 4, "arms": 3, "legs": 3, "notes": "Осквернённая флак-броня"},
        "wounds": 11, "fate": 2,
        "talents": ["Сопротивление (Страх)", "Фанатик", "Мастер боя", "Железная воля"],
        "weapons": [
            {"name": "Автопистолет", "stats": "30м, О/3/-, 1d10+2 I, Пробой 0", "weight": "1.5 кг", "notes": "—"},
            {"name": "Жертвенный кинжал", "stats": "Ближний бой, 1d10+2 R, Пробой 0", "weight": "1 кг", "notes": "—"},
        ],
        "equipment": ["Осквернённая броня", "Символ бога Хаоса", "Свечи для ритуала", "Книга запретных молитв"],
    },

    "asuryani": {
        "armour": {"head": 6, "body": 6, "arms": 6, "legs": 6, "notes": "Сетчатый бодисьют эльдар"},
        "wounds": 14, "fate": 2,
        "talents": ["Обострённые чувства (Зрение, Слух)", "Тёмное зрение", "Спринт", "Падение с высоты", "Сверхъестественная ловкость (x2)"],
        "weapons": [
            {"name": "Сюрикен-катапульта", "stats": "60м, О/3/-, 1d10+4 R, Пробой 3", "weight": "2.5 кг", "notes": "Надёжное"},
            {"name": "Эльдарский силовой меч", "stats": "Ближний бой, 1d10+4 E, Пробой 6", "weight": "2 кг", "notes": "Сбалансированное, Силовое поле"},
        ],
        "equipment": ["Сетчатый бодисьют эльдар", "Камень Души", "Плащ-хамелеолин", "Шлем с психо-усилителями"],
    },

    "drukhari": {
        "armour": {"head": 5, "body": 5, "arms": 5, "legs": 5, "notes": "Броня Каббалита"},
        "wounds": 13, "fate": 2,
        "talents": ["Обострённые чувства (Зрение, Слух)", "Тёмное зрение", "Спринт", "Падение с высоты", "Сверхъестественная ловкость (x2)", "Сила через Боль"],
        "weapons": [
            {"name": "Сюрикен-винтовка", "stats": "80м, О/3/5, 1d10+2 R, Пробой 3", "weight": "2.5 кг", "notes": "Токсичное"},
            {"name": "Моно-меч", "stats": "Ближний бой, 1d10+5 R, Пробой 4", "weight": "1 кг", "notes": "Сбалансированное"},
        ],
        "equipment": ["Броня Каббалита", "Микро-бусина", "Транслокатор", "2 дозы яда"],
    },

    "harlequin": {
        "armour": {"head": 6, "body": 6, "arms": 6, "legs": 6, "notes": "Голо-костюм Арлекина"},
        "wounds": 13, "fate": 3,
        "talents": ["Обострённые чувства (Зрение, Слух)", "Тёмное зрение", "Спринт", "Падение с высоты", "Сверхъестественная ловкость (x2)", "Молниеносные рефлексы", "Трудная цель"],
        "weapons": [
            {"name": "Поцелуй Арлекина", "stats": "Ближний бой, 2d10+8 R, Пробой 8", "weight": "1.5 кг", "notes": "Силовое поле, Рвущее"},
            {"name": "Сюрикен-пистолет", "stats": "30м, О/3/-, 1d10+2 R, Пробой 3", "weight": "1.5 кг", "notes": "Надёжное"},
        ],
        "equipment": ["Голо-костюм", "Флип-пояс", "Маска Арлекина", "Маска Смеющегося Бога"],
    },

    "exodite": {
        "armour": {"head": 5, "body": 6, "arms": 5, "legs": 5, "notes": "Сетчатая и костяная броня"},
        "wounds": 14, "fate": 2,
        "talents": ["Обострённые чувства (Зрение, Слух)", "Тёмное зрение", "Спринт", "Сверхъестественная ловкость (x2)", "Мастер-наездник"],
        "weapons": [
            {"name": "Длинная винтовка Рейнджера", "stats": "200м, О/-/-, 1d10+3 E, Пробой 2", "weight": "2 кг", "notes": "Точное, Индивидуализированное"},
            {"name": "Силовой клинок", "stats": "Ближний бой, 1d10+5 E, Пробой 5", "weight": "3 кг", "notes": "Силовое поле"},
        ],
        "equipment": ["Сетчатая броня", "Костяная броня", "Плащ-хамелеолин", "Кристаллы Мирового Духа"],
    },

    "freebooter": {
        "armour": {"head": 5, "body": 6, "arms": 4, "legs": 4, "notes": "'Эви Армор"},
        "wounds": 17, "fate": 2,
        "talents": ["Крепкое телосложение (x2)", "Неестественная выносливость (x2)", "Железная челюсть", "Сопротивление (Яды)", "Внимание"],
        "weapons": [
            {"name": "Слагга", "stats": "20м, О/-/-, 1d10+4 I, Пробой 1", "weight": "3 кг", "notes": "Неточное"},
            {"name": "Чоппа", "stats": "Ближний бой, 1d10+3 R, Пробой 2", "weight": "4 кг", "notes": "Несбалансированное"},
        ],
        "equipment": ["'Эви Армор", "3 стикк-бомбы", "Сквиг-гончая", "Фляга с грибным пивом"],
    },

    "tau": {
        "armour": {"head": 4, "body": 4, "arms": 4, "legs": 4, "notes": "Броня Касты Огня"},
        "wounds": 12, "fate": 2,
        "talents": ["Обострённые чувства (Зрение)", "Молниеносные рефлексы", "Трудная цель", "Мастер боя", "Точный выстрел"],
        "weapons": [
            {"name": "Импульсная винтовка", "stats": "150м, О/2/4, 2d10+3 E, Пробой 4", "weight": "8 кг", "notes": "Гироскопически стабилизированное"},
            {"name": "Импульсный пистолет", "stats": "30м, О/-/-, 2d10+2 E, Пробой 4", "weight": "2 кг", "notes": "—"},
        ],
        "equipment": ["Броня Касты Огня", "Дрон-щит", "Маркерный маяк", "Фотонная граната"],
    },

    "necron": {
        "armour": {"head": 9, "body": 9, "arms": 9, "legs": 9, "notes": "Некродермис с усилением"},
        "wounds": 40, "fate": 3,
        "talents": ["Тёмное зрение", "Машина", "Регенерация 10", "Страх 4", "Неестественная Сила (x2)", "Неестественная Выносливость (x2)"],
        "weapons": [
            {"name": "Коса Войны", "stats": "Ближний бой, 2d10+17 E, Пробой 9", "weight": "5 кг", "notes": "Силовое поле, Фазовое оружие"},
            {"name": "Посох Света", "stats": "Ближний бой, 1d10+5 E, Пробой 6; дальний: 30м, 1d10+4 E", "weight": "2 кг", "notes": "Силовое поле"},
        ],
        "equipment": ["Некродермис (AP 9)", "Филактерия", "Фазовый Сдвигатель", "Вуаль Тьмы"],
    },

    "genestealer": {
        "armour": {"head": 6, "body": 6, "arms": 6, "legs": 6, "notes": "Хитиновый панцирь"},
        "wounds": 15, "fate": 2,
        "talents": ["Тёмное зрение", "Иммунитет к Страху", "Иммунитет к Пыткам", "Иммунитет к Психическим Силам", "Неестественная Сила (x2)", "Неестественная Выносливость (x2)", "Скрытность", "Бесшумное передвижение"],
        "weapons": [
            {"name": "Косы-когти", "stats": "Ближний бой, 1d10+4 R, Пробой 3", "weight": "—", "notes": "Рвущее, Сбалансированное"},
            {"name": "Костяной меч", "stats": "Ближний бой, 1d10+5 E, Пробой 6", "weight": "1 кг", "notes": "Силовое поле, Психическое"},
        ],
        "equipment": ["Хитиновый панцирь (AP 6)", "Кислотная кровь", "Симбиотические рипперы"],
    },
}

DEFAULT_FALLBACK = "rogue_trader"

ULTIMATE_FALLBACK = {
    "armour": {"head": 4, "body": 4, "arms": 4, "legs": 4, "notes": "Стандартная броня"},
    "wounds": 12, "fate": 2,
    "talents": ["Обострённые чувства (Зрение)", "Молниеносные рефлексы"],
    "weapons": [
        {"name": "Лазган", "stats": "100м, О/3/-, 1d10+3 E, Пробой 0", "weight": "2 кг", "notes": "Надёжное"},
    ],
    "equipment": ["Флак-броня", "Респиратор", "Рюкзак", "Фляга"],
}


# ============================================================
# BACKGROUND: шаблоны по расам (если GigaChat вернёт чушь)
# ============================================================
BACKGROUND_BY_FACTION = {
    "eldar": (
        "Ты родился на Крафтворлде, среди костей-призраков и вечного сияния Бесконечного Circuit. "
        "Твой народ угасает, но ты идёшь по Пути, чтобы обуздать свои страсти и не дать Слаанеш поглотить твою душу. "
        "Теперь твой путь лежит через холодную тьму галактики, где каждый встречный — либо враг, либо инструмент."
    ),
    "imperium": (
        "Ты родился в Империуме Человечества — колоссальной империи, которой правит Император с Золотого Трона. "
        "Ты служишь человечеству, зная, что вокруг только ксеносы, еретики и демоны. "
        "Каждый твой шаг — во имя Императора, и каждый враг — угроза для всего, что ты защищаешь."
    ),
    "chaos": (
        "Ты отверг Императора и принял Тёмные Боги. Варп шепчет тебе, обещая силу и бессмертие. "
        "Твои враги — весь Империум, а твои союзники — лишь до тех пор, пока ты сильнее их. "
        "Ты идёшь по пути проклятых, и обратной дороги нет."
    ),
    "orks": (
        "Ты — орк. Ты родился из споры в грязи, вырос в драках, и вся твоя жизнь — это война. "
        "Ты покинул свой клан, чтобы искать новых врагов, новые зубы и новую славу. "
        "ДАККА! Больше дакки! Вот что делает тебя счастливым."
    ),
    "tau": (
        "Ты — тау, дитя Империи Тау, служащее Высшему Благу. Ты веришь, что все разумные расы "
        "могут объединиться ради общего процветания. Ты обучен, дисциплинирован и предан. "
        "Твой путь лежит в дикие земли, где другие расы ещё не познали свет Tau'va."
    ),
    "necrons": (
        "Ты — древний некрон, пробудившийся от шестидесятимиллионнолетнего сна. Твоя плоть давно стала металлом, "
        "а душа — лишь эхо в некродермисе. Твоя династия требует восстановления былой славы. "
        "Галактика забыла, кто здесь истинный хозяин. Ты напомнишь ей."
    ),
    "tyranids": (
        "Ты — дитя Сверхразума, часть бесконечного роя. Ты был послан вперёд, чтобы подготовить путь "
        "для флотов-ульев. Твоя цель — поглощать, размножаться и расширяться. "
        "Вселенная — это пища. Ты — её пожиратель."
    ),
}


# ============================================================
# МАППИНГ СУБФРАКЦИЯ → ФРАКЦИЯ (для background и фильтров)
# ============================================================
SUBFACTION_TO_FACTION_KEY = {
    "rogue_trader": "imperium", "space_marine": "imperium", "imperial_guard": "imperium",
    "mechanicus": "imperium", "sororitas": "imperium", "arbites": "imperium",
    "chaos_marine": "chaos", "dark_mechanicum": "chaos", "cultist": "chaos",
    "asuryani": "eldar", "drukhari": "eldar", "harlequin": "eldar", "exodite": "eldar",
    "freebooter": "orks",
    "tau": "tau",
    "necron": "necrons",
    "genestealer": "tyranids",
}

CROSS_FACTION_WORDS = {
    "eldar":    ["космодесантник", "космический десантник", "астартес", "инквизитор", "механикус", "сороритас", "арбитр", "орк ", " тау", "некрон", "тиранид", "хаосит", "империум"],
    "imperium": ["эльдар", "аэльдари", "асуриани", "друкхари", "орк ", " тау", "некрон", "тиранид", "хаосит", "кхорн", "тзинч", "нургл"],
    "chaos":    ["эльдар", "асуриани", "орк ", " тау", "некрон", "тиранид", "астартес лояльн", "император-защитник"],
    "orks":     ["эльдар", "асуриани", "космодесантник", "астартес", "империум", "тау", "некрон", "тиранид"],
    "tau":      ["эльдар", "космодесантник", "астартес", "империум", "орк ", "некрон", "тиранид", "хаосит"],
    "necrons":  ["эльдар", "космодесантник", "астартес", "империум", "орк ", "тау", "тиранид", "хаосит"],
    "tyranids": ["эльдар", "космодесантник", "астартес", "империум", "орк ", "тау", "некрон", "хаосит"],
}


# ============================================================
# ПОЧИНКА JSON
# ============================================================
def _repair_json_text(text: str) -> str:
    """
    Пытается починить частые ошибки GigaChat в JSON:
    - Лишние кавычки перед `{` или `[` внутри массивов
    - Лишние кавычки после `}` или `]`
    - Незакрытые строки
    """
    if not text:
        return text

    # Убираем markdown-обёртки
    if "```json" in text:
        text = text.split("```json", 1)[1].split("```", 1)[0]
    elif "```" in text:
        text = text.split("```", 1)[1].split("```", 1)[0]

    text = text.strip()

    # 1. Убираем лишние кавычки перед { или [ в начале элементов массива
    text = re.sub(r'"(\s*\{)', r'\1', text)
    text = re.sub(r'"(\s*\[)', r'\1', text)

    # 2. Убираем лишние кавычки после } или ] перед запятой
    text = re.sub(r'(\}\s*)"(\s*,)', r'\1\2', text)
    text = re.sub(r'(\]\s*)"(\s*,)', r'\1\2', text)

    # 3. Иногда GigaChat пишет `{name": ...}` без открывающей кавычки у ключа
    text = re.sub(r'([{,]\s*)(\w+)"(\s*:)', r'\1"\2"\3', text)

    # 4. Убираем trailing запятые перед ] или }
    text = re.sub(r',(\s*[\]}])', r'\1', text)

    return text


def _try_parse_json(text: str) -> dict:
    """Пытается распарсить JSON, при неудаче — починить и попробовать ещё раз."""
    # Попытка 1: как есть
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass

    # Попытка 2: с починкой
    repaired = _repair_json_text(text)
    try:
        return json.loads(repaired)
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON не распарсился даже после починки: {e}\n\nСырой ответ:\n{text}")


# ============================================================
# ПРИМЕНЕНИЕ FALLBACK
# ============================================================
def apply_fallbacks(sheet: dict, subfaction_id: str, archetype_id: str) -> dict:
    """
    Жёсткая валидация и подстановка каноничных данных.
    ВСЁ, кроме skills и background, берётся из fallback.
    """
    fallback = FALLBACK_BY_SUBFACTION.get(subfaction_id)
    if not fallback:
        fallback = FALLBACK_BY_SUBFACTION.get(DEFAULT_FALLBACK, ULTIMATE_FALLBACK)

    # ---- ВСЕГДА из fallback ----
    sheet["armour"] = dict(fallback["armour"])
    wounds_max = fallback.get("wounds", 12)
    sheet["wounds"] = {"current": wounds_max, "max": wounds_max}
    fate_max = fallback.get("fate", 2)
    sheet["fate_points"] = {"current": fate_max, "max": fate_max}
    sheet["talents"] = list(fallback["talents"])
    sheet["weapons"] = [dict(w) for w in fallback["weapons"]]
    sheet["equipment"] = list(fallback["equipment"])

    # ---- Навыки ----
    if not sheet.get("skills"):
        chars = sheet.get("characteristics", {})
        sheet["skills"] = [
            {"name": "Внимание",     "characteristic": "Per", "value": chars.get("Per", 30) + 5},
            {"name": "Скрытность",   "characteristic": "Ag",  "value": chars.get("Ag", 30) + 5},
            {"name": "Акробатика",   "characteristic": "Ag",  "value": chars.get("Ag", 30)},
            {"name": "Выживание",    "characteristic": "Int", "value": chars.get("Int", 30)},
            {"name": "Дальний бой",  "characteristic": "BS",  "value": chars.get("BS", 30)},
            {"name": "Общие знания", "characteristic": "Int", "value": chars.get("Int", 30)},
        ]

    # Исправление привязки навыков
    skill_to_char = {
        "скрытность": "Ag", "акробатика": "Ag",
        "внимание": "Per", "бдительность": "Per", "восприятие": "Per", "психознание": "Per",
        "выживание": "Int", "слежка": "Int", "выслеживание": "Int", "навигация": "Int",
        "общие знания": "Int", "запретные знания": "Int", "логика": "Int",
        "медицина": "Int", "техноиспользование": "Int",
        "дальний бой": "BS", "стрельба": "BS",
        "ближний бой": "WS", "рукопашный": "WS",
        "обман": "Fel", "убеждение": "Fel", "командование": "Fel",
        "запугивание": "S", "атлетика": "S", "лазание": "S", "плавание": "S",
        "сила воли": "WP", "сопротивление": "WP",
    }

    chars = sheet.get("characteristics", {})
    for s in sheet.get("skills", []):
        if not isinstance(s, dict):
            continue
        name_lower = s.get("name", "").lower()
        correct_char = None
        for key, ch in skill_to_char.items():
            if key in name_lower:
                correct_char = ch
                break
        if correct_char:
            s["characteristic"] = correct_char
            base = chars.get(correct_char, 30)
            val = s.get("value", 0)
            if not isinstance(val, int) or val < base or val > base + 25:
                s["value"] = base + 5

    # ---- Пси-рейтинг ----
    if archetype_id in PSYKER_ARCHETYPES:
        sheet["psy_rating"] = PSYKER_ARCHETYPES[archetype_id]
        sheet["psychic_powers"] = list(PSYKER_PSYCHIC_POWERS.get(archetype_id, []))
    else:
        sheet["psy_rating"] = 0
        sheet["psychic_powers"] = []

    sheet["corruption"] = 0
    sheet["insanity"] = 0

    # ---- Background: проверка на чужие фракции ----
    faction_key = SUBFACTION_TO_FACTION_KEY.get(subfaction_id, "imperium")
    bg = sheet.get("background", "")
    forbidden = CROSS_FACTION_WORDS.get(faction_key, [])
    has_foreign = False
    if bg and isinstance(bg, str):
        bg_lower = bg.lower()
        for word in forbidden:
            if word in bg_lower:
                has_foreign = True
                break

    if not bg or not isinstance(bg, str) or len(bg.strip()) < 30 or has_foreign:
        sheet["background"] = BACKGROUND_BY_FACTION.get(
            faction_key,
            f"{sheet.get('name', 'Персонаж')} — {sheet.get('archetype', 'странник')} "
            f"из {sheet.get('subfaction', 'неизвестных земель')}."
        )

    return sheet


# ============================================================
# ГЕНЕРАЦИЯ ПОЛНОГО ЛИСТА ЧЕРЕЗ LLM + RAG
# ============================================================
def generate_full_sheet(
    kb,
    faction_id: str,
    subfaction_id: str,
    archetype_id: str,
    faction_name: str,
    subfaction_name: str,
    archetype_name: str,
    extra_choices: dict,
    characteristics: dict,
    name: str,
    age: str = "",
    appearance: str = "",
    background: str = "",
) -> dict:
    """
    Отправляет промт в GigaChat, просит вернуть skills и background.
    Всё остальное (talents/weapons/equipment/armour/wounds/fate) берётся
    из fallback по субфракции.
    """
    rag_query = f"{faction_name} {subfaction_name} {archetype_name}"
    if extra_choices:
        rag_query += " " + " ".join(str(v) for v in extra_choices.values() if v)
    context = kb.format_context(rag_query, top_k=6)

    extra_str = ", ".join(f"{k}: {v}" for k, v in extra_choices.items() if v) or "—"
    chars_str = ", ".join(f"{ch} {v}" for ch, v in characteristics.items())

    prompt = f"""Ты — генератор навыков и предыстории для персонажа настольной RPG Warhammer 40,000 Rogue Trader (система d100).

Персонаж:
- Имя: {name}
- Раса/Фракция: {faction_name}
- Субфракция: {subfaction_name}
- Архетип: {archetype_name}
- Дополнительно: {extra_str}
- Возраст: {age or "не указан"}

Характеристики (НЕ меняй их):
{chars_str}

Справка из базы знаний:
{context}

ВЕРНИ ТОЛЬКО ВАЛИДНЫЙ JSON, без markdown, без пояснений:

{{
  "skills": [
    {{"name": "Скрытность", "characteristic": "Ag", "value": <Ag значение + 5..15>}},
    {{"name": "Внимание", "characteristic": "Per", "value": <Per значение + 5..15>}},
    {{"name": "Дальний бой", "characteristic": "BS", "value": <BS значение + 5..15>}},
    {{"name": "Выживание", "characteristic": "Int", "value": <Int значение + 5..15>}},
    {{"name": "Акробатика", "characteristic": "Ag", "value": <Ag значение + 0..10>}},
    {{"name": "Общие знания", "characteristic": "Int", "value": <Int значение + 0..10>}}
  ],
  "background": "<4-6 предложений от второго лица о персонаже>"
}}

ПРАВИЛА:
1. Навык "Выживание" идёт на Int. "Внимание" — на Per. "Скрытность" и "Акробатика" — на Ag. "Дальний бой" — на BS. "Ближний бой" — на WS.
2. Значение навыка = характеристика + бонус 0..25.
3. Background пиши от второго лица ("Ты родился...", "Твой путь...").
4. Background должен СООТВЕТСТВОВАТЬ РАСЕ. Для эльдара — надменный, древний, скорбящий о падении своего народа. Для орка — агрессивный, громкий, любящий драки. Для тау — идеалистичный, верящий в Высшее Благо. НЕ пиши про другие расы.
5. НЕ добавляй поля armour, weapons, talents, equipment — их добавлять не нужно.
"""

    # ---- Ретрай: до 2 попыток ----
    last_error = None
    for attempt in range(2):
        try:
            giga = GigaChat(
                credentials=API_KEY,
                verify_ssl_certs=False,
                scope="GIGACHAT_API_PERS",
                model=MODEL_NAME,
            )
            response = giga.chat(Chat(messages=[
                Messages(role=MessagesRole.USER, content=prompt)
            ]))
            text = response.choices[0].message.content.strip()
            data = _try_parse_json(text)
            break
        except Exception as e:
            last_error = e
            if attempt == 0:
                continue
            raise ValueError(f"Не удалось получить JSON от GigaChat после 2 попыток: {last_error}")

    # Метаданные
    data["name"] = name
    data["age"] = age
    data["appearance"] = appearance
    data["faction"] = faction_name
    data["subfaction"] = subfaction_name
    data["archetype"] = archetype_name
    data["faction_id"] = faction_id
    data["subfaction_id"] = subfaction_id
    data["archetype_id"] = archetype_id
    data["extra_choices"] = extra_choices
    data["characteristics"] = characteristics
    data["bonuses"] = {ch: char_bonus(v) for ch, v in characteristics.items()}
    data["created_at"] = datetime.now().isoformat()
    data["xp"] = 0
    data["rank"] = 1
    data["user_background"] = background

    # Жёсткий fallback — всё, кроме skills и background, ставится канонично
    data = apply_fallbacks(data, subfaction_id, archetype_id)

    return data