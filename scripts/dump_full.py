# scripts/patch.py — PATCH_88
# Критичные баги + пополнение FACTION_STARTING + fallback бонусов + перенос тестов.
from __future__ import annotations
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TAG = "PATCH_88"
LOG = []


def backup(p: Path) -> None:
    if not p.exists():
        return
    bak = p.with_suffix(p.suffix + ".bak_pre_" + TAG)
    if not bak.exists():
        shutil.copy2(p, bak)


def read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def write(p: Path, text: str) -> None:
    p.write_text(text, encoding="utf-8")


def sub_once(text: str, old: str, new: str, tag: str) -> str:
    if old not in text:
        LOG.append("[WARN] " + tag + ": не найдена точка замены")
        return text
    return text.replace(old, new, 1)


def patch_file(rel: str, mutator) -> None:
    p = ROOT / rel
    if not p.exists():
        LOG.append("[ERROR] " + rel + ": файл не найден")
        return
    backup(p)
    text = read(p)
    new_text = mutator(text)
    if new_text != text:
        write(p, new_text)
        LOG.append("[OK]   " + rel)
    else:
        LOG.append("[SKIP] " + rel)


# ============================================================
# 1. app.py: psy.render -> psy.render_entry
# ============================================================
def _patch_app(text: str) -> str:
    return sub_once(
        text,
        '"psy": psy.render,',
        '"psy": psy.render_entry,',
        "app.py psy",
    )


# ============================================================
# 2. ui/screens/psy.py: добавить render_entry
# ============================================================
_PSY_ENTRY = '''

def render_entry() -> None:
    """PATCH_88: обёртка для app.py. Сама достаёт активного персонажа."""
    import streamlit as st
    login = st.session_state.get("user_login")
    name = st.session_state.get("active_character")
    if not login or not name:
        st.session_state.screen = "main_menu"
        st.rerun()
        return
    try:
        from persistence.characters import load_character
        char = load_character(login, name)
    except Exception as e:
        st.error("Не удалось загрузить персонажа: " + str(e))
        if st.button("В главное меню", key="psy_back_err"):
            st.session_state.screen = "main_menu"
            st.rerun()
        return
    render(char)
    st.markdown("---")
    if st.button("\\u2190 В игру", key="psy_back", use_container_width=True):
        st.session_state.screen = "game"
        st.rerun()
'''


def _patch_psy(text: str) -> str:
    if "def render_entry" in text:
        LOG.append("[SKIP] ui/screens/psy.py: render_entry уже есть")
        return text
    if not text.endswith("\n"):
        text += "\n"
    return text + _PSY_ENTRY


# ============================================================
# 3. services/state_applier.py: xp/wounds/fate дельта/абсолют
# ============================================================
_SIMPLE_ABS_OLD = '''    simple_abs = {
        "wounds": ("wounds", "current"),
        "fate": ("fate_points", "current"),
        "insanity": (None, "insanity"),
        "corruption": (None, "corruption"),
        "xp": (None, "xp"),
        "rank": (None, "rank"),
    }'''

_SIMPLE_ABS_NEW = '''    # PATCH_88: wounds/fate/xp вынесены ниже как "дельта или абсолют".
    # insanity/corruption/rank остаются абсолютными.
    simple_abs = {
        "insanity": (None, "insanity"),
        "corruption": (None, "corruption"),
        "rank": (None, "rank"),
    }'''

_XP_OLD = '''    if "xp" in changes:
        is_d, v = _delta(changes["xp"])
        if is_d:
            char["xp"] = int(char.get("xp", 0) or 0) + v
'''

