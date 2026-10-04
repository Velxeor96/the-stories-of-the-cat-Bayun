# scripts/patch.py — PATCH_63: 5 субфракций Империума (архетипы)
from __future__ import annotations
import ast, json, shutil, sys
from pathlib import Path

TAG = "PATCH_63"
ROOT = Path(__file__).resolve().parent.parent
if not (ROOT / "app.py").exists():
    print("[ERROR] app.py не найден.")
    sys.exit(1)

r = {"modified": [], "errors": []}

def _bk(p):
    b = p.with_suffix(p.suffix + ".bak_pre_" + TAG)
    if not b.exists() and p.exists():
        try:
            shutil.copy2(p, b)
        except Exception:
            pass

def _write_json(name, data):
    p = ROOT / "data" / name
    if p.exists():
        r["modified"].append(f"data/{name} — уже есть (пропуск)")
        return
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    r["modified"].append(f"data/{name} — создан")

def _write_service(name, meta, extras=""):
    p = ROOT / "services" / f"{name}.py"
    if p.exists():
        r["modified"].append(f"services/{name}.py — уже есть (пропуск)")
        return
    body = f'''"""services/{name}.py — сервис субфракции {meta['name']}."""
from __future__ import annotations
import json
from pathlib import Path

_DATA = None

def _load() -> dict:
    global _DATA
    if _DATA is None:
        p = Path(__file__).resolve().parent.parent / "data" / "{name}.json"
        _DATA = json.loads(p.read_text(encoding="utf-8"))
    return _DATA


def get_archetypes() -> list:
    return _load().get("archetypes", [])

def get_archetypes_by_type(t: str) -> list:
    return [a for a in get_archetypes() if a.get("type") == t]

def get_archetype(arch_id: str):
    for a in get_archetypes():
        if a["id"] == arch_id:
            return a
    return None

def get_talents() -> list:
    return _load().get("talents", [])

def get_talent(talent_id: str):
    for t in get_talents():
        if t.get("id") == talent_id:
            return t
    return None

def get_faction_meta() -> dict:
    d = _load()
    return {{
        "id": d["faction_id"],
        "name": d["name"],
        "full_name": d.get("full_name", d["name"]),
        "description": d.get("description", ""),
    }}
{extras}
'''
    p.write_text(body, encoding="utf-8")
    r["modified"].append(f"services/{name}.py — создан")

