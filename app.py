# PATCH_15Y_HARD_ROUTER
# app.py — точка входа и маршрутизация (HARD ROUTER + LANDING GUARD).

# PATCH_72: автораспаковка HF-кэша
def _ensure_hf_cache() -> None:
    import os
    import zipfile
    import json
    from pathlib import Path
    root = Path(__file__).resolve().parent
    hub_root = Path.home() / ".cache" / "huggingface" / "hub"
    model_dir = hub_root / "models--intfloat--multilingual-e5-small"
    snap_dir = model_dir / "snapshots"

    # Проверяем — есть ли уже модель
    if snap_dir.exists() and any(snap_dir.rglob("model.safetensors")):
        return

    manifest_path = root / "hf_cache_manifest.json"
    if not manifest_path.exists():
        print("[app] hf_cache_manifest.json не найден -> HF-кэш не распакуется")
        return

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        parts = manifest.get("parts", [])
        if not parts:
            return

        # Склеиваем части в один zip
        full_zip = root / "_hf_cache_assembled.zip"
        with open(full_zip, "wb") as out:
            for part in parts:
                pp = root / part
                if not pp.exists():
                    print(f"[app] Отсутствует часть {part} -> отказ")
                    return
                out.write(pp.read_bytes())

        # Распаковываем содержимое модели прямо в её папку
        model_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(full_zip, "r") as zf:
            zf.extractall(model_dir)

        # Удаляем временный zip
        try:
            full_zip.unlink()
        except Exception:
            pass

        print(f"[app] HF-кэш распакован: {model_dir}")
    except Exception as e:
        print(f"[app] HF cache error: {type(e).__name__}: {e}")


_ensure_hf_cache()
# /PATCH_72

# PATCH_66: offline-режим HuggingFace
# Не даём sentence-transformers / huggingface_hub ходить в сеть за моделью.
# Модель intfloat/multilingual-e5-small должна быть в локальном кэше
# (или подгружена рядом с chroma_db).
import os as _os
_os.environ.setdefault("HF_HUB_OFFLINE", "1")
_os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
# /PATCH_66


import streamlit as st

st.set_page_config(
    page_title="Warhammer 40K RPG",
    page_icon="XB",
    layout="wide",
)

# PATCH_65: автораспаковка chroma_db.zip
# Если папки chroma_db/ нет, но есть chroma_db.zip (для Streamlit Cloud),
# распаковываем её при старте приложения.
def _ensure_chroma_db() -> None:
    import os
    import zipfile
    root = os.path.dirname(os.path.abspath(__file__))
    db_dir = os.path.join(root, "chroma_db")
    zip_path = os.path.join(root, "chroma_db.zip")
    if os.path.isdir(db_dir) and os.listdir(db_dir):
        return  # база на месте
    if not os.path.isfile(zip_path):
        print("[app] chroma_db/ нет, chroma_db.zip нет -> RAG отключён")
        return
    try:
        size_mb = os.path.getsize(zip_path) / (1024 * 1024)
        print("[app] chroma_db.zip найден ({:.1f} МБ), распаковываю...".format(size_mb))
        os.makedirs(db_dir, exist_ok=True)
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(db_dir)
        n = sum(len(f) for _, _, f in os.walk(db_dir))
        print("[app] chroma_db/ распакован: {} файлов".format(n))
    except Exception as e:
        print("[app] распаковка chroma_db.zip упала: "
              + type(e).__name__ + ": " + str(e))


_ensure_chroma_db()
# /PATCH_65



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

# PATCH_33: применяем CSS-тему (свечения, градиенты, панели)
try:
    from ui.theme import apply_theme
    apply_theme()
    print('[app] apply_theme OK')
except Exception as _te:
    print('[app] apply_theme FAIL: '
          + type(_te).__name__ + ': ' + str(_te))
    import traceback
    traceback.print_exc()

from ui.screens import (  # noqa: E402
    splash, about, auth, onboarding, tutorial, wizard, game,
    kot_intro, tutorial_prompt, tutorial_help, loading,
    main_menu, loads, settings_screen, credits, progression,
    character, chronicles, combat, ship, market, library,
    game_settings, companions, achievements, journal,
    rituals, dreams, skills,
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