_XP_NEW = '''    # PATCH_88: wounds / fate / xp — дельта, если начинается с +/-,
    # иначе абсолют. Убирает двойной подсчёт xp=+50.
    if "wounds" in changes:
        w = _ensure_dict(char, "wounds")
        is_d, v = _delta(changes["wounds"])
        cur = int(w.get("current", 0) or 0)
        w["current"] = (cur + v) if is_d else _to_int(changes["wounds"], cur)
        applied.append("wounds")

    if "fate" in changes:
        fp = _ensure_dict(char, "fate_points")
        is_d, v = _delta(changes["fate"])
        cur = int(fp.get("current", 0) or 0)
        fp["current"] = (cur + v) if is_d else _to_int(changes["fate"], cur)
        applied.append("fate")

    if "xp" in changes:
        is_d, v = _delta(changes["xp"])
        cur = int(char.get("xp", 0) or 0)
        char["xp"] = (cur + v) if is_d else _to_int(changes["xp"], cur)
        applied.append("xp")
'''


def _patch_state_applier(text: str) -> str:
    text = sub_once(text, _SIMPLE_ABS_OLD, _SIMPLE_ABS_NEW, "state_applier simple_abs")
    text = sub_once(text, _XP_OLD, _XP_NEW, "state_applier xp block")
    return text


# ============================================================
# 4. services/character_creation.py: archetype_id kwarg
# ============================================================
_BC_OLD = '''def build_character(
    *, name, gender, age, appearance, user_background,
    faction_id, subfaction_id=None,
    home_world_id=None, career_id=None,
    characteristics=None,
):
    if faction_id not in FACTIONS:
        raise ValueError("Неизвестная фракция: " + str(faction_id))'''

_BC_NEW = '''def build_character(
    *, name, gender, age, appearance, user_background,
    faction_id, subfaction_id=None,
    home_world_id=None, career_id=None, archetype_id=None,
    characteristics=None,
):
    # PATCH_88: tutorial передаёт archetype_id — принимаем как алиас career_id.
    if archetype_id and not career_id:
        career_id = archetype_id
    if faction_id not in FACTIONS:
        raise ValueError("Неизвестная фракция: " + str(faction_id))'''


def _patch_creation(text: str) -> str:
    return sub_once(text, _BC_OLD, _BC_NEW, "character_creation signature")


# ============================================================
# 5. services/necrons.py: удалить дубль + алиас get_components
# ============================================================
def _patch_necrons(text: str) -> str:
    pattern = re.compile(
        r"# === PATCH_43: загрузка расширенных данных ===.*?"
        r"(?=# === PATCH_43: расширенные данные ===)",
        re.DOTALL,
    )
    if "# === PATCH_43: загрузка расширенных данных ===" in text:
        text = pattern.sub(
            "# === PATCH_43: расширенные данные (дедуп в PATCH_88) ===\n",
            text, count=1,
        )
    else:
        LOG.append("[SKIP] necrons: дублирующий блок уже удалён")

    # алиас get_components
    if "def get_components" not in text:
        text = text.rstrip() + '''


# PATCH_88: алиас для совместимости с внешним кодом
def get_components():
    return get_ship_components()
'''
    return text


# ============================================================
# 6. ui/screens/game.py: psy-save + 1 _logout
# ============================================================
_GAME_PSY_OLD = '''        try:
            from services.psy_archetypes import ensure_psy_fields
            _psy_changed = ensure_psy_fields(char)
            if _psy_changed:
                try:
                    from persistence.characters import save_character as _save_psy
                    _save_psy(login, char_name, char)
                except Exception:
                    pass
        except Exception as _e:
            print("[game] ensure_psy fail: " + type(_e).__name__)'''

_GAME_PSY_NEW = '''        try:
            from services.psy_archetypes import ensure_psy_fields
            _before_psy = int(char.get("psy_rating", 0) or 0)
            ensure_psy_fields(char)
            _after_psy = int(char.get("psy_rating", 0) or 0)
            if _after_psy != _before_psy:
                try:
                    from persistence.characters import save_character as _save_psy
                    _save_psy(login, char_name, char)
                except Exception:
                    pass
        except Exception as _e:
            print("[game] ensure_psy fail: " + type(_e).__name__)'''

