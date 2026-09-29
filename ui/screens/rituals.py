# PATCH_30
"""ui/screens/rituals.py — ритуалы фракции."""
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

    from services.rituals import list_rituals, perform

    st.markdown("<h2 style='font-family:Georgia,serif;'>🕯 Ритуалы</h2>",
                unsafe_allow_html=True)
    c1, c2 = st.columns([3, 1])
    with c1:
        st.caption("Традиции фракции: " + str(char.get("faction", "?")))
    with c2:
        if st.button("← Назад", use_container_width=True):
            _goto("game")
            st.rerun()

    fid = char.get("faction_id") or ""
    rituals = list_rituals(fid)
    if not rituals:
        st.info("Для этой фракции ритуалы не описаны.")
        return

    for name, desc, kind in rituals:
        c1, c2 = st.columns([5, 1])
        with c1:
            st.markdown("**" + name + "** — " + desc)
        with c2:
            if st.button("Провести", key="rit_" + name,
                         use_container_width=True):
                res = perform(char, name)
                if res.get("ok"):
                    st.success(res.get("text", ""))
                    save_character(login, char_name, char)
                    st.rerun()
                else:
                    st.warning(res.get("text", ""))
