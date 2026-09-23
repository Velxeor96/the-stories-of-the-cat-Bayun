# PATCH_11_THEME_ALL_V2
'''ui/screens/splash.py — стартовый экран.'''
from __future__ import annotations

import streamlit as st

from ui.assets import sigil_svg
from ui.theme import _current


SPLASH_CSS = '''<style>
.splash-wrap {
    display: flex; flex-direction: column;
    align-items: center; justify-content: center;
    min-height: 70vh; text-align: center; padding: 40px 20px;
}
.splash-sigil {
    animation: fadeInUp 0.9s ease-out;
    filter: drop-shadow(0 0 30px var(--accent-glow));
}
.splash-title {
    font-family: Georgia, serif;
    font-size: 58px;
    letter-spacing: 8px;
    color: var(--fg);
    margin: 24px 0 8px 0;
    text-shadow: 0 0 30px var(--accent-glow), 0 0 60px var(--accent-glow);
    animation: fadeInUp 1.0s ease-out;
}
.splash-sub {
    color: var(--fg-dim);
    font-style: italic;
    font-size: 16px;
    letter-spacing: 3px;
    margin-bottom: 32px;
    animation: fadeInUp 1.2s ease-out;
}
.splash-divider {
    width: 200px; height: 1px;
    background: linear-gradient(90deg, transparent 0%,
        var(--accent) 50%, transparent 100%);
    margin: 12px 0 24px 0;
    opacity: 0.7;
}
.splash-quote {
    color: var(--fg-dim);
    font-family: Georgia, serif;
    font-style: italic;
    max-width: 620px;
    line-height: 1.7;
    font-size: 15px;
    animation: fadeInUp 1.4s ease-out;
}
</style>'''


def render() -> None:
    st.markdown(SPLASH_CSS, unsafe_allow_html=True)
    theme = _current()
    sigil = sigil_svg(theme, size=140)
    html = (
        "<div class='splash-wrap'>"
        f"<div class='splash-sigil'>{sigil}</div>"
        "<div class='splash-title'>WARHAMMER 40K</div>"
        "<div class='splash-sub'>ВОЛЬНЫЙ ТОРГОВЕЦ · АЛЬФА</div>"
        "<div class='splash-divider'></div>"
        "<div class='splash-quote'>"
        "&laquo;В мрачной тьме далёкого будущего есть только война. "
        "Но ты — не солдат. Ты — Вольный Торговец. Твой Потент подписан "
        "самим Императором. И завтра ты сам решишь, чьи миры будут "
        "гореть.&raquo;</div></div>"
    )
    st.markdown(html, unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        if st.button("▶  Войти", use_container_width=True, type="primary",
                     key="splash_enter"):
            st.session_state.screen = "auth"
            st.rerun()
        if st.button("📖  Об игре", use_container_width=True,
                     key="splash_about"):
            st.session_state.screen = "about"
            st.rerun()

    _legal_block()


def _legal_block() -> None:
    st.markdown("---")
    with st.expander("Правовая информация"):
        st.markdown(
            "Это **фанатский некоммерческий проект**, "
            "созданный из любви к вселенной Warhammer 40,000.\n\n"
            "Warhammer 40,000, Аквила, Адептус Механикус, "
            "Opus Machina, Т'ау, символы фракций, названия "
            "карьер и правил, а также все связанные торговые "
            "марки являются интеллектуальной собственностью "
            "**Games Workshop Ltd.** и соответствующих "
            "правообладателей.\n\n"
            "Проект:\n"
            "- не преследует коммерческих целей;\n"
            "- не приносит дохода;\n"
            "- не связан с Games Workshop Ltd.;\n"
            "- не претендует на чужую интеллектуальную "
            "собственность.\n\n"
            "Все права принадлежат их законным владельцам."
        )
