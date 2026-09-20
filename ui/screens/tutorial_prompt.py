# PATCH_11_THEME_ALL_V2
'''ui/screens/tutorial_prompt.py — предложение пройти обучение.'''
from __future__ import annotations

import streamlit as st

from persistence.settings import set_setting
from ui.assets import sigil_svg
from ui.theme import _current


PROMPT_CSS = '''<style>
.tp-wrap {
    max-width: 760px; margin: 50px auto 20px auto;
    text-align: center; padding: 0 20px;
    animation: fadeInUp 0.7s ease-out;
}
.tp-hero { text-align: center; padding: 12px 0 8px 0; }
.tp-title {
    font-family: Georgia, serif;
    font-size: 36px; color: var(--fg);
    margin: 14px 0 22px 0; letter-spacing: 2px;
    text-shadow: 0 0 20px var(--accent-glow);
}
.tp-text {
    color: var(--fg-dim);
    font-size: 16px; line-height: 1.8; font-style: italic;
    max-width: 620px; margin: 0 auto;
}
.tp-card {
    background: var(--panel);
    border: 1px solid var(--border-hi);
    border-radius: 14px;
    padding: 24px 28px;
    margin: 22px 0;
    box-shadow: 0 8px 28px var(--shadow), 0 0 40px var(--accent-glow);
    animation: fadeInUp 0.8s ease-out;
}
.tp-ornament {
    text-align: center; color: var(--accent);
    letter-spacing: 12px; font-size: 14px;
    margin: 26px 0; opacity: 0.65;
}
</style>'''


def _mark_tutorial_done() -> None:
    login = st.session_state.get("user_login")
    if login:
        try:
            set_setting(login, "seen_tutorial", True)
        except Exception as e:
            print(f"[tutorial_prompt] set_setting: {e}")


def render() -> None:
    st.markdown(PROMPT_CSS, unsafe_allow_html=True)
    theme = _current()
    sigil = sigil_svg(theme, size=72)

    st.markdown(
        f"<div class='tp-wrap'><div class='tp-hero'>{sigil}</div>"
        "<div class='tp-title'>Желаешь пройти обучение?</div>"
        "<div class='tp-card'><div class='tp-text'>"
        "Это короткий путь — всего 15–20 минут — который объяснит тебе, "
        "как устроена эта игра. Как бросать кубы. Как принимать решения. "
        "Как быть Вольным Торговцем."
        "</div></div></div>"
        "<div class='tp-ornament'>❦ ❦ ❦</div>",
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("ДА", use_container_width=True,
                     type="primary", key="tp_yes"):
            st.session_state.screen = "tutorial"
            st.rerun()
    with c2:
        if st.button("НЕТ", use_container_width=True, key="tp_no"):
            _mark_tutorial_done()
            st.session_state.screen = "wizard"
            st.rerun()
    with c3:
        if st.button("НЕ ЗНАЮ", use_container_width=True, key="tp_dunno"):
            st.session_state.screen = "tutorial_help"
            st.rerun()
