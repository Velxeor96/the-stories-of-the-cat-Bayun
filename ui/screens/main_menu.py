# PATCH_15F
# ui/screens/main_menu.py — главное меню (7 кнопок).
from __future__ import annotations

import streamlit as st
from ui.version_info import (
    get_current_version,
    get_changelog_top,
    mark_version_seen,
    has_seen_current,
)

from ui.assets import sigil_svg
from ui.theme import _current, render_theme_selector


MENU_CSS = '''<style>
.menu-wrap {
    display: flex; flex-direction: column;
    align-items: center; justify-content: center;
    text-align: center; padding: 24px 20px 8px 20px;
}
.menu-sigil {
    filter: drop-shadow(0 0 24px var(--accent-glow));
    margin-bottom: 10px;
}
.menu-title {
    font-family: Georgia, serif;
    font-size: 44px; letter-spacing: 6px;
    color: var(--fg);
    text-shadow: 0 0 24px var(--accent-glow);
    margin: 8px 0 4px 0;
}
.menu-sub {
    color: var(--fg-dim); font-style: italic;
    letter-spacing: 3px; font-size: 14px;
    margin-bottom: 16px;
}
.menu-char {
    color: var(--fg-dim); font-size: 14px;
    border: 1px solid var(--accent);
    border-radius: 6px;
    padding: 6px 14px;
    margin-bottom: 18px;
    background: rgba(255,255,255,0.03);
}
.menu-char b { color: var(--fg); }
</style>'''


def render() -> None:
    _maybe_show_changelog()
    _theme_strip()
    if st.session_state.get("_show_changelog_dialog"):
        _show_changelog_now()
    st.markdown(MENU_CSS, unsafe_allow_html=True)
    theme = _current()
    sigil = sigil_svg(theme, size=90)

    login = st.session_state.get("user_login") or "—"
    names, last = _info()

    active = st.session_state.get("active_character")
    if active and active in names:
        display = active
    elif last and last in names:
        display = last
    else:
        display = None

    if display:
        char_line = ("<div class='menu-char'>Активный персонаж: <b>"
                     + str(display) + "</b></div>")
    else:
        char_line = ("<div class='menu-char'>"
                     "Персонаж не выбран</div>")

    html = (
        "<div class='menu-wrap'>"
        + "<div class='menu-sigil'>" + sigil + "</div>"
        + "<div class='menu-title'>CAT BAYUN</div>"
        + "<div class='menu-sub'>" + str(login) + "</div>"
        + char_line
        + "</div>"
    )
    st.markdown(html, unsafe_allow_html=True)

    can_continue = bool(names)
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        if st.button("Продолжить",
                     use_container_width=True, type="primary",
                     key="menu_continue",
                     disabled=not can_continue):
            _continue()
        if not can_continue:
            st.caption("Нет персонажей. Создайте первого в разделе «Новая игра».")

        if st.button("Новая игра", use_container_width=True,
                     key="menu_new"):
            st.session_state.pop("active_character", None)
            st.session_state.screen = "wizard"
            st.rerun()

        if st.button("Обучение", use_container_width=True,
                     key="menu_tutorial"):
            st.session_state.screen = "tutorial_prompt"
            st.rerun()

        if st.button("Загрузки", use_container_width=True,
                     key="menu_loads"):
            st.session_state.screen = "loads"
            st.rerun()

        if st.button("Что нового в " + get_current_version(),
                     use_container_width=True,
                     key="menu_whats_new"):
            st.session_state["_show_changelog_dialog"] = True
            st.rerun()

        if st.button("Настройки", use_container_width=True,
                     key="menu_settings"):
            st.session_state.screen = "settings_screen"
            st.rerun()

        if st.button("Создатели", use_container_width=True,
                     key="menu_credits"):
            st.session_state.screen = "credits"
            st.rerun()

        if st.button("Выход", use_container_width=True,
                     key="menu_exit"):
            _logout()


def _info():
    login = st.session_state.get("user_login")
    if not login:
        return [], None
    names = []
    try:
        from persistence.characters import list_characters
        names = list(list_characters(login))
    except Exception as e:
        print("[main_menu] list_characters fail: "
              + type(e).__name__ + ": " + str(e))
    last = None
    try:
        from persistence.settings import get_setting
        last = get_setting(login, "last_character", None)
    except Exception as e:
        print("[main_menu] get_setting fail: "
              + type(e).__name__ + ": " + str(e))
    if last not in names:
        last = names[0] if names else None
    return names, last


def _continue() -> None:
    login = st.session_state.get("user_login")
    if not login:
        return
    names, last = _info()
    if not names:
        return
    name = last or names[0]
    try:
        from persistence.characters import load_character
        char = load_character(login, name)
    except Exception as e:
        st.error("Ошибка загрузки: " + type(e).__name__ + ": " + str(e))
        return
    if not char:
        st.error("Не удалось загрузить персонажа: " + str(name))
        return
    st.session_state.active_character = name
    try:
        from persistence.settings import set_setting
        set_setting(login, "last_character", name)
    except Exception as e:
        print("[main_menu] set_setting fail: "
              + type(e).__name__ + ": " + str(e))
    st.session_state.screen = "game"
    st.rerun()


def _logout() -> None:
    keys = list(st.session_state.keys())
    for k in keys:
        if k == "screen":
            continue
        try:
            del st.session_state[k]
        except Exception:
            pass
    st.session_state.screen = "splash"
    st.rerun()


def _theme_strip() -> None:
    from ui.theme import THEMES
    keys = list(THEMES.keys())
    cur = _current()
    try:
        idx = keys.index(cur)
    except ValueError:
        idx = 0
    choice = st.radio(
        "Тема",
        options=keys,
        index=idx,
        format_func=lambda k: THEMES[k]["icon"] + " " + THEMES[k]["label"],
        horizontal=True,
        key="_main_menu_theme_pick",
        label_visibility="collapsed",
    )
    if choice != cur:
        st.session_state.ui_theme = choice
        st.rerun()


def _maybe_show_changelog() -> None:
    login = st.session_state.get("user_login")
    if not login:
        return
    if has_seen_current(login):
        return
    st.session_state["_show_changelog_dialog"] = True


def _show_changelog_now() -> None:
    _changelog_dialog()


@st.dialog("Что нового")
def _changelog_dialog() -> None:
    st.markdown("### Версия " + get_current_version())
    body = get_changelog_top()
    if body:
        st.markdown(body)
    else:
        st.caption("История изменений недоступна.")
    if st.button("Понятно", key="dlg_changelog_ok",
                 type="primary", use_container_width=True):
        login = st.session_state.get("user_login")
        if login:
            mark_version_seen(login)
        st.session_state.pop("_show_changelog_dialog", None)
        st.rerun()
