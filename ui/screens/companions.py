# PATCH_28
"""ui/screens/companions.py — компаньоны."""
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

    from services.companions import (
        get_companions, get_preset, add_companion, remove_companion,
    )

    st.markdown("<h2 style='font-family:Georgia,serif;'>👥 Компаньоны</h2>",
                unsafe_allow_html=True)
    c1, c2 = st.columns([3, 1])
    with c2:
        if st.button("← Назад", use_container_width=True):
            _goto("game")
            st.rerun()

    comp = get_companions(char)
    if comp:
        st.markdown("### Текущий состав")
        for i, c in enumerate(comp):
            if not isinstance(c, dict):
                continue
            c1, c2 = st.columns([5, 1])
            with c1:
                alive = "жив" if c.get("alive", True) else "мёртв"
                st.markdown(
                    "<div style='border:1px solid #333;border-radius:6px;"
                    "padding:8px 12px;margin:4px 0;'>"
                    "<b>" + str(c.get("name", "?")) + "</b> · "
                    + str(c.get("role", "?")) + " · "
                    + "HP " + str(c.get("hp", 0)) + "/"
                    + str(c.get("hp_max", 0)) + " · "
                    + str(c.get("weapon", "")) + " · <i>" + alive + "</i>"
                    + "</div>",
                    unsafe_allow_html=True)
            with c2:
                if st.button("✕", key="cmp_rm_" + str(i)):
                    remove_companion(char, i)
                    save_character(login, char_name, char)
                    st.rerun()
    else:
        st.info("Компаньонов нет. Возьми кого-нибудь из доступных по фракции.")

    st.markdown("### Доступные по фракции")
    fid = char.get("faction_id") or ""
    preset = get_preset(fid)
    if not preset:
        st.caption("Для этой фракции нет готовых компаньонов.")
    else:
        for p in preset:
            c1, c2 = st.columns([5, 1])
            with c1:
                st.markdown("**" + p["name"] + "** · " + p["role"]
                            + " · HP " + str(p["hp"])
                            + " · " + p["weapon"])
            with c2:
                if st.button("Взять", key="cmp_add_" + p["name"],
                             use_container_width=True):
                    add_companion(char, p["name"], p["role"],
                                  p["hp"], p["weapon"])
                    save_character(login, char_name, char)
                    st.rerun()