# ============================================================
# 1) data/mechanicus.json
# ============================================================
MECHANICUS = {
  "faction_id": "mechanicus",
  "name": "Адептус Механикус",
  "full_name": "Adeptus Mechanicus",
  "description": "Технокульт Марса. Служители Омниссии, хранители знаний Тёмной Эры Технологий. Плоть слаба, но машина — вечна.",
  "source": ["Rogue Trader (стр. 11-63)", "Only War", "Fandom"],
  "archetypes": [
    {"id": "enginseer", "name": "Техножрец-Машиновед", "subtitle": "Tech-priest Enginseer", "type": "основная",
     "description": "Служитель Омниссии, ответственный за обслуживание техники и ритуалы активации.",
     "bonus_characteristics": {"Int": 10, "T": 5},
     "starting_skills": ["Запретное знание (Адептус Механикус)", "Обыденное знание (Адептус Механикус)", "Пользование техники", "Техпользование"],
     "starting_talents": ["Владение оружием (Силовое)", "Механодендрит (Утилита)", "Ритуал освобождения", "Логика"],
     "starting_weapons": ["омниссианский топор"],
     "starting_armour": ["тяжёлая броня AP 8"],
     "starting_gear": ["священные масла", "инфопланшет", "комбиниструмент"],
     "wounds_base": 8},
    {"id": "magos", "name": "Магос", "subtitle": "Magos", "type": "основная",
     "description": "Высший техножрец, магистр знания. Управляет исследовательскими проектами.",
     "bonus_characteristics": {"Int": 15, "WP": 5},
     "starting_skills": ["Запретное знание (Адептус Механикус)", "Запретное знание (Археотех)", "Логика", "Учёное знание (Легенды)"],
     "starting_talents": ["Владение оружием (Силовое)", "Механодендрит (Оружейный)", "Механодендрит (Оптика)", "Мастер-инженер"],
     "starting_weapons": ["силовая секира"],
     "starting_armour": ["силовая броня AP 10"],
     "starting_gear": ["электропривой", "инфопланшет", "психофокус-комп"],
     "wounds_base": 10},
    {"id": "explorator", "name": "Эксплоратор", "subtitle": "Explorator", "type": "основная",
     "description": "Исследователь дальних миров. Ищет археотех, изучает ксеносов, рискует душой ради знания.",
     "bonus_characteristics": {"Int": 10, "Per": 5},
     "starting_skills": ["Запретное знание (Ксеносы)", "Навигация (Звёздная)", "Пользование техники", "Поиск"],
     "starting_talents": ["Владение оружием (Лазерное)", "Механодендрит (Сканер)", "Железная воля"],
     "starting_weapons": ["гальваническая винтовка"],
     "starting_armour": ["карапасная броня AP 7"],
     "starting_gear": ["ауспик", "мнемо-шунт", "сканер"],
     "wounds_base": 9},
    {"id": "genetor", "name": "Генетор", "subtitle": "Genetor", "type": "приписанный",
     "description": "Биолог Механикус. Работает с генной инженерией, клонированием, биомансией.",
     "bonus_characteristics": {"Int": 10, "T": 5},
     "starting_skills": ["Медика", "Запретное знание (Биология)", "Ремесло (Химик)", "Логика"],
     "starting_talents": ["Владение оружием (Лазерное)", "Механодендрит (Медика)", "Ледяное сердце"],
     "starting_weapons": ["лазпистолет"],
     "starting_armour": ["карапасная броня AP 7"],
     "starting_gear": ["диагностор", "медицинская сумка", "инъектор"],
     "wounds_base": 9},
    {"id": "skitarius", "name": "Скитарий", "subtitle": "Skitarii", "type": "основная",
     "description": "Боевой техножрец-легионер. Машина войны, освящённая Омниссией.",
     "bonus_characteristics": {"BS": 5, "T": 5},
     "starting_skills": ["Бдительность", "Атлетика", "Обыденное знание (Война)"],
     "starting_talents": ["Владение оружием (Лазерное)", "Владение оружием (Тяжёлое)", "Железная челюсть", "Молниеносные рефлексы"],
     "starting_weapons": ["гальваническая винтовка", "аркебуза"],
     "starting_armour": ["скитарийская броня AP 8"],
     "starting_gear": ["ауспик", "респиратор", "стим-пакеты"],
     "wounds_base": 11}
  ],
  "talents": [
    {"id": "mech_omnissiah_grace", "name": "Благодать Омниссии", "cost": 200, "effect": "+10 к Техпользованию при работе с археотехом.", "prerequisites": {"rank": 1}},
    {"id": "mech_binary_chatter", "name": "Бинарная речь", "cost": 150, "effect": "Общение с другими Механикус без слов.", "prerequisites": {"rank": 1}},
    {"id": "mech_ferric_lungs", "name": "Железные лёгкие", "cost": 250, "effect": "Дыхание в вакууме до 10 минут.", "prerequisites": {"T": 40}},
    {"id": "mech_machine_touch", "name": "Прикосновение машины", "cost": 300, "effect": "Ремонт техники одним касанием (использует Int вместо Fel).", "prerequisites": {"Int": 40}},
    {"id": "mech_mechadendrite_servo", "name": "Сервопривод механодендрита", "cost": 350, "effect": "Дополнительное действие механодендритом за ход.", "prerequisites": {"rank": 2}}
  ]
}

