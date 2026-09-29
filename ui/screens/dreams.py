# PATCH_30
"""ui/screens/dreams.py — сны и видения."""
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

    from persistence.characters import load_character, save_character
    try:
        char = load_character(login, char_name)
    except Exception as e:
        st.error("Ошибка: " + str(e))
        return

    from services.dreams import get_dream

    st.markdown("<h2 style='font-family:Georgia,serif;'>💭 Сон</h2>",
                unsafe_allow_html=True)
    c1, c2 = st.columns([3, 1])
    with c2:
        if st.button("← Назад", use_container_width=True):
            _goto("game")
            st.rerun()

    if "dream_text" not in st.session_state:
        st.session_state.dream_text = get_dream(char)

    st.markdown(
        "<div style='border:1px solid #333;border-left:3px solid #6b4a0a;"
        "border-radius:8px;padding:18px 24px;background:rgba(255,255,255,0.02);"
        "font-style:italic;color:#c8c0b0;font-size:15px;line-height:1.6;'>"
        + st.session_state.dream_text +
        "</div>",
        unsafe_allow_html=True,
    )

    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🔄 Другой сон", use_container_width=True):
            st.session_state.dream_text = get_dream(char)
            st.rerun()
    with c2:
        if st.button("💾 Записать в дневник", use_container_width=True):
            try:
                from services.journal import add_entry
                add_entry(char, "Сон: " + st.session_state.dream_text,
                          kind="dream")
                from services.effects import add_insanity
                add_insanity(char, 1, "тревожный сон")
                save_character(login, char_name, char)
                st.success("Записано в дневник. +1 Безумие.")
            except Exception as e:
                st.error(str(e))
