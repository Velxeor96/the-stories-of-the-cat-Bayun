# PATCH_11_THEME_ALL_V2
'''ui/screens/about.py — экран 'Об игре'.'''
from __future__ import annotations

import streamlit as st

from ui.assets import sigil_svg
from ui.theme import _current


ABOUT_CSS = '''<style>
.about-wrap { max-width: 820px; margin: 24px auto; padding: 0 20px; }
.about-hero {
    text-align: center; padding: 20px 0 12px 0;
    animation: fadeInUp 0.7s ease-out;
}
.about-hero h1 {
    font-family: Georgia, serif; font-size: 40px; color: var(--fg);
    margin: 12px 0 0 0; letter-spacing: 3px;
    text-shadow: 0 0 24px var(--accent-glow);
}
.about-section {
    background: var(--panel); border: 1px solid var(--border);
    border-left: 3px solid var(--accent);
    border-radius: 12px;
    padding: 20px 26px; margin: 16px 0;
    color: var(--fg);
    box-shadow: 0 4px 14px var(--shadow);
    animation: fadeInUp 0.6s ease-out;
    transition: box-shadow 0.3s ease;
}
.about-section:hover {
    box-shadow: 0 8px 26px var(--shadow), 0 0 24px var(--accent-glow);
}
.about-section h3 {
    font-family: Georgia, serif; color: var(--accent);
    margin: 0 0 10px 0; letter-spacing: 1px; font-size: 18px;
}
.about-section p { margin: 0 0 10px 0; line-height: 1.7; }
.about-section ul { padding-left: 22px; margin: 8px 0; }
.about-section li { margin: 6px 0; line-height: 1.6; }
</style>'''


def render() -> None:
    st.markdown(ABOUT_CSS, unsafe_allow_html=True)
    theme = _current()
    sigil = sigil_svg(theme, size=96)

    st.markdown(
        f"<div class='about-hero'>{sigil}<h1>Об игре</h1></div>",
        unsafe_allow_html=True,
    )

    sections = [
        ("Что это",
         "<p>Настольная ролевая игра во вселенной Warhammer 40,000 — по "
         "правилам <b>Rogue Trader</b> (Fantasy Flight Games, 2009). "
         "Ты играешь за Вольного Торговца — аристократа, чей Потент "
         "подписан самим Императором. Ты можешь торговать, воевать, "
         "исследовать. Ты можешь решать судьбы миров.</p>"),
        ("Как это работает",
         "<p>Здесь три роли, и все три исполняет программа:</p><ul>"
         "<li><b>Мастер (GM)</b> — ведёт историю, описывает сцены, "
         "интерпретирует твои действия. За это отвечает нейросеть.</li>"
         "<li><b>Правила</b> — все броски кубов, пороги, ступени успеха "
         "считает Python. Никаких галлюцинаций с кубами.</li>"
         "<li><b>Модерация</b> — следит, чтобы ты играл в игру, а не "
         "разговаривал с ИИ о погоде.</li></ul>"),
        ("Что уже есть",
         "<ul>"
         "<li>6 сцен обучающего модуля <b>«Потент»</b> — от пробуждения "
         "до первого космического боя.</li>"
         "<li>Проверки d100: характеристики, навыки, модификаторы "
         "сложности, ступени успеха, критические исходы.</li>"
         "<li>Очки Судьбы, Очки Бедствия, Фактор Прибыли.</li>"
         "<li>Создание персонажа: раса, фракция, архетип, "
         "характеристики.</li>"
         "<li>RAG-база знаний — Мастер видит лор вселенной и не "
         "выдумывает локации.</li>"
         "<li>Три темы оформления — Нейтральная, Империум, Механикум.</li>"
         "</ul>"),
        ("Чего пока нет",
         "<ul>"
         "<li>Открытого мира — сейчас игра заканчивается на шестой сцене "
         "обучения.</li>"
         "<li>Инвентаря и экипировки в UI.</li>"
         "<li>Триггеров и событий (rules/wh40k_triggers.json — заглушка).</li>"
         "<li>Многопользовательского режима.</li></ul>"),
    ]
    for title, body in sections:
        st.markdown(
            f"<div class='about-section'><h3>{title}</h3>{body}</div>",
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        if st.button("←  Назад", use_container_width=True, key="about_back"):
            st.session_state.screen = "splash"
            st.rerun()
