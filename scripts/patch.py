# scripts/patch.py — PATCH_64: стартовые наборы субфракций Империума
from __future__ import annotations
import ast, shutil, sys
from pathlib import Path

TAG = "PATCH_64"
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

# ============================================================
# 1) faction_starting.py — добавить 6 наборов субфракций
# ============================================================
p = ROOT / "services" / "faction_starting.py"
text = p.read_text(encoding="utf-8")

MARKER = '"imperial_guard": {'
if MARKER in text:
    r["modified"].append("faction_starting.py — наборы субфракций уже есть")
else:
    # Найдём конец FACTION_STARTING — закрывающая "}\n\n\n" перед HOME_WORLD_BONUSES
    ANCHOR = '''    "genestealers": {
        "weapons": [
            {"name": "Автопистолет",
             "stats": "30м, О/3/-, 1d10+2 I, Пробой 0",
             "weight": "1.5 кг", "notes": "Надёжное"},
        ],
        "armour": {"head": 2, "body": 2, "arms": 2, "legs": 2,
                   "notes": "Гражданская броня"},
        "equipment": ["Символ культа", "Ложные документы",
                      "Скрытый передатчик"],
        "talents": ["Обострённые чувства (Зрение)", "Тёмное зрение",
                    "Маскировка (Мастер)"],
        "skills": ["Обман", "Скрытность", "Обаяние"],
        "money": 100, "currency": "Троны",
    },
}'''

    NEW_KITS = '''    "genestealers": {
        "weapons": [
            {"name": "Автопистолет",
             "stats": "30м, О/3/-, 1d10+2 I, Пробой 0",
             "weight": "1.5 кг", "notes": "Надёжное"},
        ],
        "armour": {"head": 2, "body": 2, "arms": 2, "legs": 2,
                   "notes": "Гражданская броня"},
        "equipment": ["Символ культа", "Ложные документы",
                      "Скрытый передатчик"],
        "talents": ["Обострённые чувства (Зрение)", "Тёмное зрение",
                    "Маскировка (Мастер)"],
        "skills": ["Обман", "Скрытность", "Обаяние"],
        "money": 100, "currency": "Троны",
    },

    # ===== PATCH_64: субфракции Империума =====
    "imperial_guard": {
        "weapons": [
            {"name": "Лазган", "stats": "100м, О/3/-, 1d10+3 E, Пробой 0",
             "weight": "2 кг", "notes": "Надёжное"},
            {"name": "Боевой нож", "stats": "Ближний бой, 1d10+2 R, Пробой 0",
             "weight": "1 кг", "notes": "Примитивное"},
        ],
        "armour": {"head": 4, "body": 4, "arms": 4, "legs": 4,
                   "notes": "Флак-броня"},
        "equipment": ["Фляга", "Респиратор", "Рюкзак",
                      "Фраг-гранаты (3)", "Крак-гранаты (3)", "Шлем"],
        "talents": ["Владение оружием (Лазерное)",
                    "Владение оружием (Низкотехнологичное)",
                    "Владение оружием (Стабберы)"],
        "skills": ["Обыденное знание (Имперская Гвардия)",
                   "Языкознание (Низкий готик)", "Бдительность"],
        "money": 50, "currency": "Троны",
    },
    "mechanicus": {
        "weapons": [
            {"name": "Омниссианский топор",
             "stats": "Ближний бой, 2d10+4 E, Пробой 6",
             "weight": "8 кг", "notes": "Силовое поле, Несбалансированное"},
            {"name": "Лазпистолет", "stats": "30м, О/--/--, 1d10+2 E, Пробой 0",
             "weight": "1 кг", "notes": "Надёжное"},
        ],
        "armour": {"head": 8, "body": 8, "arms": 8, "legs": 8,
                   "notes": "Тяжёлая броня Механикус"},
        "equipment": ["Священные масла", "Инфопланшет", "Комбиниструмент",
                      "Механодендрит"],
        "talents": ["Владение оружием (Силовое)",
                    "Механодендрит (Утилита)", "Ритуал освобождения"],
        "skills": ["Запретное знание (Адептус Механикус)",
                   "Техпользование", "Логика"],
        "money": 100, "currency": "Троны",
    },
    "inquisition": {
        "weapons": [
            {"name": "Болт-пистолет",
             "stats": "30м, О/3/-, 1d10+5 X, Пробой 4",
             "weight": "3.5 кг", "notes": "Разрывное"},
            {"name": "Силовой меч",
             "stats": "Ближний бой, 1d10+5 E, Пробой 5",
             "weight": "3 кг", "notes": "Силовое поле, Сбалансированное"},
        ],
        "armour": {"head": 8, "body": 8, "arms": 8, "legs": 8,
                   "notes": "Карапасная броня"},
        "equipment": ["Инсигния", "Розарий", "Инфопланшет",
                      "Печать Инквизитора"],
        "talents": ["Владение оружием (Болтерное)",
                    "Владение оружием (Силовое)", "Непоколебимая вера"],
        "skills": ["Запретное знание (Ересь)",
                   "Сбор информации", "Допрос"],
        "money": 300, "currency": "Троны",
    },
    "sororitas": {
        "weapons": [
            {"name": "Болтер (Годвин-Де'аз)",
             "stats": "90м, О/2/4, 1d10+5 X, Пробой 4",
             "weight": "7 кг", "notes": "Разрывное"},
            {"name": "Боевой нож", "stats": "Ближний бой, 1d10+2 R, Пробой 0",
             "weight": "1 кг", "notes": "Примитивное"},
        ],
        "armour": {"head": 9, "body": 9, "arms": 9, "legs": 9,
                   "notes": "Силовая броня Сестёр (AP 9, +10 к Силе)"},
        "equipment": ["Розарий", "Благословение Императора",
                      "Священные реликвии"],
        "talents": ["Владение оружием (Болтерное)",
                    "Непоколебимая вера", "Ненависть (Еретики)"],
        "skills": ["Обыденное знание (Экклезиархия)",
                   "Учёное знание (Имперская вера)"],
        "money": 150, "currency": "Троны",
    },
    "space_marine": {
        "weapons": [
            {"name": "Болтер Астартес",
             "stats": "100м, О/3/-, 1d10+9 X, Пробой 5",
             "weight": "7 кг", "notes": "Разрывное"},
            {"name": "Цепной меч",
             "stats": "Ближний бой, 1d10+3 R, Пробой 3",
             "weight": "6 кг", "notes": "Цепное"},
        ],
        "armour": {"head": 11, "body": 11, "arms": 11, "legs": 11,
                   "notes": "Силовая броня Астартес (AP 11, +20 к Силе)"},
        "equipment": ["Болты (4 обоймы)", "Фраг-гранаты (3)"],
        "talents": ["Владение оружием (Болтерное)",
                    "Владение оружием (Цепное)", "Мощь Астартес"],
        "skills": ["Обыденное знание (Война)", "Знание языка (Боевой)"],
        "money": 0, "currency": "Реквизиция",
    },
    "arbites": {
        "weapons": [
            {"name": "Боевой дробовик",
             "stats": "30м, О/3/-, 1d10+4 I, Пробой 0",
             "weight": "6 кг", "notes": "Надёжное, Разброс"},
            {"name": "Силовой молот",
             "stats": "Ближний бой, 1d10+5 E, Пробой 6",
             "weight": "5 кг", "notes": "Силовое поле, Шоковое (2)"},
        ],
        "armour": {"head": 8, "body": 8, "arms": 8, "legs": 8,
                   "notes": "Карапасная броня"},
        "equipment": ["Наручники", "Печати", "Ауспик",
                      "Личный вокс", "Щит Адептус Арбитрес"],
        "talents": ["Владение оружием (Стабберы)",
                    "Владение оружием (Силовое)", "Аура власти"],
        "skills": ["Запугивание", "Сбор информации",
                   "Учёное знание (Закон)"],
        "money": 200, "currency": "Троны",
    },
}'''

    if ANCHOR in text:
        nt = text.replace(ANCHOR, NEW_KITS, 1)
        try:
            ast.parse(nt)
        except SyntaxError as e:
            r["errors"].append("faction_starting.py syntax: " + str(e))
        else:
            _bk(p)
            p.write_text(nt, encoding="utf-8")
            r["modified"].append("faction_starting.py — +6 наборов субфракций")
    else:
        r["errors"].append("faction_starting.py: не нашёл конец FACTION_STARTING (genestealers)")