_GAME_LOGOUT_OLD = '''        if st.button("Выход", use_container_width=True, key="game_exit"):
            _logout()
            _logout()
            _logout()'''

_GAME_LOGOUT_NEW = '''        if st.button("Выход", use_container_width=True, key="game_exit"):
            _logout()'''


def _patch_game(text: str) -> str:
    text = sub_once(text, _GAME_PSY_OLD, _GAME_PSY_NEW, "game psy-save")
    text = sub_once(text, _GAME_LOGOUT_OLD, _GAME_LOGOUT_NEW, "game 3x logout")
    return text


# ============================================================
# 7. ui/screens/character.py: потерянный markdown
# ============================================================
def _patch_character_screen(text: str) -> str:
    return sub_once(
        text,
        "    # --- Кнопки ---    st.markdown(\"---\")\n    c1, c2, c3 = st.columns(3)",
        "    # --- Кнопки ---\n    st.markdown(\"---\")\n    c1, c2, c3 = st.columns(3)",
        "character screen markdown",
    )


# ============================================================
# 8. services/faction_starting.py: киты субфракций + fallback
# ============================================================
_NEW_KITS = '''    },

    # ===== PATCH_88: субфракции Эльдар =====
    "asuryani": {
        "weapons": [
            {"name": "Сюрикен-катапульта",
             "stats": "60м, О/3/-, 1d10+4 R, Пробой 3",
             "weight": "2.5 кг", "notes": "Надёжное"},
            {"name": "Эльдарский силовой меч",
             "stats": "Ближний бой, 1d10+4 E, Пробой 6",
             "weight": "2 кг", "notes": "Сбалансированное, Силовое поле"},
        ],
        "armour": {"head": 6, "body": 6, "arms": 6, "legs": 6,
                   "notes": "Аспектная броня (Все AP 6)"},
        "equipment": ["Камень Души", "Шлем Аспекта", "Плащ-хамелеолин"],
        "talents": ["Обострённые чувства (Зрение)", "Тёмное зрение",
                    "Молниеносные рефлексы", "Сверхъестественная ловкость"],
        "skills": ["Общие знания (Эльдар)", "Разговорный язык (Эльдар)",
                   "Уклонение"],
        "money": 200, "currency": "Троны",
    },
    "harlequin": {
        "weapons": [
            {"name": "Поцелуй Арлекина",
             "stats": "Ближний бой, 1d10+6 E, Пробой 8",
             "weight": "1.5 кг", "notes": "Силовое поле, Точное"},
            {"name": "Сюрикен-пистолет",
             "stats": "30м, О/3/-, 1d10+2 R, Пробой 3",
             "weight": "1.5 кг", "notes": "Надёжное"},
        ],
        "armour": {"head": 6, "body": 6, "arms": 6, "legs": 6,
                   "notes": "Костюм Арлекина (Все AP 6, +10 Ag)"},
        "equipment": ["Камень Души", "Маска Арлекина", "Кисел"],
        "talents": ["Обострённые чувства (Зрение)", "Тёмное зрение",
                    "Спринт", "Молниеносные рефлексы", "Мастер боя"],
        "skills": ["Акробатика", "Уклонение", "Скрытность", "Обаяние"],
        "money": 150, "currency": "Троны",
    },
    "exodite": {
        "weapons": [
            {"name": "Эльдарский силовой меч",
             "stats": "Ближний бой, 1d10+4 E, Пробой 6",
             "weight": "2 кг", "notes": "Сбалансированное, Силовое поле"},
            {"name": "Длинный лук",
             "stats": "100м, О/1/-, 1d10+3 R, Пробой 2",
             "weight": "1.5 кг", "notes": "Примитивное, Точное"},
        ],
        "armour": {"head": 5, "body": 5, "arms": 5, "legs": 5,
                   "notes": "Костяная броня (Все AP 5)"},
        "equipment": ["Камень Души", "Дракон-компаньон", "Колчан стрел"],
        "talents": ["Обострённые чувства (Зрение)", "Выживание",
                    "Снайпер", "Спринт"],
        "skills": ["Выживание", "Знание природы", "Скрытность",
                   "Разговорный язык (Эльдар)"],
        "money": 100, "currency": "Троны",
    },

    # ===== PATCH_88: субфракции Хаоса =====
    "chaos_marine": {
        "weapons": [
            {"name": "Болтер Хаоса",
             "stats": "100м, О/3/-, 1d10+9 X, Пробой 5",
             "weight": "7 кг", "notes": "Разрывное"},
            {"name": "Цепной меч",
             "stats": "Ближний бой, 1d10+4 R, Пробой 3",
             "weight": "6 кг", "notes": "Цепное"},
        ],
        "armour": {"head": 11, "body": 11, "arms": 11, "legs": 11,
                   "notes": "Силовая броня Астартес Хаоса (AP 11, +20 S)"},
        "equipment": ["Болты (4 обоймы)", "Фраг-гранаты (3)",
                      "Символ Тёмного Бога", "Печать Скверны"],
        "talents": ["Владение оружием (Болтерное)",
                    "Владение оружием (Цепное)", "Мощь Астартес",
                    "Ненависть (Империум)"],
        "skills": ["Обыденное знание (Война)",
                   "Разговорный язык (Тёмный готик)", "Запугивание"],
        "money": 150, "currency": "Троны",
    },
    "dark_mechanicum": {
        "weapons": [
            {"name": "Омниссианский топор Хаоса",
             "stats": "Ближний бой, 2d10+4 E, Пробой 6",
             "weight": "8 кг", "notes": "Силовое поле, Несбалансированное"},
            {"name": "Плазма-пистолет",
             "stats": "30м, О/2/-, 1d10+6 E, Пробой 6",
             "weight": "4 кг", "notes": "Опасное"},
        ],
        "armour": {"head": 9, "body": 9, "arms": 9, "legs": 9,
                   "notes": "Тяжёлая броня Тёмного Механикум"},
        "equipment": ["Священные масла Хаоса", "Механодендрит",
                      "Инфопланшет Хаоса", "Демонический комбиниструмент"],
        "talents": ["Владение оружием (Силовое)",
                    "Механодендрит (Оружейный)", "Ритуал освобождения",
                    "Сопротивление (Псайкеры)"],
        "skills": ["Запретное знание (Варп)", "Техпользование", "Логика"],
        "money": 200, "currency": "Троны",
    },
    "cultist": {
        "weapons": [
            {"name": "Автопистолет",
             "stats": "30м, О/3/-, 1d10+3 I, Пробой 0",
             "weight": "1.5 кг", "notes": "Надёжное"},
            {"name": "Жертвенный нож",
             "stats": "Ближний бой, 1d10+2 R, Пробой 0",
             "weight": "1 кг", "notes": "Примитивное"},
        ],
        "armour": {"head": 2, "body": 2, "arms": 2, "legs": 2,
                   "notes": "Гражданская броня"},
        "equipment": ["Символ Тёмного Бога", "Книга Ритуалов",
                      "Жертвенные принадлежности"],
        "talents": ["Сопротивление (Страх)", "Ярость",
                    "Ненависть (Империум)", "Фанатизм"],
        "skills": ["Запретное знание (Варп)", "Обман",
                   "Разговорный язык (Низкий готик)"],
        "money": 50, "currency": "Троны",
    },

    # ===== PATCH_88: субфракции Орков =====
    "freebooter": {
        "weapons": [
            {"name": "Слагга",
             "stats": "60м, О/3/-, 1d10+4 I, Пробой 2",
             "weight": "5 кг", "notes": "Надёжное"},
            {"name": "Чоппа",
             "stats": "Ближний бой, 1d10+3 R, Пробой 2",
             "weight": "4 кг", "notes": "Цепное"},
        ],
        "armour": {"head": 4, "body": 4, "arms": 4, "legs": 4,
                   "notes": "Импровизированная броня"},
        "equipment": ["Зубы", "Фляга грибного пива", "Грот-помощник"],
        "talents": ["Ярость", "Сопротивление (Яд)", "Рвач",
                    "Обострённые чувства (Зрение)"],
        "skills": ["Разговорный язык (Орочий)", "Запугивание", "Драка"],
        "money": 50, "currency": "Зубы",
    },

    # ===== PATCH_88: субфракции Тау =====
    "fire_warrior": {
        "weapons": [
            {"name": "Импульсная винтовка",
             "stats": "150м, О/3/-, 1d10+4 E, Пробой 4",
             "weight": "4 кг", "notes": "Надёжное, Точное"},
            {"name": "Плазменный клинок",
             "stats": "Ближний бой, 1d10+6 E, Пробой 8",
             "weight": "2 кг", "notes": "Силовое поле"},
        ],
        "armour": {"head": 6, "body": 6, "arms": 6, "legs": 6,
                   "notes": "Боевой костюм Тау (Все AP 6)"},
        "equipment": ["Дрон-помощник", "Маркерный маяк", "Инфопланшет"],
        "talents": ["Обострённые чувства (Зрение)", "Снайпер",
                    "Сопротивление (Страх)"],
        "skills": ["Пилотирование (Личное)", "Техноиспользование",
                   "Разговорный язык (Тау)"],
        "money": 100, "currency": "Троны",
    },

    # ===== PATCH_88: субфракции Друхкари =====
    "kabalite": {
        "weapons": [
            {"name": "Сюрикен-пистолет",
             "stats": "30м, О/3/-, 1d10+2 R, Пробой 3",
             "weight": "1.5 кг", "notes": "Надёжное"},
            {"name": "Агонайзер",
             "stats": "Ближний бой, 1d10+4 E, Пробой 4",
             "weight": "1.5 кг", "notes": "Шоковое (3), Болевое"},
        ],
        "armour": {"head": 5, "body": 5, "arms": 5, "legs": 5,
                   "notes": "Шипастая броня (Все AP 5)"},
        "equipment": ["Яды", "Клинки-осколки", "Трофей"],
        "talents": ["Тёмное зрение", "Обострённые чувства (Зрение)",
                    "Обострённые чувства (Слух)", "Спринт"],
        "skills": ["Уклонение", "Запугивание", "Скрытность",
                   "Разговорный язык (Друхкари)"],
        "money": 200, "currency": "Троны",
    },

    # ===== PATCH_88: субфракции Некронов =====
    "necron_lord": {
        "weapons": [
            {"name": "Гаусс-флинта",
             "stats": "120м, О/3/-, 1d10+5 E, Пробой 4",
             "weight": "3 кг", "notes": "Гаусс"},
            {"name": "Силовой клинок Некрона",
             "stats": "Ближний бой, 1d10+6 E, Пробой 6",
             "weight": "3 кг", "notes": "Силовое поле, Гиперфазовая"},
        ],
        "armour": {"head": 10, "body": 10, "arms": 10, "legs": 10,
                   "notes": "Некродермис (Все AP 10)"},
        "equipment": ["Скарабей-слуга", "Фаза-серп",
                      "Регенерационный слой", "Орб Возрождения"],
        "talents": ["Сверхъестественная стойкость",
                    "Сопротивление (Страх)", "Тёмное зрение",
                    "Молниеносные рефлексы"],
        "skills": ["Запретные знания (Древние)",
                   "Общие знания (Некроны)", "Командование"],
        "money": 0, "currency": "Нет",
    },

    # ===== PATCH_88: субфракции Генокрадов =====
    "magus": {
        "weapons": [
            {"name": "Автопистолет",
             "stats": "30м, О/3/-, 1d10+2 I, Пробой 0",
             "weight": "1.5 кг", "notes": "Надёжное"},
            {"name": "Коготь генокрада",
             "stats": "Ближний бой, 1d10+4 R, Пробой 5",
             "weight": "1 кг", "notes": "Рвущее, Точное"},
        ],
        "armour": {"head": 3, "body": 3, "arms": 3, "legs": 3,
                   "notes": "Гражданская броня"},
        "equipment": ["Символ культа", "Ложные документы",
                      "Скрытый передатчик"],
        "talents": ["Обострённые чувства (Зрение)", "Тёмное зрение",
                    "Маскировка (Мастер)", "Сопротивление (Псайкеры)"],
        "skills": ["Обман", "Скрытность", "Обаяние", "Командование"],
        "money": 100, "currency": "Троны",
    },
'''