# ============================================================
# 2) data/inquisition.json
# ============================================================
INQUISITION = {
  "faction_id": "inquisition",
  "name": "Инквизиция",
  "full_name": "The Inquisition",
  "description": "Тайная полиция Империума. Ордо Ксенос, Маллеус, Еретикус. Никто не ожидает Инквизиции.",
  "source": ["Dark Heresy", "Rogue Trader", "Fandom"],
  "archetypes": [
    {"id": "inquisitor", "name": "Инквизитор", "subtitle": "Inquisitor", "type": "основная",
     "description": "Полноправный агент Инквизиции. Власть казнить и миловать именем Императора.",
     "bonus_characteristics": {"WP": 10, "Fel": 5},
     "starting_skills": ["Допрос", "Запретное знание (Ересь)", "Запретное знание (Демонология)", "Сбор информации", "Командование"],
     "starting_talents": ["Аура власти", "Владение оружием (Болтерное)", "Владение оружием (Силовое)", "Непоколебимая вера", "Печать Инквизитора"],
     "starting_weapons": ["болт-пистолет (хор.)", "силовой меч (хор.)"],
     "starting_armour": ["карапасная броня AP 8"],
     "starting_gear": ["инсигния", "печать Инквизитора", "розарий"],
     "wounds_base": 12},
    {"id": "acolyte", "name": "Аколит", "subtitle": "Acolyte", "type": "приписанный",
     "description": "Помощник инквизитора. Может быть кем угодно: учёным, убийцей, псайкером.",
     "bonus_characteristics": {"Int": 5, "Per": 5},
     "starting_skills": ["Бдительность", "Сбор информации", "Скрытность", "Знание языка (Высокий готик)"],
     "starting_talents": ["Владение оружием (Лазерное)", "Владение оружием (Низкотехнологичное)", "Непримечательный"],
     "starting_weapons": ["лазпистолет", "боевой нож"],
     "starting_armour": ["флак-броня AP 4"],
     "starting_gear": ["инфопланшет", "фонарь", "ауспик"],
     "wounds_base": 10},
    {"id": "storm_trooper_inq", "name": "Штурмовик Инквизиции", "subtitle": "Inquisitorial Storm Trooper", "type": "приписанный",
     "description": "Элитный боец инквизиции. Зачистка еретических гнёзд.",
     "bonus_characteristics": {"BS": 10, "WS": 5},
     "starting_skills": ["Бдительность", "Уклонение", "Запугивание", "Скрытность"],
     "starting_talents": ["Владение оружием (Лазерное)", "Владение оружием (Болтерное)", "Нокдаун", "Быстрая перезарядка"],
     "starting_weapons": ["пробивной лазган (хор.)", "болт-пистолет"],
     "starting_armour": ["панцирный доспех штурмовика AP 8"],
     "starting_gear": ["фраг-гранаты (4)", "крак-гранаты (2)"],
     "wounds_base": 13},
    {"id": "psyker_inq", "name": "Псайкер Инквизиции", "subtitle": "Inquisitorial Psyker", "type": "приписанный",
     "description": "Санкционированный псайкер в штате инквизитора. Опасный инструмент.",
     "bonus_characteristics": {"WP": 10, "Per": 5},
     "starting_skills": ["Психическое чутьё", "Запретное знание (Псайкеры)", "Учёное знание (Криптология)"],
     "starting_talents": ["Владение оружием (Лазерное)", "Обострённые чувства (Слух)", "Психосилы на 400 ОО"],
     "starting_weapons": ["лазпистолет", "посох"],
     "starting_armour": ["флак-броня AP 4"],
     "starting_gear": ["психофокус", "инфопланшет"],
     "special": ["Псайкер"],
     "wounds_base": 9},
    {"id": "crusader", "name": "Крусейдер", "subtitle": "Crusader", "type": "приписанный",
     "description": "Рыцарь-фанатик на службе Инквизиции. Сила веры и щит Императора.",
     "bonus_characteristics": {"WS": 10, "S": 5},
     "starting_skills": ["Атлетика", "Запугивание", "Учёное знание (Имперская вера)"],
     "starting_talents": ["Владение оружием (Силовое)", "Непоколебимая вера", "Ненависть (Еретики)", "Нокдаун"],
     "starting_weapons": ["силовой меч", "штурмовой щит"],
     "starting_armour": ["карапасная броня AP 8"],
     "starting_gear": ["розарий", "священные реликвии"],
     "wounds_base": 12}
  ],
  "talents": [
    {"id": "inq_rosette", "name": "Роза Инквизитора", "cost": 400, "effect": "Полномочия Инквизитора. Право требовать подчинения.", "prerequisites": {"rank": 3}},
    {"id": "inq_terror", "name": "Ужас Инквизиции", "cost": 250, "effect": "+20 к Запугиванию против служителей Империума.", "prerequisites": {"Fel": 40}},
    {"id": "inq_sanctioned", "name": "Санкция Инквизиции", "cost": 300, "effect": "Иммунитет к обвинениям в ереси (пока при исполнении).", "prerequisites": {"rank": 2}},
    {"id": "inq_interrogation", "name": "Допрос Инквизитора", "cost": 200, "effect": "Перебрасывает провалы Допроса.", "prerequisites": {"WP": 35}},
    {"id": "inq_purity", "name": "Чистота помыслов", "cost": 350, "effect": "+20 против Порчи и демонического влияния.", "prerequisites": {"WP": 40}}
  ]
}

