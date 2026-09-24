# PATCH_15W
# ui/screens/credits.py — создатели + благодарности тестерам и донатерам.
from __future__ import annotations

import streamlit as st

from ui.assets import sigil_svg
from ui.theme import _current


THANKS_NAMES = [
    "Ксения",
    "Анна",
    "Игорь",
    "Сергей",
    "Роман",
    "друзья Романа (кем бы вы ни были, ребят)",
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
.thanks-card {
    max-width: 640px; margin: 14px auto;
    padding: 18px 22px;
    border: 1px solid var(--accent);
    border-left: 3px solid var(--accent-soft);
    border-radius: 8px;
    background: rgba(255,255,255,0.02);
    text-align: left;
    color: var(--fg);
    font-family: Georgia, serif;
    line-height: 1.7;
}
.thanks-card .head {
    color: var(--accent-soft); letter-spacing: 4px;
    font-size: 12px; text-transform: uppercase;
    margin-bottom: 12px;
}
.thanks-card .lead {
    color: var(--fg); font-size: 14px;
    margin-bottom: 14px;
}
.thanks-card ul {
    list-style: none; padding: 0; margin: 8px 0 12px 0;
}
.thanks-card li {
    padding: 3px 0; color: var(--fg);
    border-bottom: 1px dashed rgba(255,255,255,0.05);
}
.thanks-card li:last-child { border-bottom: none; }
.thanks-card .tail {
    color: var(--fg-dim); font-size: 13px; font-style: italic;
    margin-top: 12px;
}
</style>'''


def _thanks_block():
    items = "".join("<li>" + str(n) + "</li>" for n in THANKS_NAMES)
    return (
        "<div class='thanks-card'>"
        "<div class='head'>БЛАГОДАРНОСТИ</div>"
        "<div class='lead'>"
        "Этот проект жив не благодаря нам. Он жив благодаря вам. "
        "Тем, кто тестировал ранние сборки, находил баги там, где "
        "их не должно было быть, и терпеливо писал нам, что опять "
        "сломалось. Тем, кто в полночь спорил с нашими решениями "
        "и оказывался прав. Тем, кто возвращался."
        "</div>"
        "<ul>" + items + "</ul>"
        "<div class='tail'>"
        "Адептус Механикус знает: даже в мрачной тьме далёкого "
        "будущего есть свет. Его зажигают те, кто рядом."
        "</div>"
        "</div>"
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
