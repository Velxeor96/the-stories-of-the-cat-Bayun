# PATCH_28
"""ui/screens/achievements.py — достижения."""
from __future__ import annotations
import streamlit as st


def _goto(screen: str) -> None:
    st.session_state.screen = screen


def render() -> None:
    login = st.session_state.get("user_login")
    char_name = st.session_state.get("active_character")
    if not login or not char_name:
        _goto("main_menu")
        st.rerun()
        return

    from persistence.characters import load_character
    try:
        char = load_character(login, char_name)
    except Exception as e:
        st.error("Ошибка: " + str(e))
        return

    from services.achievements import all_with_status, check_all

    # обновить статусы перед показом
    check_all(char)

    st.markdown("<h2 style='font-family:Georgia,serif;'>🏆 Достижения</h2>",
                unsafe_allow_html=True)
    c1, c2 = st.columns([3, 1])
    with c2:
        if st.button("← Назад", use_container_width=True):
            _goto("game")
            st.rerun()

    items = all_with_status(char)
    unlocked = sum(1 for i in items if i["unlocked"])
    st.caption("Открыто: " + str(unlocked) + " / " + str(len(items)))

    for it in items:
        mark = "🏆" if it["unlocked"] else "🔒"
        color = "#d4a72c" if it["unlocked"] else "#888"
        st.markdown(
            "<div style='border:1px solid #333;border-radius:6px;"
            "padding:8px 12px;margin:4px 0;color:" + color + ";'>"
            + mark + " <b>" + it["name"] + "</b> — " + it["desc"]
            + "</div>",
            unsafe_allow_html=True)
