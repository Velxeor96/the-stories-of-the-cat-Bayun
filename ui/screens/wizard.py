"""ui/screens/wizard.py — создание персонажа."""
import random

import streamlit as st

from persistence.characters import (
    CharacterError,
    list_characters,
    load_character,
    save_character,
)
from services.character_creation import build_character, roll_characteristics
from services.fallbacks import (
    CHARACTERISTIC_KEYS,
    CHARACTERISTIC_NAMES,
    FACTIONS,
    SUBFACTION_NAMES,
)


def _goto(screen: str) -> None:
    st.session_state.screen = screen
    st.rerun()


def _logout() -> None:
    for k in ("user_login", "wizard_data", "active_character"):
        st.session_state.pop(k, None)
    _goto("splash")


def _existing_block(login: str) -> None:
    chars = list_characters(login)
    if not chars:
        return

    with st.expander(f"У меня уже есть персонажи ({len(chars)})", expanded=False):
        for name in chars:
            c1, c2 = st.columns([3, 1])
            with c1:
                st.markdown(f"**{name}**")
            with c2:
                if st.button("Играть", key=f"pick_{name}", use_container_width=True):
                    st.session_state.active_character = name
                    _goto("game")


def _form_block(login: str) -> None:
    with st.form("wizard_form"):
        st.markdown("#### 1. Общее")
        c1, c2 = st.columns([2, 1])
        with c1:
            name = st.text_input("Имя персонажа", key="wz_name")
        with c2:
            gender = st.selectbox(
                "Пол", options=["male", "female"],
                format_func=lambda x: {"male": "Мужской", "female": "Женский"}[x],
                key="wz_gender",
            )

        c1, c2 = st.columns(2)
        with c1:
            age = st.text_input("Возраст", value="30", key="wz_age")
        with c2:
            appearance = st.text_input("Внешность (кратко)", key="wz_appearance")

        user_background = st.text_area(
            "Краткая предыстория (необязательно)",
            key="wz_background", height=80,
        )

        st.markdown("#### 2. Фракция")
        faction_id = st.selectbox(
            "Фракция",
            options=list(FACTIONS.keys()),
            format_func=lambda x: FACTIONS[x]["name"],
            key="wz_faction",
        )

        subfaction_id = st.selectbox(
            "Субфракция",
            options=FACTIONS[faction_id]["subfactions"],
            format_func=lambda x: SUBFACTION_NAMES.get(x, x),
            key="wz_subfaction",
        )

        st.markdown("#### 3. Характеристики")
        st.caption("Нажми «Сохранить» — сгенерируем 2d10+25 для каждой.")

        submitted = st.form_submit_button(
            "💾 Создать персонажа", type="primary", use_container_width=True,
        )

    if submitted:
        if not name.strip():
            st.error("Введите имя персонажа")
            return
        try:
            stats = roll_characteristics(random.Random())
            data = build_character(
                name=name.strip(),
                gender=gender,
                age=str(age),
                appearance=appearance,
                user_background=user_background,
                faction_id=faction_id,
                subfaction_id=subfaction_id,
                characteristics=stats,
            )
            save_character(login, name.strip(), data)
            st.session_state.active_character = name.strip()
            st.success(f"Персонаж «{name}» создан")
            _goto("game")
        except (CharacterError, ValueError) as e:
            st.error(str(e))


def render() -> None:
    login = st.session_state.get("user_login", "—")

    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
    st.markdown(
        "<h2 style='text-align: center; font-family: Georgia, serif; "
        "letter-spacing: 3px;'>🧬 Создание персонажа</h2>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<p style='text-align: center; opacity: 0.6;'>Игрок: {login}</p>",
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        _existing_block(login)
        _form_block(login)

        st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
        if st.button("Выйти из аккаунта", use_container_width=True):
            _logout()


# ---------- game.py обновим тоже — покажем лист персонажа ----------
