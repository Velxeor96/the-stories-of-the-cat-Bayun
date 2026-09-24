# scripts/patch.py
# PATCH_15Y — XP-модель, kot_intro после каждого логина,
# кнопка "Развитие" из главного меню в сайдбар игры,
# стартовый XP=300, подключение progression в роутер.
# Запуск: python scripts\patch.py
from __future__ import annotations

import ast
import shutil
import sys
from pathlib import Path

TAG = "PATCH_15Y"
ROOT = Path(__file__).resolve().parent.parent
FILES: dict = {}
REPLACEMENTS: list = []


FILES["VERSION"] = "1.4.0\n"


FILES["app.py"] = r"""# PATCH_15Y_HARD_ROUTER
# app.py — точка входа и маршрутизация (HARD ROUTER + LANDING GUARD).
import streamlit as st

st.set_page_config(
    page_title="Warhammer 40K RPG",
    page_icon="XB",
    layout="wide",
)

if "screen" not in st.session_state:
    st.session_state.screen = "splash"


def _force_reset():
    screen = st.session_state.get("screen")
    if screen != "game":
        return
    login = st.session_state.get("user_login")
    active = st.session_state.get("active_character")
    if not login:
        st.session_state.screen = "splash"
        return
    if not active:
        print("[app] _force_reset: game без персонажа -> main_menu")
        st.session_state.screen = "main_menu"
        return
    try:
        from persistence.characters import list_characters
        names = list(list_characters(login))
        if active not in names:
            print("[app] _force_reset: " + repr(active) + " не найден -> main_menu")
            st.session_state.pop("active_character", None)
            st.session_state.screen = "main_menu"
    except Exception as e:
        print("[app] _force_reset check fail: " + str(e))


_force_reset()

from ui.screens import (  # noqa: E402
    splash, about, auth, onboarding, tutorial, wizard, game,
    kot_intro, tutorial_prompt, tutorial_help, loading,
    main_menu, loads, settings_screen, credits, progression,
)

try:
    from ui.theme import apply_theme  # noqa: E402
    apply_theme()
except Exception as _e:
    print("[app] apply_theme failed: " + type(_e).__name__ + ": " + str(_e))
    import traceback
    traceback.print_exc()

SCREENS = {
    "splash": splash.render,
    "about": about.render,
    "auth": auth.render,
    "onboarding": onboarding.render,
    "kot_intro": kot_intro.render,
    "loading": loading.render,
    "main_menu": main_menu.render,
    "tutorial_prompt": tutorial_prompt.render,
    "tutorial_help": tutorial_help.render,
    "tutorial": tutorial.render,
    "wizard": wizard.render,
    "game": game.render,
    "loads": loads.render,
    "settings_screen": settings_screen.render,
    "credits": credits.render,
    "progression": progression.render,
}

_PRELOGIN = {"splash", "auth"}


def _setting(login, key, default=False):
    try:
        from persistence.settings import get_setting
        return bool(get_setting(login, key, default))
    except Exception as e:
        print("[app] _setting(" + key + "): " + type(e).__name__ + ": " + str(e))
        return default


def _character_exists(login, name):
    if not name:
        return False
    try:
        from persistence.characters import list_characters
        return name in list(list_characters(login))
    except Exception as e:
        print("[app] _character_exists: " + str(e))
        return False


def _resolve_screen():
    screen = st.session_state.get("screen", "splash")
    login = st.session_state.get("user_login")

    def _fix(new_screen, why):
        if new_screen != screen:
            print("[app] " + repr(screen) + " -> " + repr(new_screen) + " (" + why + ")")
            st.session_state.screen = new_screen
        return new_screen

    if not login:
        if screen not in ("splash", "auth", "about"):
            return _fix("splash", "no login")
        return screen

    # Landing: при каждом НОВОМ логине ведём на kot_intro.
    # Повторные rerun'ы в той же сессии уже помечены.
    landed_for = st.session_state.get("_post_login_landed_for", "")
    if landed_for != login:
        st.session_state["_post_login_landed_for"] = login
        return _fix("kot_intro", "landing")

    if screen in _PRELOGIN:
        return _fix("main_menu", "post-login")

    if screen == "game":
        active = st.session_state.get("active_character")
        if not active:
            return _fix("main_menu", "no active_character")
        if not _character_exists(login, active):
            st.session_state.pop("active_character", None)
            return _fix("main_menu", "character missing")

    if screen == "wizard" and not login:
        return _fix("splash", "wizard needs login")

    return screen


screen = _resolve_screen()
if screen in SCREENS:
    SCREENS[screen]()
else:
    st.warning("Неизвестный экран: " + repr(screen))
    if st.button("На главную"):
        st.session_state.screen = "splash"
        st.rerun()
"""