# ============================================================
# 2) character_creation.py — использовать subfaction_id + arch bonus
# ============================================================
p = ROOT / "services" / "character_creation.py"
text = p.read_text(encoding="utf-8")

if "PATCH_64" in text and "_arch_service_map" in text:
    r["modified"].append("character_creation.py — уже пропатчен")
else:
    # 2а) Найти строку "    if faction_id in ("necrons", "tyranids"):" и вставить
    #      перед ней блок применения архетипных бонусов + определения _kit_key
    OLD_IF = '    if faction_id in ("necrons", "tyranids"):'
    NEW_IF = '''    # PATCH_64: бонусы архетипа для всех субфракций с сервисом
    _arch_service_map = {
        "imperial_guard": "services.imperial_guard",
        "mechanicus":     "services.mechanicus",
        "inquisition":    "services.inquisition",
        "sororitas":      "services.sororitas",
        "space_marine":   "services.space_marines",
        "arbites":        "services.arbites",
    }
    _kit_key = subfaction_id if subfaction_id else faction_id
    _arch_key = _kit_key if _kit_key in _arch_service_map else None
    if _arch_key:
        try:
            _mod = __import__(_arch_service_map[_arch_key],
                              fromlist=["get_archetype"])
            _arch = _mod.get_archetype(career_id or "")
        except Exception as _e:
            print("[build_character] archetype: " + type(_e).__name__)
            _arch = None
        if _arch:
            for _k, _v in (_arch.get("bonus_characteristics", {}) or {}).items():
                if _k in stats:
                    stats[_k] = int(stats[_k]) + int(_v)

    if faction_id in ("necrons", "tyranids"):'''

    # 2б) Заменить get_starting_kit(faction_id) на get_starting_kit(_kit_key)
    OLD_KIT = '        kit = get_starting_kit(faction_id)'
    NEW_KIT = '        kit = get_starting_kit(_kit_key)'

    nt = text
    changed = 0

    if OLD_IF in nt:
        nt = nt.replace(OLD_IF, NEW_IF, 1)
        changed += 1
    else:
        r["errors"].append("character_creation.py: 'if faction_id in (necrons, tyranids)' не найдена")

    if OLD_KIT in nt:
        nt = nt.replace(OLD_KIT, NEW_KIT, 1)
        changed += 1
    else:
        r["errors"].append("character_creation.py: 'kit = get_starting_kit(faction_id)' не найдена")

    if changed > 0 and not r["errors"]:
        try:
            ast.parse(nt)
        except SyntaxError as e:
            r["errors"].append("character_creation.py syntax: " + str(e))
        else:
            _bk(p)
            p.write_text(nt, encoding="utf-8")
            r["modified"].append("character_creation.py — subfaction kit + arch bonuses")

print("=== PATCH " + TAG + " ===")
for m in r["modified"]:
    print("  [MODIFIED] " + m)
for e in r["errors"]:
    print("  [ERROR] " + e)
print("DONE" if not r["errors"] else "DONE (with errors)")