# ============================================================
# 3) data/sororitas.json
# ============================================================
SORORITAS = {
  "faction_id": "sororitas",
  "name": "Адепта Сороритас",
  "full_name": "Adepta Sororitas",
  "description": "Сёстры Битвы. Воинствующие монахини Экклезиархии. Вера — их щит, огонь — их меч.",
  "source": ["Dark Heresy", "Fandom"],
  "archetypes": [
    {"id": "battle_sister", "name": "Сестра Битвы", "subtitle": "Battle Sister", "type": "основная",
     "description": "Стандартный боец Ордена. Болтер и вера Императора.",
     "bonus_characteristics": {"BS": 10, "WP": 5},
     "starting_skills": ["Бдительность", "Атлетика", "Учёное знание (Имперская вера)"],
     "starting_talents": ["Владение оружием (Болтерное)", "Непоколебимая вера", "Ненависть (Еретики)"],
     "starting_weapons": ["болтер (Годвин-Де'аз)", "боевой нож"],
     "starting_armour": ["силовая броня Сестёр AP 9"],
     "starting_gear": ["розарий", "благословение Императора"],
     "wounds_base": 12},
    {"id": "seraphim", "name": "Серафима", "subtitle": "Seraphim", "type": "основная",
     "description": "Сёстры с прыжковыми ранцами. Небо принадлежит им.",
     "bonus_characteristics": {"Ag": 10, "BS": 5},
     "starting_skills": ["Акробатика", "Атлетика", "Пилотирование (Личное)"],
     "starting_talents": ["Владение оружием (Болтерное)", "Владение оружием (Пистолеты)", "Спринт"],
     "starting_weapons": ["два болт-пистолета"],
     "starting_armour": ["силовая броня Серафим AP 8"],
     "starting_gear": ["прыжковый ранец", "розарий"],
     "wounds_base": 11},
    {"id": "dominion", "name": "Доминион", "subtitle": "Dominion", "type": "основная",
     "description": "Сёстры с штурмовым оружием. Зачистка с ближней дистанции.",
     "bonus_characteristics": {"BS": 10, "S": 5},
     "starting_skills": ["Бдительность", "Запугивание", "Скрытность"],
     "starting_talents": ["Владение оружием (Зажигательное)", "Владение оружием (Мельта)", "Быстрая перезарядка"],
     "starting_weapons": ["огнемёт", "болт-пистолет"],
     "starting_armour": ["силовая броня Сестёр AP 9"],
     "starting_gear": ["розарий", "прометий (5 зарядов)"],
     "wounds_base": 12},
    {"id": "retributor", "name": "Ритрибьютор", "subtitle": "Retributor", "type": "приписанный",
     "description": "Сёстры тяжёлого оружия. Огонь Императора обрушивается на врагов.",
     "bonus_characteristics": {"BS": 10, "S": 5},
     "starting_skills": ["Бдительность", "Затуливание", "Обыденное знание (Война)"],
     "starting_talents": ["Владение оружием (Тяжёлое)", "Железная челюсть"],
     "starting_weapons": ["тяжёлый болтер", "болт-пистолет"],
     "starting_armour": ["силовая броня Сестёр AP 9"],
     "starting_gear": ["боеприпасы (тяжёлый болтер)"],
     "wounds_base": 13},
    {"id": "celestian", "name": "Целестина", "subtitle": "Celestian", "type": "приписанный",
     "description": "Ветеран-сестра. Провела десятки битв и осталась жива. Телохранитель Канониссы.",
     "bonus_characteristics": {"WS": 5, "BS": 5, "WP": 5},
     "starting_skills": ["Командование", "Учёное знание (Тактика Империалис)", "Запугивание"],
     "starting_talents": ["Аура власти", "Владение оружием (Цепное)", "Владение оружием (Болтерное)", "Нокдаун"],
     "starting_weapons": ["цепной меч (хор.)", "болт-пистолет (хор.)"],
     "starting_armour": ["силовая броня Сестёр AP 9"],
     "starting_gear": ["розарий", "реликвия Ордена"],
     "wounds_base": 13}
  ],
  "talents": [
    {"id": "sor_acts_of_faith", "name": "Акт Веры", "cost": 400, "effect": "Раз за сессию совершает чудо верой (переброс любого провала).", "prerequisites": {"WP": 45}},
    {"id": "sor_shield_of_faith", "name": "Щит Веры", "cost": 250, "effect": "+1 AP от силовой брони, если носишь розарий.", "prerequisites": {"rank": 1}},
    {"id": "sor_purity_seal", "name": "Печать Чистоты", "cost": 200, "effect": "+10 против Порчи.", "prerequisites": {"WP": 35}},
    {"id": "sor_spirit_of_martyr", "name": "Дух Мученицы", "cost": 300, "effect": "При смерти — перебрасывает один бросок за товарищей.", "prerequisites": {"rank": 3}},
    {"id": "sor_bolter_doctrine", "name": "Болтерная доктрина", "cost": 250, "effect": "+10 к стрельбе из болтера.", "prerequisites": {"BS": 40}}
  ]
}

