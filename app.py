# app.py — точка входа и маршрутизация (HARD ROUTER + LANDING GUARD).
import os as _os
_os.environ.setdefault("HF_HUB_OFFLINE", "1")
_os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

from scripts.bootstrap import init_project
init_project()

import streamlit as st

# PATCH_120: Кэширование тяжелой инициализации (выполняется 1 раз при старте)
@st.cache_resource
def _bootstrap_init():
    from scripts.bootstrap import init_project
    from persistence.db import init_db
    init_project()
    init_db()

_bootstrap_init()
# /PATCH_120


st.set_page_config(
    page_title="Warhammer 40K RPG",
    page_icon="XB",
    layout="wide",
)

from persistence.db import init_db
init_db()

st.markdown(
    """
    <link rel="manifest" href="/static/manifest.json">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    """,
    unsafe_allow_html=True
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
        st.session_state.screen = "main_menu"
        return
    try:
        from persistence.characters import list_characters
        names = list(list_characters(login))
        if active not in names:
            st.session_state.pop("active_character", None)
            st.session_state.screen = "main_menu"
    except Exception as e:
        print("[app] _force_reset check fail: " + str(e))

_force_reset()

try:
    from ui.theme import apply_theme
    apply_theme()
except Exception as _te:
    print('[app] apply_theme FAIL: ' + type(_te).__name__ + ': ' + str(_te))

from ui.screens import (
    splash, about, auth, onboarding, tutorial, wizard, game,
    kot_intro, tutorial_prompt, tutorial_help, loading,
    main_menu, loads, settings_screen, credits, progression,
    character, chronicles, combat, ship, market, library,
    game_settings, companions, achievements, journal,
    rituals, dreams, skills, psy,
)

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
    "combat": combat.render,
    "ship": ship.render,
    "progression": progression.render,
    "skills": skills.render,
    "market": market.render,
    "library": library.render,
    "loads": loads.render,
    "settings_screen": settings_screen.render,
    "credits": credits.render,
    "game_settings": game_settings.render,
    "companions": companions.render,
    "achievements": achievements.render,
    "journal": journal.render,
    "rituals": rituals.render,
    "dreams": dreams.render,
    "psy": psy.render_entry,
    "character": character.render,
}

from services.module_loader import get_manifest

_CAPABILITY_MAP = {
    "ship": "ship",
    "market": "trade",
    "psy": "psy",
    "combat": "combat",
}

def _filter_screens_by_capabilities():
    manifest = get_manifest()
    capabilities = set(manifest.get("capabilities", []))
    if not capabilities:
        return
    for screen, required_cap in _CAPABILITY_MAP.items():
        if required_cap not in capabilities and screen in SCREENS:
            del SCREENS[screen]
            print(f"[app] Экран '{screen}' отключен: нет capability '{required_cap}'")

_filter_screens_by_capabilities()

_PRELOGIN = {"splash", "auth"}

def _character_exists(login, name):
    if not name:
        return False
    try:
        from persistence.characters import list_characters
        return name in list(list_characters(login))
    except Exception:
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
