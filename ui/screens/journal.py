# PATCH_28
"""ui/screens/journal.py — дневник."""
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

    from services.journal import get_entries, add_entry, remove_entry

    st.markdown("<h2 style='font-family:Georgia,serif;'>📖 Дневник</h2>",
                unsafe_allow_html=True)
    c1, c2 = st.columns([3, 1])
    with c2:
        if st.button("← Назад", use_container_width=True):
            _goto("game")
            st.rerun()

    txt = st.text_area("Новая запись", key="jn_new", height=100)
    if st.button("Добавить запись", key="jn_add", type="primary"):
        if add_entry(char, txt, kind="manual"):
            save_character(login, char_name, char)
            st.rerun()

    entries = get_entries(char)
    if not entries:
        st.info("Дневник пуст.")
        return

    st.markdown("---")
    for i, e in enumerate(reversed(entries)):
        real_idx = len(entries) - 1 - i
        if not isinstance(e, dict):
            continue
        kind = e.get("kind", "note")
        marker = {"turn": "🎲", "note": "📝", "manual": "✍️"}.get(kind, "•")
        ts = e.get("ts", "")
        c1, c2 = st.columns([6, 1])
        with c1:
            st.caption(ts + " · " + marker)
            st.markdown(str(e.get("text", ""))[:1500])
        with c2:
            if st.button("✕", key="jn_rm_" + str(real_idx)):
                remove_entry(char, real_idx)
                save_character(login, char_name, char)
                st.rerun()
        st.markdown("---")
