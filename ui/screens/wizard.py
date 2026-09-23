# PATCH_13_FACTION_FIX_V1

'''ui/screens/wizard.py — создание персонажа (FACTION-FIX V1).'''
from __future__ import annotations

import streamlit as st

from persistence.characters import CharacterError, save_character
from services.character_creation import build_character, roll_characteristics
from services.fallbacks import (
    CHARACTERISTIC_KEYS,
    CHARACTERISTIC_NAMES,
    FACTIONS,
    SUBFACTION_NAMES,
)


FACTION_LORE = {
    "imperium": "Ветераны и бюрократы, сражающиеся за Императора. Власть, вера, сталь.",
    "chaos": "Проклятые и одержимые. Сила через Варп, цена — душа.",
    "eldar": "Древняя раса с погибающего крафт-мира. Ловкость, чутьё, пророчества.",
    "drukhari": "Тёмные родичи эльдар. Боль как искусство, тень как дом.",
    "orks": "Зелёная орда. Просто. Громко. Весело.",
    "tau": "Молодая империя Высшего Блага. Дальний бой, дроны, каста.",
    "necrons": "Пробудившиеся машины древней династии. Нет боли. Нет страха. Нет пощады.",
    "genestealers": "Скрытая угроза. Культ, что растёт изнутри. Ты — уже не ты.",
}


def _goto(screen: str) -> None:
    st.session_state.screen = screen


def _reset_subfaction_key() -> None:
    '''Старое значение субфракции больше не актуально.'''
    for k in list(st.session_state.keys()):
        if k == "wz_subfaction" or k.startswith("wz_subfaction_"):
            st.session_state.pop(k, None)


def render() -> None:
    login = st.session_state.get("user_login")
    if not login:
        st.warning("Сначала войди.")
        if st.button("← На главную"):
            _goto("splash")
            st.rerun()
        return

    st.markdown(
        "<h1 style='font-family:Georgia,serif;text-align:center;'>"
        "🧬 Создание персонажа</h1>"
        "<div style='text-align:center; color:#a0a0a0; font-style:italic; "
        "margin-bottom:22px;'>Игрок: " + login + "</div>",
        unsafe_allow_html=True,
    )

    # --- Существующие персонажи ---
    from persistence.characters import list_characters
    try:
        existing = list_characters(login)
    except Exception:
        existing = []
    if existing:
        with st.expander(f"У меня уже есть персонажи ({len(existing)})",
                         expanded=False):
            for name in existing:
                c1, c2 = st.columns([4, 1])
                with c1:
                    st.markdown(f"**{name}**")
                with c2:
                    if st.button("Играть", key=f"play_{name}",
                                 use_container_width=True):
                        st.session_state.active_character = name
                        _goto("game")
                        st.rerun()

    # --- Шаг 1: Общее ---
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
        age = st.number_input("Возраст", min_value=16, max_value=600,
                              value=30, step=1, key="wz_age")
    with c2:
        appearance = st.text_input("Внешность (кратко)", key="wz_appearance")

    user_background = st.text_area(
        "Краткая предыстория (необязательно)",
        key="wz_background", height=80,
    )

    # --- Шаг 2: Фракция ---
    st.markdown("#### 2. Фракция")
    faction_ids = list(FACTIONS.keys())

    faction_id = st.selectbox(
        "Фракция",
        options=faction_ids,
        format_func=lambda x: FACTIONS[x]["name"],
        key="wz_faction",
        on_change=_reset_subfaction_key,
    )

    # Лор выбранной фракции
    lore = FACTION_LORE.get(faction_id, "")
    if lore:
        st.markdown(
            "<div style='background:#131316; border-left:3px solid #8b1a1a; "
            "padding:8px 12px; border-radius:6px; margin:4px 0 14px 0; "
            "color:#c8c0b0; font-style:italic; font-size:13px;'>"
            + lore + "</div>",
            unsafe_allow_html=True,
        )

    # --- Шаг 2b: Субфракция (динамический key — при смене faction виджет свежий) ---
    subfaction_options = FACTIONS[faction_id].get("subfactions", [])
    if subfaction_options:
        subfaction_id = st.selectbox(
            "Субфракция",
            options=subfaction_options,
            format_func=lambda x: SUBFACTION_NAMES.get(x, x),
            key=f"wz_subfaction_{faction_id}",
        )
    else:
        subfaction_id = None
        st.info("У этой фракции нет субфракций.")

    # --- Шаг 3: Характеристики ---
    st.markdown("#### 3. Характеристики")
    st.caption("Нажми «Сохранить» — сгенерируем 2d10+25 для каждой.")
    if st.button("🎲 Сохранить персонажа", type="primary",
                 use_container_width=True, key="wz_save"):
        if not name or not name.strip():
            st.error("Введи имя персонажа.")
            return
        try:
            stats = roll_characteristics()
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
            st.success(f"Персонаж «{name}» создан ({FACTIONS[faction_id]['name']})")
            _goto("game")
            st.rerun()
        except CharacterError as e:
            st.error(str(e))
        except Exception as e:
            st.error(f"Ошибка: {type(e).__name__}: {e}")

    # --- Отладка: показать текущий выбор ---
    with st.expander("🔧 Текущий выбор (отладка)", expanded=False):
        st.write({
            "faction_id": faction_id,
            "faction_name": FACTIONS[faction_id]["name"],
            "subfaction_id": subfaction_id,
            "subfaction_name": SUBFACTION_NAMES.get(subfaction_id, subfaction_id),
            "available_subfactions": subfaction_options,
        })


if __name__ == "__main__":
    pass