_ANCHOR_OLD = '''        "money": 200, "currency": "Троны",
    },
}


# ===== БОНУСЫ РОДНЫХ МИРОВ ====='''

_ANCHOR_NEW = '''        "money": 200, "currency": "Троны",
    },''' + _NEW_KITS + '''}


# ===== БОНУСЫ РОДНЫХ МИРОВ ====='''


_FALLBACK_OLD = '''def get_starting_kit(faction_id):
    return FACTION_STARTING.get(faction_id, FACTION_STARTING.get("imperium", {}))


def _lookup(table, faction_id, name):
    if not name:
        return {"bonus": {}, "penalty": {}}
    tf = table.get(faction_id, {})
    n = _norm(name)
    for key, val in tf.items():
        if _norm(key) == n:
            return {"bonus": dict(val.get("bonus") or {}),
                    "penalty": dict(val.get("penalty") or {})}
    return {"bonus": {}, "penalty": {}}


def get_home_world_bonuses(faction_id, name):
    return _lookup(HOME_WORLD_BONUSES, faction_id, name)


def get_career_bonuses(faction_id, name):
    return _lookup(CAREER_BONUSES, faction_id, name)'''

_FALLBACK_NEW = '''# PATCH_88: карта «id субфракции -> модуль сервиса»
_SERVICE_MAP = {
    "imperial_guard": "services.imperial_guard",
    "mechanicus":     "services.mechanicus",
    "inquisition":    "services.inquisition",
    "sororitas":      "services.sororitas",
    "space_marine":   "services.space_marines",
    "arbites":        "services.arbites",
}


def _resolve_parent(fid):
    try:
        from services.fallbacks import _resolve_parent_faction
        return _resolve_parent_faction(fid)
    except Exception:
        return fid


def _try_subfaction_service(faction_id, name, kind):
    """PATCH_88: если у субфракции есть свой сервис — берём бонусы оттуда."""
    mod_name = _SERVICE_MAP.get(faction_id)
    if not mod_name:
        return None
    try:
        mod = __import__(mod_name, fromlist=["get_archetypes", "get_home_worlds"])
    except Exception as e:
        print("[starting] " + faction_id + " import: " + str(e))
        return None
    n = _norm(name)
    if kind == "home_world":
        try:
            for hw in mod.get_home_worlds():
                if _norm(hw.get("name", "")) == n:
                    return {"bonus": dict(hw.get("chars") or {}),
                            "penalty": dict(hw.get("penalty") or {})}
        except Exception as e:
            print("[starting] " + faction_id + " hw: " + str(e))
    elif kind == "career":
        try:
            for a in mod.get_archetypes():
                if _norm(a.get("name", "")) == n:
                    return {"bonus": dict(a.get("bonus_characteristics") or {}),
                            "penalty": {}}
        except Exception as e:
            print("[starting] " + faction_id + " career: " + str(e))
    return None


def get_starting_kit(faction_id):
    # PATCH_88: точное совпадение -> родительская фракция -> imperium.
    if faction_id in FACTION_STARTING:
        return FACTION_STARTING[faction_id]
    parent = _resolve_parent(faction_id)
    if parent != faction_id and parent in FACTION_STARTING:
        return FACTION_STARTING[parent]
    return FACTION_STARTING.get("imperium", {})


def _lookup(table, faction_id, name):
    if not name:
        return {"bonus": {}, "penalty": {}}
    tf = table.get(faction_id, {})
    n = _norm(name)
    for key, val in tf.items():
        if _norm(key) == n:
            return {"bonus": dict(val.get("bonus") or {}),
                    "penalty": dict(val.get("penalty") or {})}
    return {"bonus": {}, "penalty": {}}


def get_home_world_bonuses(faction_id, name):
    if not name:
        return {"bonus": {}, "penalty": {}}
    r = _lookup(HOME_WORLD_BONUSES, faction_id, name)
    if r["bonus"] or r["penalty"]:
        return r
    sub = _try_subfaction_service(faction_id, name, "home_world")
    if sub is not None:
        return sub
    return _lookup(HOME_WORLD_BONUSES, _resolve_parent(faction_id), name)


def get_career_bonuses(faction_id, name):
    if not name:
        return {"bonus": {}, "penalty": {}}
    r = _lookup(CAREER_BONUSES, faction_id, name)
    if r["bonus"] or r["penalty"]:
        return r
    sub = _try_subfaction_service(faction_id, name, "career")
    if sub is not None:
        return sub
    return _lookup(CAREER_BONUSES, _resolve_parent(faction_id), name)'''


