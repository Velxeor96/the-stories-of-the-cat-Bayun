# PATCH_15I
# ui/screens/settings_screen.py — тема, логи, отладка, сброс вводного потока.
from __future__ import annotations

import json
import platform
from datetime import datetime
from pathlib import Path

import streamlit as st

from ui.theme import _current
from ui.version_info import get_current_version, get_changelog


def render() -> None:
    st.markdown(
        "<h2 style='font-family: Georgia, serif; letter-spacing: 5px; "
        "text-align: center;'>НАСТРОЙКИ</h2>",
        unsafe_allow_html=True,
    )

    tab_theme, tab_logs, tab_debug, tab_ver = st.tabs(
        ["Тема", "Логи", "Отладка", "История версий"]
    )

    with tab_theme:
        _tab_theme()
    with tab_logs:
        _tab_logs()
    with tab_debug:
        _tab_debug()
    with tab_ver:
        _tab_versions()

    st.markdown("---")
    if st.button("← В главное меню", key="settings_back"):
        st.session_state.screen = "main_menu"
        st.rerun()


def _tab_theme():
    st.write("Выберите тему оформления:")
    try:
        from ui.theme import render_theme_selector
        render_theme_selector()
    except Exception as e:
        st.error("Не удалось отрисовать выбор темы: "
                 + type(e).__name__ + ": " + str(e))


def _tab_logs():
    st.write("Состояние сессии:")
    snap = {}
    for k, v in st.session_state.items():
        try:
            json.dumps(v)
            snap[k] = v
        except Exception:
            snap[k] = repr(v)
    st.json(snap)

    st.write("История чата активного персонажа:")
    login = st.session_state.get("user_login")
    active = st.session_state.get("active_character")
    if not login or not active:
        st.info("Нет активного персонажа.")
        return
    try:
        from persistence.chats import load_history
        hist = load_history(login, active)
        st.write("Записей: " + str(len(hist or [])))
        st.json(hist or [])
    except Exception as e:
        st.warning("Не удалось загрузить историю: "
                   + type(e).__name__ + ": " + str(e))


def _tab_debug():
    st.write("Системная информация:")
    info = {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "time": datetime.now().isoformat(timespec="seconds"),
        "theme": str(_current()),
    }
    st.json(info)

    try:
        vf = Path("VERSION")
        if vf.exists():
            st.write("VERSION: " + vf.read_text(encoding="utf-8").strip())
        else:
            st.write("VERSION: файл не найден")
    except Exception as e:
        st.write("VERSION: н/д (" + type(e).__name__ + ")")

    st.markdown("---")
    st.write("Вводный поток (знакомство + загрузка):")
    st.caption(
        "Сбросит флаги kot_intro_seen и loading_seen для текущего акаунта. "
        "При следующем действии снова увидишь INITIATIO."
    )
    if st.button("Сбросить вводный поток", key="settings_reset_intro"):
        _reset_intro()


def _reset_intro():
    login = st.session_state.get("user_login")
    if not login:
        st.error("Нет активной сессии.")
        return
    try:
        from persistence.settings import set_setting
        set_setting(login, "kot_intro_seen", False)
        set_setting(login, "loading_seen", False)
    except Exception as e:
        st.error("Ошибка сброса: " + type(e).__name__ + ": " + str(e))
        return
    st.session_state.pop("_post_login_landed", None)
    st.session_state["screen"] = "kot_intro"
    st.success("Сброшено. Идём на kot_intro.")
    st.rerun()


def _tab_versions():
    st.write("Текущая версия: " + get_current_version())
    st.markdown("---")
    body = get_changelog()
    if body:
        st.markdown(body)
    else:
        st.caption("История изменений недоступна.")