# ============================================================
# 4) data/space_marines.json
# ============================================================
SPACE_MARINES = {
  "faction_id": "space_marines",
  "name": "Адептус Астартес",
  "full_name": "Adeptus Astartes",
  "description": "Космические Десантники. Генные воины Императора. Их 1000 Орденов, и каждый — легенда.",
  "source": ["Deathwatch", "Rogue Trader", "Fandom"],
  "archetypes": [
    {"id": "tactical", "name": "Тактик", "subtitle": "Tactical Marine", "type": "основная",
     "description": "Универсальный боец Ордена. Болтер, гибкость, дисциплина.",
     "bonus_characteristics": {"WS": 10, "BS": 10, "S": 10, "T": 10},
     "starting_skills": ["Бдительность", "Атлетика", "Обыденное знание (Война)", "Знание языка (Боевой)"],
     "starting_talents": ["Владение оружием (Болтерное)", "Владение оружием (Цепное)", "Мощь Астартес", "Кислотная слюна", "Двойное сердце"],
     "starting_weapons": ["болтер Астартес (хор.)", "цепной меч"],
     "starting_armour": ["силовая броня Астартес AP 11"],
     "starting_gear": ["болты (4 обоймы)", "фраг-гранаты (3)"],
     "special": ["Импланты Астартес (19 шт.)", "Размер (Крупный)"],
     "wounds_base": 20},
    {"id": "devastator", "name": "Девастатор", "subtitle": "Devastator Marine", "type": "основная",
     "description": "Тяжёлое оружие Ордена. Огонь и смерть с дальних дистанций.",
     "bonus_characteristics": {"BS": 15, "S": 10, "T": 10},
     "starting_skills": ["Затуливание", "Обыденное знание (Война)", "Техпользование"],
     "starting_talents": ["Владение оружием (Тяжёлое)", "Владение оружием (Болтерное)", "Мощь Астартес", "Железная челюсть"],
     "starting_weapons": ["тяжёлый болтер", "болт-пистолет"],
     "starting_armour": ["силовая броня Астартес AP 11"],
     "starting_gear": ["боеприпасы тяжёлого болтера"],
     "special": ["Импланты Астартес", "Размер (Крупный)"],
     "wounds_base": 21},
    {"id": "assault", "name": "Ассаулт", "subtitle": "Assault Marine", "type": "основная",
     "description": "Прыжковый ранец и цепной меч. Удар с неба.",
     "bonus_characteristics": {"WS": 15, "Ag": 10, "S": 10},
     "starting_skills": ["Акробатика", "Атлетика", "Запугивание"],
     "starting_talents": ["Владение оружием (Цепное)", "Владение оружием (Пистолеты)", "Неистовство", "Мощь Астартес"],
     "starting_weapons": ["цепной меч (хор.)", "болт-пистолет (хор.)"],
     "starting_armour": ["силовая броня Астартес AP 11"],
     "starting_gear": ["прыжковый ранец"],
     "special": ["Импланты Астартес", "Размер (Крупный)"],
     "wounds_base": 20},
    {"id": "scout", "name": "Скаут", "subtitle": "Scout Marine", "type": "основная",
     "description": "Молодой десантник до имплантации Чёрного панциря. Разведка, снайперская стрельба.",
     "bonus_characteristics": {"BS": 10, "Per": 10, "Ag": 10},
     "starting_skills": ["Бдительность", "Скрытность", "Слежка", "Выживание"],
     "starting_talents": ["Владение оружием (Лазерное)", "Владение оружием (Снайперское)", "Орлиный глаз", "Мощь Астартес"],
     "starting_weapons": ["снайперская винтовка", "болт-пистолет"],
     "starting_armour": ["скаутская броня AP 6"],
     "starting_gear": ["хамелеолиновый плащ", "ауспик"],
     "special": ["Импланты Астартес (неполные)", "Размер (Крупный)"],
     "wounds_base": 17},
    {"id": "librarian", "name": "Библиарий", "subtitle": "Librarian", "type": "приписанный",
     "description": "Псайкер Ордена. Опасен для врага и для себя.",
     "bonus_characteristics": {"WS": 10, "WP": 15, "Int": 10},
     "starting_skills": ["Психическое чутьё", "Запретное знание (Варп)", "Запретное знание (Псайкеры)"],
     "starting_talents": ["Владение оружием (Силовое)", "Мощь Астартес", "Психосилы на 500 ОО"],
     "starting_weapons": ["силовой меч", "болт-пистолет"],
     "starting_armour": ["силовая броня Астартес AP 11"],
     "starting_gear": ["психофокус", "Книга Санкции"],
     "special": ["Псайкер", "Импланты Астартес", "Размер (Крупный)"],
     "wounds_base": 20},
    {"id": "apothecary", "name": "Апотекарий", "subtitle": "Apothecary", "type": "приписанный",
     "description": "Врач Ордена. Собирает генные семена павших.",
     "bonus_characteristics": {"Int": 10, "T": 10},
     "starting_skills": ["Медика", "Запретное знание (Биология)", "Логика"],
     "starting_talents": ["Владение оружием (Болтерное)", "Мощь Астартес", "Ледяное сердце"],
     "starting_weapons": ["болт-пистолет", "боевой нож (редуктор)"],
     "starting_armour": ["силовая броня Астартес AP 11"],
     "starting_gear": ["медицинская сумка", "редуктор", "диагностор"],
     "special": ["Импланты Астартес", "Размер (Крупный)"],
     "wounds_base": 21}
  ],
  "talents": [
    {"id": "sm_astartes_might", "name": "Мощь Астартес", "cost": 0, "effect": "Сила и Выносливость ×2. Особенности имплантов.", "prerequisites": {"rank": 1}},
    {"id": "sm_killing_strike", "name": "Смертельный удар", "cost": 300, "effect": "Мощный удар в рукопашной, +2 урона и шок.", "prerequisites": {"WS": 45}},
    {"id": "sm_chapter_tactics", "name": "Тактика Ордена", "cost": 350, "effect": "+10 к Командованию внутри Ордена.", "prerequisites": {"Int": 40}},
    {"id": "sm_honour_duel", "name": "Честь в поединке", "cost": 250, "effect": "+10 к рукопашному бою против равного противника.", "prerequisites": {"WS": 40}},
    {"id": "sm_bolter_drill", "name": "Болтерная муштра", "cost": 200, "effect": "+10 к стрельбе из болтера.", "prerequisites": {"BS": 40}}
  ]
}

