# PATCH_16H
# ui/screens/character.py — обзорная карточка персонажа.
from __future__ import annotations

import streamlit as st

from persistence.characters import load_character
from services.fallbacks import (
    CHARACTERISTIC_NAMES,
    FACTIONS,
    SUBFACTION_NAMES,
)


_CSS = '''<style>
.ch-wrap {
    max-width: 900px;
    margin: 0 auto;
    padding: 20px 24px 40px 24px;
}
.ch-head {
    display: flex;
    align-items: center;
    gap: 24px;
    padding-bottom: 18px;
    border-bottom: 1px solid var(--border);
    margin-bottom: 20px;
}
.ch-sigil {
    width: 110px; height: 110px;
    display: flex; align-items: center; justify-content: center;
    filter: drop-shadow(0 0 22px var(--accent-glow));
    flex-shrink: 0;
}
.ch-sigil svg, .ch-sigil img {
    display: block; max-width: 100%; max-height: 100%;
}
.ch-name {
    font-family: Georgia, serif;
    font-size: 38px;
    letter-spacing: 4px;
    color: var(--fg);
    text-shadow: 0 0 22px var(--accent-glow);
    margin: 0 0 6px 0;
}
.ch-tags {
    color: var(--fg-dim);
    font-size: 13px;
    letter-spacing: 2px;
    font-style: italic;
}
.ch-sec {
    font-size: 11px;
    letter-spacing: 4px;
    color: var(--accent);
    text-transform: uppercase;
    margin: 24px 0 10px 0;
    padding-bottom: 6px;
    border-bottom: 1px solid var(--border);
}
.ch-card {
    border: 1px solid var(--border);
    border-left: 3px solid var(--accent);
    border-radius: 8px;
    padding: 14px 18px;
    background: rgba(255,255,255,0.02);
    color: var(--fg);
    line-height: 1.6;
    font-size: 14px;
    margin-bottom: 8px;
}
.ch-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 10px;
    margin-bottom: 8px;
}
.ch-stat {
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 12px 14px;
    background: linear-gradient(180deg,
        color-mix(in srgb, var(--accent) 4%, var(--panel)) 0%,
        var(--panel) 100%);
    text-align: center;
}
.ch-stat .code {
    font-size: 10px;
    letter-spacing: 2px;
    color: var(--fg-dim);
    text-transform: uppercase;
    margin-bottom: 2px;
}
.ch-stat .val {
    font-family: Georgia, serif;
    font-size: 32px;
    font-weight: bold;
    color: var(--fg);
    text-shadow: 0 0 14px var(--accent-glow);
    line-height: 1;
}
.ch-stat .lbl {
    font-size: 11px;
    color: var(--fg-dim);
    margin-top: 4px;
}
.ch-pair {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 10px;
    margin-bottom: 8px;
}
.ch-mini {
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 10px 14px;
    background: rgba(255,255,255,0.02);
    text-align: center;
}
.ch-mini .lbl {
    font-size: 10px;
    letter-spacing: 2px;
    color: var(--fg-dim);
    text-transform: uppercase;
}
.ch-mini .val {
    font-family: Georgia, serif;
    font-size: 22px;
    font-weight: bold;
    color: var(--fg);
    margin-top: 4px;
}
.ch-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
}
.ch-chip {
    display: inline-block;
    border: 1px solid var(--border-hi);
    border-radius: 12px;
    padding: 4px 12px;
    font-size: 13px;
    color: var(--fg);
    background: rgba(255,255,255,0.03);
}
.ch-empty {
    color: var(--fg-dim);
    font-style: italic;
    font-size: 13px;
}
.ch-back {
    max-width: 900px;
    margin: 0 auto;
    padding: 0 24px;
}
</style>'''


def _sigil_html(theme):
    try:
        from ui.assets import sigil_svg
        return sigil_svg(theme, 110)
    except Exception:
        return ""


def _load():
    lg = st.session_state.get("user_login")
    nm = st.session_state.get("active_character")
    if not lg or not nm:
        return None
    try:
        return load_character(lg, nm)
    except Exception as e:
        st.error("Не удалось загрузить: " + type(e).__name__ + ": " + str(e))
        return None


def _chip_list(items):
    if not items:
        return "<div class='ch-empty'>— нет —</div>"
    chips = []
    for it in items:
        if isinstance(it, dict):
            name = str(it.get("name") or it.get("title") or it)
        else:
            name = str(it)
        chips.append("<span class='ch-chip'>" + name + "</span>")
    return "<div class='ch-chips'>" + "".join(chips) + "</div>"