FILES["CHANGELOG.md"] = r"""# Changelog

Все значимые изменения проекта «Истории Кота Баюна».

## [1.4.0] — 2026-09-24

### Added

- **Мастер выдаёт XP за победу.** Победа над врагом в бою даёт:
  мелкий — 10, средний — 25, крупный — 35, великий
  (демон, лорд Хаоса) — 50. Инструкция встроена в user-message
  Мастера, не в промпт-файл.
- **Стартовый XP = 300** при создании персонажа. Хватает ровно
  на одно улучшение (навык, талант или +5 характеристики).
- **`progression` подключён к роутеру.** Кнопка «Развитие» теперь
  ведёт на экран прокачки.

### Changed

- **Кнопка «Развитие» переехала** из главного меню в сайдбар игры.
  Игроку удобнее открывать прокачку прямо во время сессии.
- **Приветствие Кота Баюна при каждом логине.** Landing-guard
  запоминает логин (`_post_login_landed_for`), а не факт «уже
  видел». Каждый вход в аккаунт — `kot_intro → loading → main_menu`.

### Fixed

- Кнопка «Развитие» в главном меню больше не ведёт в пустоту
  (`progression` не был подключён к `app.py`).

## [1.3.1] — 2026-09-24

### Fixed

- Убраны буквенные префиксы тем.
- PNG-сиглы перечитываются при изменении файла на диске.

## [1.3.0] — 2026-09-24

### Added

- Секретные темы (код «АЛЬФА»): Тзинч, Кхорн, Нургл, Слаанеш,
  Инквизиция, Альфа Легион.
- Раздел «Секретные протоколы Механикум» в настройках.
- Бейдж-титул рядом с ником в главном меню.
- Блок благодарностей на экране «Создатели».

## [1.2.0] — 2026-09-23

### Added

- Тема «Хаос».

## [1.1.0] — 2026-09-23

### Added

- Сиглы фракций из PNG / SVG.
- Правовая плашка на splash.
- Экран «Что нового» + CHANGELOG в настройках.
- Прокачка Rogue Trader.
- Сайдбар игры: локация, полоски, экипировка, оружие, навыки.
- Экран INITIATIO.

## [1.0.0] — 2026-09-23

Первый полноценный релиз.
"""


# Точечные правки через anchor
REPLACEMENTS.append((
    "main_menu",
    '        if st.button("Развитие", use_container_width=True,\n'
    '                     key="menu_progression"):\n'
    '            st.session_state.screen = "progression"\n'
    '            st.rerun()\n\n',
    '',
))

REPLACEMENTS.append((
    "game_btn",
    '        if st.button("Обучение", use_container_width=True, key="game_tut"):',
    '        if st.button("Развитие", use_container_width=True,\n'
    '                     key="game_progression"):\n'
    '            st.session_state.screen = "progression"\n'
    '            st.rerun()\n'
    '        if st.button("Обучение", use_container_width=True, key="game_tut"):',
))

REPLACEMENTS.append((
    "wizard_xp",
    '            save_character(login, name.strip(), data)',
    '            if int(data.get("xp", 0) or 0) == 0:\n'
    '                data["xp"] = 300\n'
    '            save_character(login, name.strip(), data)',
))

