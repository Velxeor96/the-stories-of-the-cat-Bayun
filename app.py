# PATCH_11_COMPAT_V8

'''app.py — точка входа и маршрутизация (V8).'''
import streamlit as st

st.set_page_config(
    page_title="Warhammer 40K RPG",
    page_icon="⚔️",
    layout="wide",
)

if "screen" not in st.session_state:
    st.session_state.screen = "splash"

from ui.screens import (  # noqa: E402
    splash, about, auth, onboarding, tutorial, wizard, game,
    kot_intro, tutorial_prompt, tutorial_help,
)
from ui.theme import apply_theme  # noqa: E402

apply_theme()

SCREENS = {
    "splash": splash.render,
    "about": about.render,
    "auth": auth.render,
    "onboarding": onboarding.render,
    "kot_intro": kot_intro.render,
    "tutorial_prompt": tutorial_prompt.render,
    "tutorial_help": tutorial_help.render,
    "tutorial": tutorial.render,
    "wizard": wizard.render,
    "game": game.render,
}


def _setting(login, key, default=False):
    try:
        from persistence.settings import get_setting
        return bool(get_setting(login, key, default))
    except Exception:
        return default


def _has_any_character(login):
    try:
        from persistence.characters import has_any
        return bool(has_any(login))
    except Exception:
        return False


def _resolve_screen():
    '''Главный роутер. Решает, какой экран показать прямо сейчас.'''
    screen = st.session_state.get("screen", "splash")
    login = st.session_state.get("user_login")

    # --- НЕ залогинен ---
    if not login:
        if screen not in ("splash", "auth", "about"):
            return "splash"
        return screen

    # --- Залогинен ---
    # Онбординг (необязательный) — если ещё не видел, показать 1 раз
    if screen == "onboarding":
        if not _setting(login, "seen_onboarding"):
            return "onboarding"
        st.session_state.screen = "wizard"
        screen = "wizard"

    # Если сидит на login-экранах после успешного логина — гоним дальше
    if screen in ("splash", "auth", "about"):
        screen = "wizard"

    # Первый раз: Кот Баюн
    if not _setting(login, "kot_intro_seen"):
        return "kot_intro"

    # Второй раз: предложение обучения
    if not _setting(login, "seen_tutorial"):
        return "tutorial_prompt"

    # Всё видел — решаем по наличию персонажа
    if screen in ("wizard", "game"):
        if not _has_any_character(login):
            return "wizard"
        return "game"

    # Пропускаем как есть
    if screen in SCREENS:
        return screen

    # Фолбэк
    return "wizard"


screen = _resolve_screen()
if screen in SCREENS:
    SCREENS[screen]()
else:
    st.warning(f"Неизвестный экран: {screen!r}")
    if st.button("← На главную"):
        st.session_state.screen = "splash"
        st.rerun()
