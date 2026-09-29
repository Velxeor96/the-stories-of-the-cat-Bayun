# PATCH_30B
"""ui/screens/skills.py — навыки персонажа."""
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

    st.markdown("<h2 style='font-family:Georgia,serif;'>🎓 Навыки</h2>",
                unsafe_allow_html=True)
    c1, c2 = st.columns([3, 1])
    with c2:
        if st.button("← Назад", use_container_width=True):
            _goto("game")
            st.rerun()

    skills = char.get("skills") or []
    if not skills:
        st.info("Пока навыков нет.")
    else:
        for s in skills:
            if isinstance(s, dict):
                nm = str(s.get("name") or s.get("title") or "навык")
                lvl = str(s.get("level") or "")
            else:
                nm = str(s)
                lvl = ""
            st.markdown("**" + nm + "**" + (" — " + lvl if lvl else ""))

    st.markdown("---")
    st.markdown("### Таланты")
    talents = char.get("talents") or []
    if not talents:
        st.caption("Талантов нет.")
    else:
        for t in talents:
            st.markdown("• " + str(t))

    st.markdown("---")
    st.markdown("### Психические силы")
    psy = char.get("psychic_powers") or []
    if not psy:
        st.caption("Пси-сил нет.")
    else:
        for p in psy:
            st.markdown("• " + str(p))