# ============================================================
# 5) data/arbites.json
# ============================================================
ARBITES = {
  "faction_id": "arbites",
  "name": "Адептус Арбитрес",
  "full_name": "Adeptus Arbites",
  "description": "Судьи Империума. Блюстители Lex Imperialis. Их слово — закон, их щит — Император.",
  "source": ["Dark Heresy", "Rogue Trader", "equipment.txt Раздел VIII"],
  "archetypes": [
    {"id": "patrolman", "name": "Патрульный", "subtitle": "Patrolman", "type": "основная",
     "description": "Обычный арбитр на улицах улья. Судья в патруле.",
     "bonus_characteristics": {"WS": 5, "BS": 5, "T": 5},
     "starting_skills": ["Бдительность", "Запугивание", "Сбор информации", "Обыденное знание (Империум)"],
     "starting_talents": ["Владение оружием (Стабберы)", "Владение оружием (Низкотехнологичное)", "Аура власти", "Уличный боец"],
     "starting_weapons": ["боевой дробовик", "силовой молот"],
     "starting_armour": ["карапасная броня AP 8", "щит Адептус Арбитрес"],
     "starting_gear": ["наручники", "печати", "личный вокс"],
     "wounds_base": 12},
    {"id": "judge", "name": "Судья", "subtitle": "Judge", "type": "основная",
     "description": "Полномочный судья Арбитрес. Выносит приговоры на месте.",
     "bonus_characteristics": {"WP": 10, "Int": 5, "Fel": 5},
     "starting_skills": ["Допрос", "Учёное знание (Закон)", "Командование", "Сбор информации"],
     "starting_talents": ["Аура власти", "Железная дисциплина", "Владение оружием (Силовое)", "Непоколебимая вера"],
     "starting_weapons": ["болт-пистолет (хор.)", "силовой молот"],
     "starting_armour": ["карапасная броня AP 9"],
     "starting_gear": ["Lex Imperialis", "печать Судьи", "ауспик"],
     "wounds_base": 13},
    {"id": "prosecutor", "name": "Прокурор", "subtitle": "Prosecutor", "type": "основная",
     "description": "Специалист по расследованиям. Идёт по следу ереси и коррупции.",
     "bonus_characteristics": {"Int": 10, "Per": 10},
     "starting_skills": ["Сбор информации", "Слежка", "Проницательность", "Учёное знание (Закон)"],
     "starting_talents": ["Бдительность", "Допрос", "Непримечательный", "Владение оружием (Лазерное)"],
     "starting_weapons": ["лазпистолет", "боевой нож"],
     "starting_armour": ["флак-броня AP 4"],
     "starting_gear": ["инфопланшет", "печати", "фонарь", "личный вокс"],
     "wounds_base": 11},
    {"id": "marshal", "name": "Маршал", "subtitle": "Marshal", "type": "приписанный",
     "description": "Командир отряда Арбитрес. Ведёт войска против бунтарей и культистов.",
     "bonus_characteristics": {"WS": 10, "WP": 5, "Fel": 5},
     "starting_skills": ["Командование", "Запугивание", "Учёное знание (Тактика Империалис)"],
     "starting_talents": ["Аура власти", "Железная дисциплина", "Владение оружием (Болтерное)", "Нокдаун"],
     "starting_weapons": ["болтер (хор.)", "силовой молот"],
     "starting_armour": ["карапасная броня AP 9"],
     "starting_gear": ["щит подавления", "печати Маршала"],
     "wounds_base": 13}
  ],
  "talents": [
    {"id": "arb_lex_imperialis", "name": "Lex Imperialis", "cost": 300, "effect": "Знание законов Империума. Может цитировать в суде.", "prerequisites": {"Int": 35}},
    {"id": "arb_verdict", "name": "Приговор Арбитра", "cost": 400, "effect": "Может вынести приговор на месте (NPC подчиняются при провале WP).", "prerequisites": {"rank": 3}},
    {"id": "arb_suppression_shield", "name": "Щит подавления", "cost": 250, "effect": "+20 против психических сил при использовании щита.", "prerequisites": {"rank": 2}},
    {"id": "arb_hardened_boots", "name": "Тяжёлые ботинки", "cost": 200, "effect": "Игнорирует штрафы от неровной местности.", "prerequisites": {"rank": 1}},
    {"id": "arb_warrant", "name": "Ордер", "cost": 300, "effect": "Право на арест и обыск любого подданного Империума.", "prerequisites": {"rank": 3}}
  ]
}