REPLACEMENTS.append((
    "master_xp",
    '        return "\\n\\n".join(parts)',
    '        parts.append(\n'
    '            "=== ИНСТРУКЦИЯ ПО ОПЫТУ (XP) ===\\n"\n'
    '            "Если игрок победил врага в бою (убил, обратил в бегство, "\n'
    '            "обезвредил), добавь в [STATE] строку:\\n"\n'
    '            "  xp=+10  за мелкого врага\\n"\n'
    '            "  xp=+25  за среднего\\n"\n'
    '            "  xp=+35  за крупного\\n"\n'
    '            "  xp=+50  за великого (демон, лорд Хаоса)\\n"\n'
    '            "В остальных случаях XP НЕ выдавай."\n'
    '        )\n'
    '        return "\\n\\n".join(parts)',
))


def _write_one(rel_path, content):
    dst = ROOT / rel_path
    dst.parent.mkdir(parents=True, exist_ok=True)
    existed = dst.exists()
    if existed:
        try:
            old = dst.read_text(encoding="utf-8")
        except Exception as e:
            return "ERROR reading: " + type(e).__name__ + ": " + str(e)
        if old == content:
            return "skip (identical)"
    if dst.suffix == ".py":
        try:
            ast.parse(content)
        except SyntaxError as e:
            return ("ERROR SyntaxError: line " + str(e.lineno)
                    + ": " + str(e.msg))
    if existed:
        bak = dst.with_name(dst.name + ".bak_pre_" + TAG)
        try:
            shutil.copy2(dst, bak)
        except Exception as e:
            return "ERROR backup: " + type(e).__name__ + ": " + str(e)
    try:
        dst.write_text(content, encoding="utf-8")
    except Exception as e:
        return "ERROR write: " + type(e).__name__ + ": " + str(e)
    return "backup + overwrite" if existed else "create"


def _apply_anchor(tag, rel_path, old_sub, new_sub):
    p = ROOT / rel_path
    if not p.exists():
        return "ERROR: file not found: " + rel_path
    try:
        src = p.read_text(encoding="utf-8")
    except Exception as e:
        return "ERROR read: " + type(e).__name__ + ": " + str(e)

    if old_sub not in src:
        if new_sub and new_sub in src:
            return "skip (already patched)"
        return "skip (anchor not found)"

    new_src = src.replace(old_sub, new_sub, 1)
    if new_src == src:
        return "skip (no changes)"

    if p.suffix == ".py":
        try:
            ast.parse(new_src)
        except SyntaxError as e:
            return ("ERROR SyntaxError: line " + str(e.lineno)
                    + ": " + str(e.msg))

    bak = p.with_name(p.name + ".bak_pre_" + TAG)
    try:
        shutil.copy2(p, bak)
    except Exception as e:
        return "ERROR backup: " + type(e).__name__ + ": " + str(e)
    try:
        p.write_text(new_src, encoding="utf-8")
    except Exception as e:
        return "ERROR write: " + type(e).__name__ + ": " + str(e)
    return "patched"


ANCHOR_FILES = {
    "main_menu": "ui/screens/main_menu.py",
    "game_btn": "ui/screens/game.py",
    "wizard_xp": "ui/screens/wizard.py",
    "master_xp": "services/master.py",
}


def main():
    print("=" * 64)
    print("PATCH " + TAG + " — XP, kot_intro, кнопка Развитие")
    print("ROOT: " + str(ROOT))
    print("=" * 64)

    any_error = False

    print("[1/2] Перезапись файлов:")
    for rel in FILES:
        status = _write_one(rel, FILES[rel])
        if status.startswith("ERROR"):
            any_error = True
        print("  " + rel.ljust(28) + " -> " + status)

    print("[2/2] Точечные правки:")
    for tag, old_s, new_s in REPLACEMENTS:
        rel = ANCHOR_FILES.get(tag, "?")
        status = _apply_anchor(tag, rel, old_s, new_s)
        if status.startswith("ERROR"):
            any_error = True
        print("  " + tag.ljust(28) + " -> " + status)

    print("=" * 64)
    print("DONE" + (" (with errors)" if any_error else " — ok"))
    return 1 if any_error else 0


if __name__ == "__main__":
    sys.exit(main())