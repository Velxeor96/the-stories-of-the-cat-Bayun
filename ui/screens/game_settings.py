# PATCH_27
"""ui/screens/game_settings.py — настройки игрового процесса."""
from __future__ import annotations
import streamlit as st


def _goto(screen: str) -> None:
    st.session_state.screen = screen


def render() -> None:
    login = st.session_state.get("user_login")
    if not login:
        _goto("main_menu")
        st.rerun()
        return

    from services.settings_game import get_settings, save_settings

    st.markdown("<h2 style='font-family:Georgia,serif;'>⚙️ Настройки игры</h2>",
                unsafe_allow_html=True)
    c1, c2 = st.columns([3, 1])
    with c2:
        if st.button("← Назад", width="stretch"):
            _goto("game")
            st.rerun()

    cur = get_settings(login)

    st.markdown("### Длина ответа мастера")
    length = st.radio(
        "Насколько подробно мастер описывает сцену",
        options=["Короткий", "Средний", "Развёрнутый"],
        index=["Короткий", "Средний", "Развёрнутый"].index(
            cur.get("response_length", "Средний")),
        horizontal=True,
        key="gs_length",
    )

    st.markdown("### Летальность")
    leth = st.radio(
        "Насколько опасны бои",
        options=["Лёгкая", "Норма", "Хардкор"],
        index=["Лёгкая", "Норма", "Хардкор"].index(
            cur.get("lethality", "Норма")),
        horizontal=True,
        key="gs_leth",
    )
    st.caption("Влияет на XP-множитель и шанс травм.")

    st.markdown("### Частота случайных событий")
    chance = st.slider(
        "Шанс события на каждый ход (%)",
        min_value=0, max_value=50,
        value=int(cur.get("event_chance", 15)),
        step=5,
        key="gs_event",
    )

    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("💾 Сохранить", type="primary",
                     width="stretch", key="gs_save"):
            save_settings(login, {
                "response_length": length,
                "lethality": leth,
                "event_chance": chance,
            })
            st.success("Настройки сохранены.")
    with c2:
        if st.button("↺ Сбросить", width="stretch",
                     key="gs_reset"):
            save_settings(login, {
                "response_length": "Средний",
                "lethality": "Норма",
                "event_chance": 15,
            })
            st.success("Сброшено на значения по умолчанию.")
            st.rerun()