# Запись JSON
_write_json("mechanicus.json", MECHANICUS)
_write_json("inquisition.json", INQUISITION)
_write_json("sororitas.json", SORORITAS)
_write_json("space_marines.json", SPACE_MARINES)
_write_json("arbites.json", ARBITES)

# Запись сервисов
_write_service("mechanicus", MECHANICUS)
_write_service("inquisition", INQUISITION)
_write_service("sororitas", SORORITAS)
_write_service("space_marines", SPACE_MARINES)
_write_service("arbites", ARBITES)

# ============================================================
# 6) wizard.py: расширить _ARCH_FACTIONS
# ============================================================
p = ROOT / "ui" / "screens" / "wizard.py"
text = p.read_text(encoding="utf-8")

NEW_ENTRIES = [
    ('"mechanicus":', '("services.mechanicus", "Специальность")'),
    ('"inquisition":', '("services.inquisition", "Служение")'),
    ('"sororitas":', '("services.sororitas", "Сестринство")'),
    ('"space_marine":', '("services.space_marines", "Специализация")'),
    ('"arbites":', '("services.arbites", "Звание")'),
]

if '"mechanicus":' in text and '"services.mechanicus"' in text:
    r["modified"].append("wizard.py — субфракции Империума уже зарегистрированы")
else:
    # Найдём _ARCH_FACTIONS и допишем туда новые строки
    OLD_MAP_END = '        "Имперская Гвардия":  ("services.imperial_guard",  "Специальность"),\n    }'
    if OLD_MAP_END in text:
        extra = ""
        for key, val in NEW_ENTRIES:
            extra += f'        {key:<23} {val},\n'
        NEW_MAP_END = ('        "Имперская Гвардия":  ("services.imperial_guard",  "Специальность"),\n'
                       + extra
                       + '    }')
        nt = text.replace(OLD_MAP_END, NEW_MAP_END, 1)
        try:
            ast.parse(nt)
        except SyntaxError as e:
            r["errors"].append("wizard.py syntax: " + str(e))
        else:
            _bk(p)
            p.write_text(nt, encoding="utf-8")
            r["modified"].append("wizard.py — +5 субфракций Империума")
    else:
        r["errors"].append("wizard.py: конец _ARCH_FACTIONS не найден")

