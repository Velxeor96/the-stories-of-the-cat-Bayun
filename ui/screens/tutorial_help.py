# PATCH_11_THEME_ALL_V2
'''ui/screens/tutorial_help.py — справка об обучении.'''
from __future__ import annotations

import streamlit as st

from persistence.settings import set_setting
from ui.assets import sigil_svg
from ui.theme import _current


HELP_CSS = '''<style>
.th-wrap { max-width: 800px; margin: 40px auto; padding: 0 20px; }
.th-hero {
    text-align: center; padding: 12px 0 8px 0;
    animation: fadeInUp 0.7s ease-out;
}
.th-title {
    font-family: Georgia, serif; font-size: 30px; color: var(--fg);
    text-align: center; margin: 14px 0 24px 0; letter-spacing: 2px;
    text-shadow: 0 0 20px var(--accent-glow);
}
.th-body {
    background: var(--panel);
    border: 1px solid var(--border-hi);
    border-left: 3px solid var(--accent);
    border-radius: 12px;
    padding: 26px 32px;
    color: var(--fg);
    font-size: 15px; line-height: 1.8;
    box-shadow: 0 8px 28px var(--shadow), 0 0 30px var(--accent-glow);
    animation: fadeInUp 0.8s ease-out;
}
.th-body p { margin: 0 0 14px 0; }
.th-body ul { margin: 10px 0 16px 0; padding-left: 24px; }
.th-body li { margin: 6px 0; }
.th-body b { color: var(--accent-soft); }
</style>'''


def _mark_tutorial_done() -> None:
    login = st.session_state.get("user_login")
    if login:
        try:
            set_setting(login, "seen_tutorial", True)
        except Exception as e:
            print(f"[tutorial_help] set_setting: {e}")


def render() -> None:
    st.markdown(HELP_CSS, unsafe_allow_html=True)
    theme = _current()
    sigil = sigil_svg(theme, size=64)

    st.markdown(
        f"<div class='th-wrap'><div class='th-hero'>{sigil}</div>"
        "<div class='th-title'>Об обучении</div>"
        "<div class='th-body'>"
        "<p>Обучение — это короткий интерактивный модуль. Он не "
        "обязателен, но крайне полезен.</p>"
        "<p><b>Что ты узнаешь:</b></p><ul>"
        "<li>Как работают проверки навыков (бросок d100).</li>"
        "<li>Что такое характеристики и навыки персонажа.</li>"
        "<li>Как проходят бои — и наземные, и космические.</li>"
        "<li>Что такое Очки Судьбы и как их использовать.</li>"
        "<li>Что такое Фактор Прибыли и как он решает проблемы.</li>"
        "<li>Как устроен мир Warhammer 40,000 — и кто такие "
        "Вольные Торговцы.</li></ul>"
        "<p>Обучение длится 15–20 минут. В нём ты играешь за одного "
        "из двух предсозданных персонажей. После обучения ты сможешь "
        "создать своего собственного героя и выйти в открытый мир.</p>"
        "<p><b>Начать обучение?</b></p>"
        "</div></div>",
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns(2)
    with c1:
        if st.button("НАЧАТЬ ОБУЧЕНИЕ", use_container_width=True,
                     type="primary", key="th_start"):
            st.session_state.screen = "tutorial"
            st.rerun()
    with c2:
        if st.button("ПРОПУСТИТЬ ОБУЧЕНИЕ", use_container_width=True,
                     key="th_skip"):
            _mark_tutorial_done()
            st.session_state.screen = "wizard"
            st.rerun()
