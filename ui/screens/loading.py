# PATCH_16D
# ui/screens/loading.py — INITIATIO с фракционными фразами.
from __future__ import annotations

import random
import time

import streamlit as st

from ui.loading_screen import (
    full_css,
    full_html,
    get_phrases,
)


def _theme():
    try:
        from ui.theme import _current
        return _current()
    except Exception:
        return "dark"


def _finish():
    login = st.session_state.get("user_login")
    if login:
        try:
            from persistence.settings import set_setting
            set_setting(login, "loading_seen", True)
        except Exception as e:
            print("[loading] set_setting fail: "
                  + type(e).__name__ + ": " + str(e))
    st.session_state["_loading_anim_done"] = False
    st.session_state.screen = "main_menu"
    st.rerun()


def _run_animation():
    st.markdown(full_css(), unsafe_allow_html=True)
    placeholder = st.empty()
    theme = _theme()
    pool = get_phrases(theme)

    total_steps = 100
    dt = 0.1
    elapsed = 0.0
    phrase_idx = 0
    next_phrase_at = 0.0
    current = pool[0]

    for step in range(total_steps + 1):
        progress = int(step / total_steps * 100)
        if elapsed >= next_phrase_at:
            current = pool[phrase_idx % len(pool)]
            phrase_idx += 1
            next_phrase_at = elapsed + random.uniform(3.0, 5.0)
        placeholder.markdown(
            full_html(theme, progress, current),
            unsafe_allow_html=True,
        )
        time.sleep(dt)
        elapsed += dt

    st.session_state["_loading_anim_done"] = True
    st.rerun()


def render():
    login = st.session_state.get("user_login")
    if not login:
        st.warning("Нет активной сессии.")
        if st.button("На главную", key="loading_nologin"):
            st.session_state.screen = "splash"
            st.rerun()
        return

    if st.session_state.get("_loading_anim_done"):
        st.markdown(full_css(), unsafe_allow_html=True)
        st.markdown(
            full_html(_theme(), 100,
                      "> ДУХ-МАШИНЫ ГОТОВЫ К СЛУЖЕНИЮ."),
            unsafe_allow_html=True,
        )
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            if st.button("Продолжить", use_container_width=True,
                         type="primary", key="loading_continue"):
                _finish()
        return

    _run_animation()
