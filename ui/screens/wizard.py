# PATCH_34B
"""ui/screens/wizard.py — создание персонажа с data_editor и full-screen INITIATIO."""
from __future__ import annotations
import streamlit as st

from persistence.characters import (
    CharacterError, save_character, list_characters,
)
from services.character_creation import (
    build_character, roll_pool, auto_distribute,
)
from services.fallbacks import (
    CHARACTERISTIC_KEYS, CHARACTERISTIC_NAMES,
    FACTIONS, SUBFACTION_NAMES,
    home_worlds_for, careers_for,
    home_world_display_name, career_display_name,
    home_world_data, career_data,
)

FACTION_LORE = {
    "imperium": "Ветераны и бюрократы, сражающиеся за Императора.",
    "chaos": "Проклятые и одержимые. Сила через Варп, цена — душа.",
    "eldar": "Древняя раса с погибающего крафт-мира.",
    "drukhari": "Тёмные родичи эльдар. Боль как искусство.",
    "orks": "Зелёная орда. Просто. Громко. Весело.",
    "tau": "Молодая империя Высшего Блага.",
    "necrons": "Пробудившиеся машины древней династии.",
    "genestealers": "Скрытая угроза.",
}


def _goto(screen: str) -> None:
    st.session_state.screen = screen


def _reset_subfaction_key() -> None:
    for k in list(st.session_state.keys()):
        if k.startswith("wz_subfaction_"):
            st.session_state.pop(k, None)


