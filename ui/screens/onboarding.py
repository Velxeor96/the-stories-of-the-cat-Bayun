# PATCH_11_THEME_ALL_V2
'''ui/screens/onboarding.py — приветствие после первого входа.'''
from __future__ import annotations

import streamlit as st

from persistence.settings import set_setting
from ui.assets import sigil_svg
from ui.theme import _current


ONBOARDING_CSS = '''<style>
.ob-wrap { max-width: 820px; margin: 32px auto; padding: 0 20px; }
.ob-hero {
    text-align: center; padding: 20px 0 12px 0;
    animation: fadeInUp 0.7s ease-out;
}
.ob-hero h1 {
    font-family: Georgia, serif; font-size: 38px; color: var(--fg);
    margin: 12px 0 0 0; letter-spacing: 3px;
    text-shadow: 0 0 24px var(--accent-glow);
}
</style>'''


def _mark_seen(login: str) -> None:
    try:
        set_setting(login, "seen_onboarding", True)
    except Exception as e:
        print(f"[onboarding] set_setting: {e}")


def render() -> None:
    st.markdown(ONBOARDING_CSS, unsafe_allow_html=True)
    theme = _current()
    sigil = sigil_svg(theme, size=80)
    login = st.session_state.get("user_login", "путник")

    st.markdown(
        f"<div class='ob-wrap'><div class='ob-hero'>{sigil}"
        f"<h1>Добро пожаловать, {login}</h1></div></div>",
        unsafe_allow_html=True,
    )

    with st.expander("Что такое НРИ?", expanded=True):
        st.markdown(
            "**Настольная ролевая игра** — это когда несколько человек "
            "садятся за стол, один ведёт историю (Мастер), остальные "
            "играют за своих персонажей.\n\n"
            "Мастер описывает мир, ситуации, NPC. Игроки говорят, что "
            "делает их персонаж. Кубики решают, получилось ли задуманное. "
            "Получается история, которую никто не планировал заранее — "
            "она рождается прямо за столом.\n\n"
            "Здесь Мастер — не человек. Его играет искусственный "
            "интеллект. Ты пишешь свободным текстом, он отвечает сценой. "
            "Это работает очень похоже на живого Мастера."
        )
    with st.expander("Что такое Warhammer 40,000?"):
        st.markdown(
            "Сорок первое тысячелетие. Человечество растянулось по "
            "миллионам миров Галактики. Император сидит на Золотом Троне "
            "уже десять тысяч лет. За стенами Империума — хаос, ксеносы "
            "и Варп.\n\n"
            "Ты — не солдат Имперской Гвардии и не космодесантник. Ты — "
            "**Вольный Торговец**. Аристократ, чей Потент даёт право "
            "торговать и воевать за пределами Империума. Твои решения "
            "меняют судьбы миров."
        )
    with st.expander("Как играть (главное)"):
        st.markdown(
            "1. Пишешь, что делает твой персонаж — свободным текстом.\n"
            "2. Мастер решает, нужен ли бросок. Если да — Python бросает "
            "d100.\n"
            "3. Результат броска решает исход: успех, провал, критика.\n"
            "4. Мастер описывает, что произошло, и даёт варианты "
            "действий.\n\n"
            "**Максимум механик — Python. Мастер — только для истории.**"
        )
    with st.expander("Если что-то непонятно"):
        st.markdown(
            "Кнопка **🎓 Обучение** в сайдбаре откроет модуль «Потент» — "
            "6 сцен с объяснением всех механик. Пройди его один раз — "
            "дальше будет понятно."
        )

    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        if st.button("Начать  →", use_container_width=True,
                     type="primary", key="ob_start"):
            _mark_seen(login)
            st.session_state.screen = "splash"
            st.rerun()
        if st.button("Пропустить", use_container_width=True, key="ob_skip"):
            _mark_seen(login)
            st.session_state.screen = "splash"
            st.rerun()
