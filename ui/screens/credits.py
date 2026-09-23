# PATCH_15H
# ui/screens/credits.py — создатели + благодарности тестерам.
from __future__ import annotations

import streamlit as st

from ui.assets import sigil_svg
from ui.theme import _current


# Впиши имена тестеров в список TESTERS. Пример:
#     TESTERS = ["Адепт Иван", "Сестра Анна", "Магос Пётр"]
# Если список пуст — рендерится общая благодарность.
TESTERS = [
]


CREDITS_CSS = '''<style>
.credits-wrap { text-align: center; padding: 22px 20px; }
.credits-title {
    font-family: Georgia, serif;
    font-size: 40px; letter-spacing: 6px;
    color: var(--fg);
    text-shadow: 0 0 24px var(--accent-glow);
    margin: 12px 0 6px 0;
}
.credits-sub {
    color: var(--fg-dim); font-style: italic;
    font-size: 14px; letter-spacing: 3px;
    margin-bottom: 22px;
}
.credits-card {
    max-width: 640px; margin: 10px auto;
    padding: 16px 22px;
    border: 1px solid var(--accent);
    border-radius: 8px;
    background: rgba(255,255,255,0.03);
    text-align: left;
    color: var(--fg);
}
.credits-card .row {
    display: flex; justify-content: space-between;
    padding: 6px 0;
    border-bottom: 1px solid rgba(255,255,255,0.06);
}
.credits-card .row:last-child { border-bottom: none; }
.credits-card .role { color: var(--fg-dim); }
.credits-card .who { color: var(--fg); font-weight: 600; }
.credits-card .quote {
    color: var(--fg-dim);
    font-style: italic;
    font-family: Georgia, serif;
    text-align: center;
    margin-top: 12px;
}
.credits-thanks {
    max-width: 640px; margin: 12px auto;
    padding: 14px 22px;
    border: 1px solid var(--accent);
    border-radius: 8px;
    background: rgba(255,255,255,0.02);
    text-align: left;
    color: var(--fg);
}
.credits-thanks .head {
    color: var(--fg-dim); letter-spacing: 3px;
    font-size: 12px; margin-bottom: 8px;
}
.credits-thanks .names { color: var(--fg); }
</style>'''


def _thanks_block():
    if TESTERS:
        names = ", ".join(str(n) for n in TESTERS)
    else:
        names = "адепты, чьи имена сокрыты за печатями Механикум"
    return (
        "<div class='credits-thanks'>"
        + "<div class='head'>БЛАГОДАРНОСТИ · ТЕСТЕРЫ</div>"
        + "<div class='names'>" + names + "</div>"
        + "</div>"
    )


def render():
    st.markdown(CREDITS_CSS, unsafe_allow_html=True)
    theme = _current()
    sigil = sigil_svg(theme, size=100)

    html = (
        "<div class='credits-wrap'>"
        + "<div>" + sigil + "</div>"
        + "<div class='credits-title'>СОЗДАТЕЛИ</div>"
        + "<div class='credits-sub'>те, кто шьёт судьбы</div>"
        + "<div class='credits-card'>"
        + "<div class='row'><span class='role'>Идея и код</span>"
        + "<span class='who'>Кот Баюн (Velxeor96)</span></div>"
        + "<div class='row'><span class='role'>Хранитель лора</span>"
        + "<span class='who'>Мастер Игры</span></div>"
        + "<div class='row'><span class='role'>Библиотека</span>"
        + "<span class='who'>Архивы Терры</span></div>"
        + "<div class='row'><span class='role'>Движок</span>"
        + "<span class='who'>GigaChat · Streamlit · ChromaDB</span></div>"
        + "<div class='quote'>&laquo;В мрачной тьме далёкого будущего "
        + "есть только война. Но истории — вечны.&raquo;</div>"
        + "</div>"
        + _thanks_block()
        + "</div>"
    )
    st.markdown(html, unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        if st.button("← В главное меню", use_container_width=True,
                     key="credits_back"):
            st.session_state.screen = "main_menu"
            st.rerun()