def render() -> None:
    login = st.session_state.get("user_login")
    if not login:
        st.warning("Сначала войди.")
        if st.button("← На главную"):
            _goto("splash")
            st.rerun()
        return

    try:
        from services.data_loader import get_index
        get_index()
    except Exception as _e:
        print("[wizard] data_loader: " + type(_e).__name__)

    try:
        from ui.theme import render_theme_strip
        render_theme_strip(key_prefix="__wiz_theme")
    except Exception:
        pass

    st.markdown(
        "<h1 style='font-family:Georgia,serif;text-align:center;'>"
        "🛠️ Создание персонажа</h1>"
        "<div style='text-align:center; color:#a0a0a0; font-style:italic; "
        "margin-bottom:22px;'>Игрок: " + login + "</div>",
        unsafe_allow_html=True,
    )

    try:
        existing = list_characters(login)
    except Exception:
        existing = []
    if existing:
        with st.expander("Персонажи (" + str(len(existing)) + ")"):
            for nm in existing:
                c1, c2 = st.columns([4, 1])
                with c1:
                    st.markdown("**" + nm + "**")
                with c2:
                    if st.button("Играть", key="play_" + nm,
                                 use_container_width=True):
                        st.session_state.active_character = nm
                        _goto("game")
                        st.rerun()

    st.markdown("#### 1. Общее")
    c1, c2 = st.columns([2, 1])
    with c1:
        name = st.text_input("Имя персонажа", key="wz_name")
    with c2:
        gender = st.selectbox(
            "Пол", options=["male", "female"],
            format_func=lambda x: {"male": "Мужской",
                                   "female": "Женский"}[x],
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
        key="wz_background", height=90,
    )

    st.markdown("#### 2. Фракция")
    faction_ids = list(FACTIONS.keys())
    faction_id = st.selectbox(
        "Фракция", options=faction_ids,
        format_func=lambda x: FACTIONS[x]["name"],
        key="wz_faction", on_change=_reset_subfaction_key,
    )

    lore = FACTION_LORE.get(faction_id, "")
    if lore:
        st.markdown(
            "<div style='background:#131316; border-left:3px solid #8b1a1a; "
            "padding:8px 12px; border-radius:6px; margin:4px 0 14px 0; "
            "color:#c8c0b0; font-style:italic; font-size:13px;'>"
            + lore + "</div>",
            unsafe_allow_html=True,
        )

    subfaction_options = FACTIONS[faction_id].get("subfactions", [])
    subfaction_id = None
    if subfaction_options:
        subfaction_id = st.selectbox(
            "Субфракция",
            options=subfaction_options,
            format_func=lambda x: SUBFACTION_NAMES.get(x, x),
            key="wz_subfaction_" + faction_id,
        )

    st.markdown("#### 3. Родной мир")
    hw_keys = home_worlds_for(faction_id)
    home_world_id = None
    if hw_keys:
        home_world_id = st.selectbox(
            "Родной мир", options=hw_keys,
            format_func=lambda x: home_world_display_name(faction_id, x),
            key="wz_home_" + faction_id,
        )
        hw = home_world_data(faction_id, home_world_id)
        if hw.get("desc"):
            st.caption(hw["desc"])
    else:
        st.info("Нет данных о родных мирах.")

    st.markdown("#### 4. Карьера")
    career_keys = careers_for(faction_id)
    career_id = None
    if career_keys:
        career_id = st.selectbox(
            "Карьера", options=career_keys,
            format_func=lambda x: career_display_name(faction_id, x),
            key="wz_career_" + faction_id,
        )
        cr = career_data(faction_id, career_id)
        if cr.get("desc"):
            st.caption(cr["desc"])
    else:
        st.info("Нет данных о карьерах.")

    st.markdown("#### 5. Характеристики")
    mode = st.radio(
        "Способ генерации",
        options=["Закупка очков (по книге)", "Бросок 2d10+25"],
        horizontal=True, key="wz_mode",
    )

    raw: dict = {}

    if mode == "Закупка очков (по книге)":
        st.caption("База 25. Распредели до 35 очков на характеристику. "
                   "Всего 200 очков на пул. Печатай в колонке «Очки».")
        rows = []
        for stat in CHARACTERISTIC_KEYS:
            added = int(st.session_state.get("wz_buy_" + stat, 0) or 0)
            if added < 0:
                added = 0
            if added > 35:
                added = 35
            rows.append({
                "Код": stat,
                "Характеристика": CHARACTERISTIC_NAMES[stat] + " (" + stat + ")",
                "База": 25,
                "Очки": added,
                "Итог": 25 + added,
            })
        edited = st.data_editor(
            rows,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Код": st.column_config.TextColumn("Код", disabled=True),
                "Характеристика": st.column_config.TextColumn(
                    "Характеристика", disabled=True),
                "База": st.column_config.NumberColumn(
                    "База", disabled=True),
                "Очки": st.column_config.NumberColumn(
                    "Очки (+0…+35)", min_value=0, max_value=35, step=1),
                "Итог": st.column_config.NumberColumn(
                    "Итог", disabled=True),
            },
            key="wz_data_editor",
        )
        total_added = 0
        for row in edited:
            code = str(row.get("Код", "")).strip()
            v = int(row.get("Очки", 0) or 0)
            if v < 0:
                v = 0
            if v > 35:
                v = 35
            raw[code] = 25 + v
            st.session_state["wz_buy_" + code] = v
            total_added += v
        left = 200 - total_added
        if left < 0:
            st.error("Перебор на " + str(-left) + " очков. Снимите лишние.")
        else:
            st.success("Осталось очков: " + str(left) + " / 200")


    else:
        st.caption("9 раз бросается 2d10+25, распределяешь значения.")
        c1, c2 = st.columns([1, 2])
        with c1:
            if st.button("🎲 Сгенерировать пул", use_container_width=True):
                pool = roll_pool()
                st.session_state.wz_pool = sorted(pool, reverse=True)
                auto = auto_distribute(pool)
                for k in CHARACTERISTIC_KEYS:
                    st.session_state["wz_stat_" + k] = int(auto[k])
                st.rerun()
        with c2:
            if st.session_state.get("wz_pool"):
                st.write("**Пул:** " + ", ".join(
                    str(v) for v in st.session_state.wz_pool))
                st.write("**Сумма:** " + str(sum(st.session_state.wz_pool)))
        pool = st.session_state.get("wz_pool") or []
        if pool:
            cols = st.columns(3)
            for i, stat in enumerate(CHARACTERISTIC_KEYS):
                with cols[i % 3]:
                    default = int(st.session_state.get("wz_stat_" + stat, 30))
                    raw[stat] = st.number_input(
                        CHARACTERISTIC_NAMES[stat] + " (" + stat + ")",
                        min_value=15, max_value=70, value=default, step=1,
                        key="wz_inp_" + stat,
                    )
            used = sorted(raw.values(), reverse=True)
            expected = sorted(pool, reverse=True)
            if used != expected:
                st.warning("Не совпадает с пулом.")
            else:
                st.success("Пул распределён корректно.")
        else:
            st.info("Сначала сгенерируй пул.")

    st.markdown("---")
    if st.button("💾 Сохранить персонажа", type="primary",
                 use_container_width=True, key="wz_save"):
        if not name or not name.strip():
            st.error("Введи имя персонажа.")
            return
        if mode == "Бросок 2d10+25":
            if not st.session_state.get("wz_pool"):
                st.error("Сгенерируй пул.")
                return
            used = sorted(raw.values(), reverse=True)
            expected = sorted(st.session_state.wz_pool, reverse=True)
            if used != expected:
                st.error("Пул не распределён.")
                return
        else:
            total = sum(raw.values()) - 25 * 9
            if total > 150:
                st.error("Перебор очков.")
                return
            for k in CHARACTERISTIC_KEYS:
                if raw[k] > 60:
                    st.error(k + " > 60 (35 + 25).")
                    return
        try:
            data = build_character(
                name=name.strip(), gender=gender, age=str(age),
                appearance=appearance, user_background=user_background,
                faction_id=faction_id, subfaction_id=subfaction_id,
                home_world_id=home_world_id, career_id=career_id,
                characteristics=raw,
            )
            save_character(login, name.strip(), data)
            st.session_state.active_character = name.strip()
            st.session_state["_game_loading_pending"] = True
            _goto("game")
            st.rerun()
        except CharacterError as e:
            st.error(str(e))
        except Exception as e:
            st.error("Ошибка: " + type(e).__name__ + ": " + str(e))


if __name__ == "__main__":
    pass