# ============================================================
# 7) fallbacks.py: добавить inquisition в subfactions
# ============================================================
p = ROOT / "services" / "fallbacks.py"
text = p.read_text(encoding="utf-8")
OLD_SUB = '"imperial_guard", "mechanicus",\n                                 "sororitas", "arbites"]}'
NEW_SUB = '"imperial_guard", "mechanicus",\n                                 "sororitas", "arbites", "inquisition"]}'
if NEW_SUB in text or '"inquisition"' in text:
    r["modified"].append("fallbacks.py — inquisition уже в списке")
elif OLD_SUB in text:
    nt = text.replace(OLD_SUB, NEW_SUB, 1)
    try:
        ast.parse(nt)
    except SyntaxError as e:
        r["errors"].append("fallbacks.py syntax: " + str(e))
    else:
        _bk(p)
        p.write_text(nt, encoding="utf-8")
        r["modified"].append("fallbacks.py — +inquisition в subfactions[imperium]")
else:
    r["errors"].append("fallbacks.py: subfactions список не найден целиком")

# ============================================================
# 8) talents_registry.py: добавить 5 источников
# ============================================================
p = ROOT / "services" / "talents_registry.py"
text = p.read_text(encoding="utf-8")
if '"services.mechanicus"' in text:
    r["modified"].append("talents_registry.py — субфракции уже зарегистрированы")
else:
    OLD_T = '''_TALENT_SOURCES = {
    "necrons":        "services.necrons",
    "tyranids":       "services.tyranids",
    "imperial_guard": "services.imperial_guard",
}'''
    NEW_T = '''_TALENT_SOURCES = {
    "necrons":        "services.necrons",
    "tyranids":       "services.tyranids",
    "imperial_guard": "services.imperial_guard",
    "mechanicus":     "services.mechanicus",
    "inquisition":    "services.inquisition",
    "sororitas":      "services.sororitas",
    "space_marine":   "services.space_marines",
    "arbites":        "services.arbites",
}'''
    if OLD_T in text:
        nt = text.replace(OLD_T, NEW_T, 1)
        try:
            ast.parse(nt)
        except SyntaxError as e:
            r["errors"].append("talents_registry.py syntax: " + str(e))
        else:
            _bk(p)
            p.write_text(nt, encoding="utf-8")
            r["modified"].append("talents_registry.py — +5 субфракций")
    else:
        r["errors"].append("talents_registry.py: _TALENT_SOURCES не найден")

# ============================================================
print("=== PATCH " + TAG + " ===")
for m in r["modified"]:
    print("  [MODIFIED] " + m)
for e in r["errors"]:
    print("  [ERROR] " + e)
print("DONE" if not r["errors"] else "DONE (with errors)")