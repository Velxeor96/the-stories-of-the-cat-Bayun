# PATCH_15H_HARD_ROUTER
# app.py — точка входа и маршрутизация (HARD ROUTER + LANDING GUARD).
import streamlit as st

st.set_page_config(
    page_title="Warhammer 40K RPG",
    page_icon="⚔️",
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
    main_menu, loads, settings_screen, credits,
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

    # Landing-guard: первый переход в сессию после логина всегда ведёт
    # на kot_intro / loading / main_menu — игнорируя "зависший" screen
    # из прошлой активности (например, wizard).
    if not st.session_state.get("_post_login_landed"):
        st.session_state["_post_login_landed"] = True
        if not _setting(login, "kot_intro_seen"):
            return _fix("kot_intro", "landing")
        return _fix("loading", "landing")

    if not _setting(login, "kot_intro_seen"):
        if screen != "kot_intro":
            return _fix("kot_intro", "first login")

    # PATCH_15T: loading_seen больше не учитывается — INITIATIO
    # всегда идёт через landing (см. выше).

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
    if st.button("← На главную"):
        st.session_state.screen = "splash"
        st.rerun()