def render():
    st.markdown(_CSS, unsafe_allow_html=True)

    char = _load()
    if not char:
        st.warning("Нет активного персонажа.")
        if st.button("В главное меню", key="ch_back_none"):
            st.session_state.screen = "main_menu"
            st.rerun()
        return

    try:
        from ui.theme import _current
        theme = _current()
    except Exception:
        theme = "dark"

    name = str(char.get("name", "—"))
    faction_id = str(char.get("faction_id") or "")
    sub_id = str(char.get("subfaction_id") or "")
    faction_name = ""
    if faction_id in FACTIONS:
        faction_name = FACTIONS[faction_id].get("name", faction_id)
    elif char.get("faction"):
        faction_name = str(char.get("faction"))
    sub_name = SUBFACTION_NAMES.get(sub_id, char.get("subfaction") or "")

    gender = "Мужской" if char.get("gender") == "male" else "Женский"
    age = char.get("age", "?")

    st.markdown(
        "<div class='ch-wrap'>"
        "<div class='ch-head'>"
        "<div class='ch-sigil'>" + _sigil_html(theme) + "</div>"
        "<div>"
        "<div class='ch-name'>" + name + "</div>"
        "<div class='ch-tags'>"
        + faction_name + " · " + str(sub_name) + " · "
        + gender + " · " + str(age) + " лет"
        "</div>"
        "</div>"
        "</div>"
        "</div>",
        unsafe_allow_html=True,
    )

    # --- Характеристики ---
    st.markdown("<div class='ch-wrap'><div class='ch-sec'>"
                "Характеристики</div></div>",
                unsafe_allow_html=True)
    stats = char.get("characteristics") or {}
    if stats:
        html = "<div class='ch-wrap'><div class='ch-grid'>"
        for code, val in stats.items():
            label = CHARACTERISTIC_NAMES.get(code, code)
            html += (
                "<div class='ch-stat'>"
                "<div class='code'>" + str(code) + "</div>"
                "<div class='val'>" + str(val) + "</div>"
                "<div class='lbl'>" + label + "</div>"
                "</div>"
            )
        html += "</div></div>"
        st.markdown(html, unsafe_allow_html=True)

    # --- Ресурсы ---
    st.markdown("<div class='ch-wrap'><div class='ch-sec'>"
                "Ресурсы</div></div>",
                unsafe_allow_html=True)
    w = char.get("wounds") or {}
    fp = char.get("fate_points") or {}
    xp = int(char.get("xp", 0) or 0)
    rank = int(char.get("rank", 1) or 1)
    corr = int(char.get("corruption", 0) or 0)
    ins = int(char.get("insanity", 0) or 0)
    psy = int(char.get("psy_rating", 0) or 0)
    money = char.get("money", 0)
    cur = char.get("currency", "")
    html = (
        "<div class='ch-wrap'><div class='ch-pair'>"
        "<div class='ch-mini'><div class='lbl'>Раны</div>"
        "<div class='val'>" + str(w.get("current", 0)) + "/"
        + str(w.get("max", 0)) + "</div></div>"
        "<div class='ch-mini'><div class='lbl'>Судьба</div>"
        "<div class='val'>" + str(fp.get("current", 0)) + "/"
        + str(fp.get("max", 0)) + "</div></div>"
        "<div class='ch-mini'><div class='lbl'>XP</div>"
        "<div class='val'>" + str(xp) + "</div></div>"
        "<div class='ch-mini'><div class='lbl'>Ранг</div>"
        "<div class='val'>" + str(rank) + "</div></div>"
        "</div>"
        "<div class='ch-pair'>"
        "<div class='ch-mini'><div class='lbl'>Порча</div>"
        "<div class='val'>" + str(corr) + "</div></div>"
        "<div class='ch-mini'><div class='lbl'>Безумие</div>"
        "<div class='val'>" + str(ins) + "</div></div>"
        "<div class='ch-mini'><div class='lbl'>PSY</div>"
        "<div class='val'>" + str(psy) + "</div></div>"
        "<div class='ch-mini'><div class='lbl'>Деньги</div>"
        "<div class='val'>" + str(money) + " " + str(cur) + "</div></div>"
        "</div></div>"
    )
    st.markdown(html, unsafe_allow_html=True)

    # --- Внешность и предыстория ---
    appearance = char.get("appearance") or ""
    background = char.get("user_background") or char.get("background") or ""
    if appearance or background:
        st.markdown("<div class='ch-wrap'><div class='ch-sec'>"
                    "Внешность и предыстория</div></div>",
                    unsafe_allow_html=True)
        if appearance:
            st.markdown(
                "<div class='ch-wrap'><div class='ch-card'>"
                "<b>Внешность.</b> " + str(appearance) + "</div></div>",
                unsafe_allow_html=True,
            )
        if background:
            st.markdown(
                "<div class='ch-wrap'><div class='ch-card'>"
                "<b>Предыстория.</b> " + str(background) + "</div></div>",
                unsafe_allow_html=True,
            )

    # --- Снаряжение ---
    st.markdown("<div class='ch-wrap'><div class='ch-sec'>"
                "Снаряжение</div></div>",
                unsafe_allow_html=True)
    armour = char.get("armour") or {}
    armour_parts = []
    for slot_key, slot_name in (
        ("head", "Голова"), ("body", "Торс"),
        ("arms", "Руки"), ("legs", "Ноги"),
    ):
        val = armour.get(slot_key) or ""
        if val:
            armour_parts.append(slot_name + ": " + str(val))
    if armour_parts:
        st.markdown(
            "<div class='ch-wrap'><div class='ch-card'>"
            + " · ".join(armour_parts) + "</div></div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            "<div class='ch-wrap'><div class='ch-empty'>"
            "Броня не надета.</div></div>",
            unsafe_allow_html=True,
        )

    eq = char.get("equipment") or []
    st.markdown("<div class='ch-wrap'>" + _chip_list(eq) + "</div>",
                unsafe_allow_html=True)

    # --- Оружие ---
    weapons = char.get("weapons") or []
    st.markdown("<div class='ch-wrap'><div class='ch-sec'>"
                "Оружие</div></div>",
                unsafe_allow_html=True)
    if weapons:
        html = "<div class='ch-wrap'>"
        for i, w in enumerate(weapons):
            if isinstance(w, dict):
                nm = str(w.get("name") or w.get("title") or "—")
                stats = str(w.get("stats") or w.get("damage") or "")
                notes = str(w.get("notes") or "")
            else:
                nm = str(w)
                stats = ""
                notes = ""
            line = "<div class='ch-card'><b>" + nm + "</b>"
            if stats:
                line += " · " + stats
            if notes:
                line += "<br/><span style='color:var(--fg-dim);'>"
                line += notes + "</span>"
            line += "</div>"
            html += line
        html += "</div>"
        st.markdown(html, unsafe_allow_html=True)
    else:
        st.markdown("<div class='ch-wrap'><div class='ch-empty'>"
                    "Оружия нет.</div></div>",
                    unsafe_allow_html=True)

    # --- Навыки / таланты ---
    st.markdown("<div class='ch-wrap'><div class='ch-sec'>"
                "Навыки и таланты</div></div>",
                unsafe_allow_html=True)
    skills = char.get("skills") or []
    talents = char.get("talents") or []
    psy_powers = char.get("psychic_powers") or []
    st.markdown(
        "<div class='ch-wrap'>"
        "<div style='color:var(--fg-dim);font-size:11px;"
        "letter-spacing:2px;text-transform:uppercase;"
        "margin-bottom:6px;'>Навыки</div>"
        + _chip_list(skills) +
        "</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<div class='ch-wrap'>"
        "<div style='color:var(--fg-dim);font-size:11px;"
        "letter-spacing:2px;text-transform:uppercase;"
        "margin:14px 0 6px 0;'>Таланты</div>"
        + _chip_list(talents) +
        "</div>",
        unsafe_allow_html=True,
    )
    if psy_powers:
        st.markdown(
            "<div class='ch-wrap'>"
            "<div style='color:var(--fg-dim);font-size:11px;"
            "letter-spacing:2px;text-transform:uppercase;"
            "margin:14px 0 6px 0;'>Психосилы</div>"
            + _chip_list(psy_powers) +
            "</div>",
            unsafe_allow_html=True,
        )

    # --- Кнопки ---
    st.markdown("---")
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("В игру", use_container_width=True,
                     type="primary", key="ch_to_game"):
            st.session_state.screen = "game"
            st.rerun()
    with c2:
        if st.button("Хроники", use_container_width=True,
                     key="ch_to_chronicles"):
            st.session_state.screen = "chronicles"
            st.rerun()
    with c3:
        if st.button("В главное меню", use_container_width=True,
                     key="ch_to_menu"):
            st.session_state.screen = "main_menu"
            st.rerun()