def _patch_faction_starting(text: str) -> str:
    text = sub_once(text, _ANCHOR_OLD, _ANCHOR_NEW, "faction_starting kits")
    text = sub_once(text, _FALLBACK_OLD, _FALLBACK_NEW, "faction_starting fallback")
    return text


# ============================================================
# 9. Перенос тестов из _reference_from_old/tests/
# ============================================================
def _migrate_tests() -> None:
    src = ROOT / "_reference_from_old" / "tests"
    dst = ROOT / "tests"
    if not src.exists():
        LOG.append("[SKIP] _reference_from_old/tests: нет папки")
        return
    if not dst.exists():
        dst.mkdir(parents=True, exist_ok=True)

    existing_services = {p.stem for p in (ROOT / "services").glob("*.py")}

    def rewrite_line(line: str) -> str:
        m = re.match(r"^(\s*)(from|import)\s+core\.(\w+)", line)
        if not m:
            return line
        mod = m.group(3)
        if mod in existing_services:
            return line.replace("core." + mod, "services." + mod, 1)
        return line

    count = 0
    skipped = []
    for f in sorted(src.glob("*.py")):
        if f.name == "__init__.py":
            continue
        target = dst / f.name
        if target.exists() and target.name != "__init__.py":
            skipped.append(f.name)
            continue
        try:
            text = f.read_text(encoding="utf-8")
        except Exception as e:
            LOG.append("[WARN] tests/" + f.name + " read: " + str(e))
            continue
        lines = [rewrite_line(l) for l in text.splitlines()]
        target.write_text("\n".join(lines) + "\n", encoding="utf-8")
        count += 1
    LOG.append("[OK]   tests/: перенесено " + str(count) + " файлов"
               + (" (пропущено: " + ", ".join(skipped) + ")" if skipped else ""))


# ============================================================
# MAIN
# ============================================================
def main() -> int:
    print("=== " + TAG + " ===\n")

    patch_file("app.py", _patch_app)
    patch_file("ui/screens/psy.py", _patch_psy)
    patch_file("services/state_applier.py", _patch_state_applier)
    patch_file("services/character_creation.py", _patch_creation)
    patch_file("services/necrons.py", _patch_necrons)
    patch_file("ui/screens/game.py", _patch_game)
    patch_file("ui/screens/character.py", _patch_character_screen)
    patch_file("services/faction_starting.py", _patch_faction_starting)

    _migrate_tests()

    print("\n".join(LOG))
    err = [l for l in LOG if l.startswith("[ERROR]") or l.startswith("[WARN]")]
    if err:
        print("\n[!] Есть проблемы — см. выше.")
        return 1
    print("\nDONE — " + TAG)
    return 0


if __name__ == "__main__":
    sys.exit(main())