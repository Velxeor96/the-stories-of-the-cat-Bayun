# character_creation.py
# Логика создания персонажа: генерация, сборка листа, сохранение, история чата.

import os
import json
import random
import re
from datetime import datetime

import streamlit as st

from gigachat import GigaChat
from gigachat.models import Chat, Messages, MessagesRole

from fallbacks_archetypes import FALLBACK_BY_ARCHETYPE
from fallbacks_subfactions import FALLBACK_BY_SUBFACTION, DEFAULT_FALLBACK, ULTIMATE_FALLBACK
from fallbacks_ships import SHIP_BY_SUBFACTION, DEFAULT_SHIP
from fallbacks_currencies import CURRENCY_BY_FACTION, DEFAULT_CURRENCY


# ============================================================
# НАСТРОЙКИ
# ============================================================
try:
    API_KEY = st.secrets["GIGACHAT_API_KEY"]
except Exception:
    API_KEY = "MDFhMDk2NGMtZGQ0Yi03NGJiLTkzNWEtODgzMWEwNjZjZDYzOjBkNDViZDZmLTYxYzQtNGYyNC1hYzFlLTczZGY5OWI5MDZiMw=="

MODEL_NAME = "GigaChat-2-Pro"

CHARACTERS_DIR = "characters"
CHAT_SUFFIX = ".chat.json"

CHARACTERISTICS = ["WS", "BS", "S", "T", "Ag", "Int", "Per", "WP", "Fel"]

CHARACTERISTIC_NAMES_RU = {
    "WS": "Ближний бой (WS)", "BS": "Дальний бой (BS)", "S": "Сила (S)",
    "T": "Выносливость (T)", "Ag": "Ловкость (Ag)", "Int": "Интеллект (Int)",
    "Per": "Восприятие (Per)", "WP": "Сила воли (WP)", "Fel": "Обаяние (Fel)",
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
# ФАЙЛОВАЯ СИСТЕМА
# ============================================================
def ensure_characters_dir():
    os.makedirs(CHARACTERS_DIR, exist_ok=True)


def _safe_character_name(name: str) -> str:
    safe = "".join(c for c in str(name) if c.isalnum() or c in "-_ ").strip()
    return safe or "unnamed"


def save_character(character: dict):
    ensure_characters_dir()
    safe_name = _safe_character_name(character.get("name", "unnamed"))
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
        if fname.endswith(CHAT_SUFFIX):
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
# ИСТОРИЯ ЧАТА
# ============================================================
def chat_history_path(character_name: str) -> str:
    ensure_characters_dir()
    return os.path.join(CHARACTERS_DIR, _safe_character_name(character_name) + CHAT_SUFFIX)


def save_chat_history(character_name: str, chat_history: list) -> str:
    path = chat_history_path(character_name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({
            "character_name": character_name,
            "updated_at": datetime.now().isoformat(),
            "messages": chat_history,
        }, f, ensure_ascii=False, indent=2)
    return path


def load_chat_history(character_name: str) -> list:
    path = chat_history_path(character_name)
    if not os.path.exists(path):
        return []
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data.get("messages", [])
    except Exception:
        return []


def delete_chat_history(character_name: str):
    path = chat_history_path(character_name)
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        pass


# ============================================================
# ПСАЙКЕРЫ
# ============================================================
PSYKER_ARCHETYPES = {
    "astropath": 2, "sorcerer": 2, "seer": 2, "dreamer": 2,
    "worldsinger": 2, "shadowseer": 2, "weirdboy": 1, "navigator": 1,
}

PSYKER_PSYCHIC_POWERS = {
    "astropath":     ["Мысленная связь", "Астро-телепатия", "Внушение"],
    "sorcerer":      ["Разрушитель", "Ободрение", "Усиление"],
    "seer":          ["Фортуна", "Боевая Судьба", "Погибель"],
    "dreamer":       ["Режущий Свет", "Щит Духа", "Сканирование Души"],
    "worldsinger":   ["Щит Духа", "Ободрение", "Сокрытие"],
    "shadowseer":    ["Сокрытие", "Палач", "Усиление"],
    "weirdboy":      ["Da Jump", "Fists of Gork", "Warpath"],
    "navigator":     ["Распахнутый взор", "Взгляд в бездну"],
    "thousand_sons": ["Психический удар", "Взрыв разума", "Предвидение"],
    "magus":         ["Телепатия", "Доминирование", "Ментальный клинок"],
    "bonesinger":    ["Создание кости-призрака", "Восстановление", "Защита"],
    "stonesinger":   ["Резонанс", "Защита духа", "Песнь Мира"],
    "healer":        ["Исцеление", "Восстановление", "Очищение"],
}


# ============================================================
# BACKGROUND И ФРАКЦИИ
# ============================================================
BACKGROUND_BY_FACTION = {
    "eldar": (
        "Ты родился на Крафтворлде, среди костей-призраков и вечного сияния "
        "Бесконечного Цикла. Твой народ угасает, но ты идёшь по Пути, чтобы "
        "обуздать свои страсти и не дать Слаанеш поглотить твою душу. Теперь "
        "твой путь лежит через холодную тьму галактики, где каждый встречный — "
        "либо враг, либо инструмент."
    ),
    "imperium": (
        "Ты родился в Империуме Человечества — колоссальной империи, которой "
        "правит Император с Золотого Трона. Ты служишь человечеству, зная, что "
        "вокруг только ксеносы, еретики и демоны. Каждый твой шаг — во имя "
        "Императора, и каждый враг — угроза для всего, что ты защищаешь."
    ),
    "chaos": (
        "Ты отверг Императора и принял Тёмные Боги. Варп шепчет тебе, обещая "
        "силу и бессмертие. Твои враги — весь Империум, а твои союзники — лишь "
        "до тех пор, пока ты сильнее их. Ты идёшь по пути проклятых, и обратной "
        "дороги нет."
    ),
    "orks": (
        "Ты — орк. Ты родился из споры в грязи, вырос в драках, и вся твоя "
        "жизнь — это война. Ты покинул свой клан, чтобы искать новых врагов, "
        "новые зубы и новую славу. ДАККА! Больше дакки! Вот что делает тебя "
        "счастливым."
    ),
    "tau": (
        "Ты — тау, дитя Империи Тау, служащее Высшему Благу. Ты веришь, что "
        "все разумные расы могут объединиться ради общего процветания. Ты "
        "обучен, дисциплинирован и предан. Твой путь лежит в дикие земли, где "
        "другие расы ещё не познали свет Tau'va."
    ),
    "necrons": (
        "Ты — древний некрон, пробудившийся от шестидесятимиллионнолетнего сна. "
        "Твоя плоть давно стала металлом, а душа — лишь эхо в некродермисе. "
        "Твоя династия требует восстановления былой славы. Галактика забыла, "
        "кто здесь истинный хозяин. Ты напомнишь ей."
    ),
    "tyranids": (
        "Ты — дитя Сверхразума, часть бесконечного роя. Ты был послан вперёд, "
        "чтобы подготовить путь для флотов-ульев. Твоя цель — поглощать, "
        "размножаться и расширяться. Вселенная — это пища. Ты — её пожиратель."
    ),
}

SUBFACTION_TO_FACTION_KEY = {
    "rogue_trader": "imperium", "space_marine": "imperium", "imperial_guard": "imperium",
    "mechanicus": "imperium", "sororitas": "imperium", "arbites": "imperium",
    "chaos_marine": "chaos", "dark_mechanicum": "chaos", "cultist": "chaos",
    "asuryani": "eldar", "drukhari": "eldar", "harlequin": "eldar", "exodite": "eldar",
    "freebooter": "orks", "tau": "tau", "necron": "necrons", "genestealer": "tyranids",
}

CROSS_FACTION_WORDS = {
    "eldar":    ["космодесантник", "астартес", "инквизитор", "механикус", "сороритас", "орк ", " тау", "некрон", "тиранид", "хаосит", "империум"],
    "imperium": ["эльдар", "аэльдари", "асуриани", "друкхари", "орк ", " тау", "некрон", "тиранид", "хаосит", "кхорн", "тзинч", "нургл"],
    "chaos":    ["эльдар", "асуриани", "орк ", " тау", "некрон", "тиранид", "астартес лояльн"],
    "orks":     ["эльдар", "асуриани", "космодесантник", "астартес", "империум", "тау", "некрон", "тиранид"],
    "tau":      ["эльдар", "космодесантник", "астартес", "империум", "орк ", "некрон", "тиранид", "хаосит"],
    "necrons":  ["эльдар", "космодесантник", "астартес", "империум", "орк ", "тау", "тиранид", "хаосит"],
    "tyranids": ["эльдар", "космодесантник", "астартес", "империум", "орк ", "тау", "некрон", "хаосит"],
}


# ============================================================
# ПОЧИНКА JSON
# ============================================================
def _repair_json_text(text: str) -> str:
    if not text:
        return text
    if "```json" in text:
        text = text.split("```json", 1)[1].split("```", 1)[0]
    elif "```" in text:
        text = text.split("```", 1)[1].split("```", 1)[0]
    text = text.strip()
    text = re.sub(r'"(\s*\{)', r'\1', text)
    text = re.sub(r'"(\s*\[)', r'\1', text)
    text = re.sub(r'(\}\s*)"(\s*,)', r'\1\2', text)
    text = re.sub(r'(\]\s*)"(\s*,)', r'\1\2', text)
    text = re.sub(r'([{,]\s*)(\w+)"(\s*:)', r'\1"\2"\3', text)
    text = re.sub(r',(\s*[\]}])', r'\1', text)
    return text


def _try_parse_json(text: str) -> dict:
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass
    repaired = _repair_json_text(text)
    try:
        return json.loads(repaired)
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON не распарсился даже после починки: {e}\n\nСырой ответ:\n{text}")


# ============================================================
# ПРИМЕНЕНИЕ FALLBACK
# ============================================================
def apply_fallbacks(sheet: dict, subfaction_id: str, archetype_id: str) -> dict:
    """Приоритет: архетип → субфракция → универсальный."""
    fallback = None
    if subfaction_id in FALLBACK_BY_ARCHETYPE:
        fallback = FALLBACK_BY_ARCHETYPE[subfaction_id].get(archetype_id)
    if not fallback:
        fallback = FALLBACK_BY_SUBFACTION.get(subfaction_id)
    if not fallback:
        fallback = FALLBACK_BY_SUBFACTION.get(DEFAULT_FALLBACK, ULTIMATE_FALLBACK)

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

    skill_to_char = {
        "скрытность": "Ag", "акробатика": "Ag",
        "внимание": "Per", "бдительность": "Per", "восприятие": "Per",
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
    if "psy_rating" in fallback:
        sheet["psy_rating"] = fallback["psy_rating"]
        sheet["psychic_powers"] = list(PSYKER_PSYCHIC_POWERS.get(archetype_id, []))
    elif archetype_id in PSYKER_ARCHETYPES:
        sheet["psy_rating"] = PSYKER_ARCHETYPES[archetype_id]
        sheet["psychic_powers"] = list(PSYKER_PSYCHIC_POWERS.get(archetype_id, []))
    else:
        sheet["psy_rating"] = 0
        sheet["psychic_powers"] = []

    # ---- Порча ----
    if "corruption" in fallback:
        sheet["corruption"] = fallback["corruption"]
    else:
        fk = SUBFACTION_TO_FACTION_KEY.get(subfaction_id, "imperium")
        sheet["corruption"] = {"chaos": 3}.get(fk, 0)

    sheet["insanity"] = 0

    # ---- Background ----
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

    # ---- Деньги и ресурсы ----
    if "money" not in sheet:
        cur = CURRENCY_BY_FACTION.get(faction_key, DEFAULT_CURRENCY)
        sheet["money"] = cur.get("currency_start", 0)
        sheet["currency"] = cur.get("currency_name", "Троны")
        sheet["special_resources"] = dict(cur.get("special_resources", {}))
        sheet.setdefault("extra_currencies", {})

    # ---- Корабль ----
    if "ship" not in sheet:
        ship = SHIP_BY_SUBFACTION.get(subfaction_id, DEFAULT_SHIP)
        if ship.get("name"):
            sheet["ship"] = {
                "name": ship["name"],
                "class": ship["class"],
                "type": ship["type"],
                "description": ship["description"],
                "hull": dict(ship["hull"]),
                "crew": dict(ship["crew"]),
                "weapons": list(ship["weapons"]),
                "features": list(ship["features"]),
                "status": "В строю",
            }
        else:
            sheet["ship"] = None

    # ---- Мир и состояние ----
    sheet.setdefault("location", "")
    sheet.setdefault("game_date", "Начало приключения")
    sheet.setdefault("quests", [])
    sheet.setdefault("npcs", [])
    sheet.setdefault("effects", [])
    sheet.setdefault("companions", [])
    sheet.setdefault("goals", [])
    sheet.setdefault("journal", [])
    sheet.setdefault("notes", "")

    if "reputation" not in sheet:
        sheet["reputation"] = {
            "Империум": 0, "Механикус": 0, "Инквизиция": 0,
            "Эльдары": 0, "Друкхари": 0, "Орки": 0,
            "Тау": 0, "Некроны": 0, "Хаос": 0, "Тираниды": 0,
        }

    return sheet


# ============================================================
# ГЕНЕРАЦИЯ ПОЛНОГО ЛИСТА ЧЕРЕЗ LLM + RAG
# ============================================================
def generate_full_sheet(
    kb, faction_id, subfaction_id, archetype_id,
    faction_name, subfaction_name, archetype_name,
    extra_choices, characteristics, name,
    age="", appearance="", background="",
) -> dict:
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

    data = apply_fallbacks(data, subfaction_id, archetype_id)
    return data