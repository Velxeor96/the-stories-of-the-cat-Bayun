# PATCH_16F
# ui/screens/progression.py — экран «Развитие» (визуал).
from __future__ import annotations

import streamlit as st

from persistence.characters import load_character, save_character
from services import progression as P
from services.fallbacks import CHARACTERISTIC_NAMES


_CSS = '''<style>
.pg-head {
    text-align: center;
    padding: 8px 20px 4px 20px;
}
.pg-title {
    font-family: Georgia, serif;
    font-size: 44px;
    letter-spacing: 10px;
    color: var(--fg);
    text-shadow: 0 0 30px var(--accent-glow),
                 0 0 60px var(--accent-glow);
    margin-bottom: 6px;
}
.pg-sub {
    color: var(--fg-dim);
    font-size: 13px;
    letter-spacing: 3px;
    font-style: italic;
}
.pg-rank {
    max-width: 720px;
    margin: 18px auto 24px auto;
    border: 1px solid var(--border-hi);
    border-left: 4px solid var(--accent);
    border-radius: 10px;
    padding: 18px 24px;
    background: linear-gradient(180deg,
        color-mix(in srgb, var(--accent) 6%, var(--panel)) 0%,
        var(--panel) 100%);
    box-shadow: 0 4px 20px var(--shadow),
                0 0 30px var(--accent-glow);
}
.pg-rank .row {
    display: flex;
    justify-content: space-between;
    font-size: 14px;
    padding: 4px 0;
    border-bottom: 1px dashed rgba(255,255,255,0.05);
}
.pg-rank .row:last-of-type { border-bottom: none; }
.pg-rank .lbl {
    color: var(--fg-dim);
    letter-spacing: 2px;
    text-transform: uppercase;
    font-size: 11px;
}
.pg-rank .val {
    color: var(--fg);
    font-family: Georgia, serif;
    font-weight: bold;
    font-size: 20px;
}
.pg-rank .val.acc {
    color: var(--accent);
    text-shadow: 0 0 10px var(--accent-glow);
}
.pg-bar {
    height: 14px;
    background: rgba(255,255,255,0.05);
    border: 1px solid var(--border-hi);
    border-radius: 7px;
    overflow: hidden;
    margin-top: 12px;
    position: relative;
}
.pg-bar-fill {
    height: 100%;
    background: linear-gradient(90deg,
        var(--accent) 0%, var(--accent-soft) 100%);
    box-shadow: 0 0 14px var(--accent-glow);
    transition: width 0.4s ease;
}
.pg-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 14px;
    margin: 18px 0 22px 0;
}
.pg-card {
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 16px 14px 12px 14px;
    background: linear-gradient(180deg,
        color-mix(in srgb, var(--accent) 4%, var(--panel)) 0%,
        var(--panel) 100%);
    text-align: center;
    transition: all 0.25s ease;
    position: relative;
    overflow: hidden;
}
.pg-card:hover {
    border-color: var(--accent);
    box-shadow: 0 0 24px var(--accent-glow);
    transform: translateY(-2px);
}
.pg-card.prof {
    border-left: 3px solid var(--accent);
}
.pg-card.elite {
    border-left: 3px solid var(--border-hi);
    opacity: 0.92;
}
.pg-card .cap {
    font-size: 10px;
    letter-spacing: 3px;
    text-transform: uppercase;
    color: var(--fg-dim);
    margin-bottom: 6px;
}
.pg-card .val {
    font-family: Georgia, serif;
    font-size: 42px;
    font-weight: bold;
    color: var(--fg);
    text-shadow: 0 0 16px var(--accent-glow);
    line-height: 1;
    margin: 4px 0 8px 0;
}
.pg-card .name {
    font-size: 12px;
    color: var(--fg-dim);
    letter-spacing: 1px;
    margin-bottom: 8px;
}
.pg-card .lvl {
    display: inline-block;
    font-size: 10px;
    padding: 2px 8px;
    border: 1px solid var(--border-hi);
    border-radius: 10px;
    color: var(--fg-dim);
    letter-spacing: 1px;
    margin-bottom: 8px;
}
.pg-card .lvl.prof {
    border-color: var(--accent);
    color: var(--accent-soft);
}
.pg-card .cost {
    font-size: 11px;
    color: var(--fg-dim);
    letter-spacing: 1px;
    margin-top: 6px;
}
.pg-card .cost b {
    color: var(--accent-soft);
    font-size: 14px;
}
.pg-card .cost.max {
    color: #b08020;
    font-weight: 600;
}
.pg-sec {
    font-size: 11px;
    letter-spacing: 4px;
    color: var(--accent);
    text-transform: uppercase;
    margin: 22px 0 12px 0;
    padding-bottom: 6px;
    border-bottom: 1px solid var(--border);
}
.pg-info {
    max-width: 720px;
    margin: 12px auto;
    padding: 10px 16px;
    border-left: 3px solid var(--accent);
    background: rgba(255,255,255,0.02);
    border-radius: 6px;
    color: var(--fg-dim);
    font-size: 12px;
    letter-spacing: 1px;
}
.pg-skill-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid rgba(255,255,255,0.06);
    padding: 8px 4px;
    font-size: 14px;
}
.pg-skill-row .name {
    color: var(--fg);
    font-family: Georgia, serif;
}
.pg-skill-row .lvl {
    color: var(--accent-soft);
    font-weight: 600;
    letter-spacing: 1px;
    font-size: 12px;
}
.pg-chip {
    display: inline-block;
    padding: 4px 12px;
    margin: 3px 4px 3px 0;
    border: 1px solid var(--border-hi);
    border-radius: 12px;
    font-size: 13px;
    color: var(--fg);
    background: rgba(255,255,255,0.03);
}
</style>'''


def _login():
    return st.session_state.get("user_login") or ""


def _char_name():
    return st.session_state.get("active_character") or ""


def _load():
    lg, nm = _login(), _char_name()
    if not lg or not nm:
        return None
    try:
        return load_character(lg, nm)
    except Exception as e:
        st.error("Не удалось загрузить: " + type(e).__name__ + ": " + str(e))
        return None


def _save(char):
    try:
        save_character(_login(), _char_name(), char)
    except Exception as e:
        st.error("Не удалось сохранить: " + type(e).__name__ + ": " + str(e))


def render():
    st.markdown(_CSS, unsafe_allow_html=True)
    st.markdown(
        "<div class='pg-head'>"
        "<div class='pg-title'>РАЗВИТИЕ</div>"
        "<div class='pg-sub'>Rogue Trader · таблицы прогрессии</div>"
        "</div>",
        unsafe_allow_html=True,
    )

    char = _load()
    if not char:
        st.warning("Нет активного персонажа.")
        if st.button("В главное меню", key="pg_back_none"):
            st.session_state.screen = "main_menu"
            st.rerun()
        return

    _rank_block(char)

    tab_chars, tab_skills, tab_talents, tab_psy = st.tabs(
        ["Характеристики", "Навыки", "Таланты", "Психосилы"]
    )
    with tab_chars:
        _tab_chars(char)
    with tab_skills:
        _tab_skills(char)
    with tab_talents:
        _tab_talents(char)
    with tab_psy:
        _tab_psy(char)

    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("В игру", use_container_width=True,
                     type="primary", key="pg_to_game"):
            st.session_state.screen = "game"
            st.rerun()
    with c2:
        if st.button("В главное меню", use_container_width=True,
                     key="pg_to_menu"):
            st.session_state.screen = "main_menu"
            st.rerun()


def _rank_block(char):
    spent, cur, nxt = P.rank_progress(char)
    rank_num, rank_name = P.current_rank(char)
    free_xp = int(char.get("xp", 0) or 0)
    span = max(1, nxt - cur)
    pct = int(min(100, max(0, (spent - cur) * 100 / span)))
    html = (
        "<div class='pg-rank'>"
        "<div class='row'><span class='lbl'>Ранг</span>"
        "<span class='val acc'>" + rank_name + "</span></div>"
        "<div class='row'><span class='lbl'>Потрачено XP</span>"
        "<span class='val'>" + str(spent) + "</span></div>"
        "<div class='row'><span class='lbl'>Свободно XP</span>"
        "<span class='val acc'>" + str(free_xp) + "</span></div>"
        "<div class='row'><span class='lbl'>Следующий ранг</span>"
        "<span class='val'>" + str(nxt) + " XP</span></div>"
        "<div class='pg-bar'><div class='pg-bar-fill' "
        "style='width:" + str(pct) + "%;'></div></div>"
        "</div>"
    )
    st.markdown(html, unsafe_allow_html=True)


def _tab_chars(char):
    stats = char.get("characteristics") or {}
    free = int(char.get("xp", 0) or 0)
    if not stats:
        st.caption("Характеристик нет.")
        return

    prof_count = sum(1 for s in stats if P.is_proficient(char, s))
    st.markdown(
        "<div class='pg-info'>"
        "Профильных характеристик: <b>" + str(prof_count) + "</b> · "
        "Элитных: <b>" + str(len(stats) - prof_count) + "</b> · "
        "Свободно XP: <b>" + str(free) + "</b>"
        "</div>",
        unsafe_allow_html=True,
    )

    cards = []
    for stat, val in stats.items():
        name = CHARACTERISTIC_NAMES.get(stat, stat)
        lvl = P.char_advance_level(char, stat)
        cost = P.char_advance_cost(char, stat)
        is_prof = P.is_proficient(char, stat)
        cls = "pg-card prof" if is_prof else "pg-card elite"
        lvl_cls = "lvl prof" if is_prof else "lvl"
        lvl_text = "+" + str(lvl * 5) + " / +15"
        if cost < 0:
            cost_block = "<div class='cost max'>максимум</div>"
            btn_key = None
        else:
            cost_block = ("<div class='cost'>цена: <b>"
                          + str(cost) + "</b> XP</div>")
            btn_key = cost
        cards.append({
            "stat": stat,
            "name": name,
            "val": val,
            "cls": cls,
            "lvl_cls": lvl_cls,
            "lvl_text": lvl_text,
            "cost_block": cost_block,
            "btn_key": btn_key,
            "disabled": (cost < 0 or free < cost),
        })

    # Сетка по 3 карточки в ряд
    row_size = 3
    for i in range(0, len(cards), row_size):
        chunk = cards[i:i + row_size]
        cols = st.columns(3)
        for j, c in enumerate(chunk):
            with cols[j]:
                _render_char_card(c, char)


def _render_char_card(c, char):
    html = (
        "<div class='" + c["cls"] + "'>"
        "<div class='cap'>" + c["stat"] + "</div>"
        "<div class='val'>" + str(c["val"]) + "</div>"
        "<div class='name'>" + c["name"] + "</div>"
        "<div class='" + c["lvl_cls"] + "'>" + c["lvl_text"] + "</div>"
        + c["cost_block"]
        + "</div>"
    )
    st.markdown(html, unsafe_allow_html=True)
    if c["btn_key"] is not None:
        if st.button("+5", key="pg_char_" + c["stat"],
                     disabled=c["disabled"], use_container_width=True):
            ok, msg = P.buy_char_advance(char, c["stat"])
            if ok:
                _save(char)
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)


def _tab_skills(char):
    skills = char.get("skills") or []
    free = int(char.get("xp", 0) or 0)
    st.markdown(
        "<div class='pg-info'>"
        "Ступени: <b>Базовый</b> 100 · <b>Опытный</b> 200 · "
        "<b>Ветеран</b> 300 · Свободно XP: <b>" + str(free) + "</b>"
        "</div>",
        unsafe_allow_html=True,
    )

    known = []
    for s in skills:
        if isinstance(s, dict):
            known.append(str(s.get("name")))
        else:
            known.append(str(s))

    if known:
        st.markdown("<div class='pg-sec'>Уже известные</div>",
                    unsafe_allow_html=True)
        for nm in known:
            lvl = "Trained"
            for s in skills:
                if isinstance(s, dict) and str(s.get("name")) == nm:
                    lvl = str(s.get("level") or "Trained")
            c1, c2 = st.columns([3, 2])
            with c1:
                st.markdown(
                    "<div class='pg-skill-row'><span class='name'>"
                    + nm + "</span><span class='lvl'>"
                    + P.level_ru(lvl) + "</span></div>",
                    unsafe_allow_html=True,
                )
            with c2:
                order = ["Trained", "Experienced", "Veteran"]
                if lvl in order and order.index(lvl) < len(order) - 1:
                    nxt = order[order.index(lvl) + 1]
                    cst = P.skill_cost(nxt)
                    if st.button("→ " + P.level_ru(nxt)
                                 + " (" + str(cst) + " XP)",
                                 key="pg_sk_up_" + nm,
                                 disabled=free < cst,
                                 use_container_width=True):
                        ok, msg = P.buy_skill(char, nm)
                        if ok:
                            _save(char)
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
                else:
                    st.caption("максимум")

    st.markdown("<div class='pg-sec'>Добавить новый навык</div>",
                unsafe_allow_html=True)
    new_nm = st.text_input("Название", key="pg_sk_new")
    if st.button("Изучить (Базовый, 100 XP)", key="pg_sk_new_go",
                 disabled=not new_nm.strip() or free < 100):
        ok, msg = P.buy_skill(char, new_nm.strip())
        if ok:
            _save(char)
            st.success(msg)
            st.rerun()
        else:
            st.error(msg)


def _tab_talents(char):
    free = int(char.get("xp", 0) or 0)
    st.markdown(
        "<div class='pg-info'>"
        "Простой — 400 · С пререквизитом — 600 · "
        "Универсальный — 750 · Свободно XP: <b>" + str(free) + "</b>"
        "</div>",
        unsafe_allow_html=True,
    )

    tal = char.get("talents") or []
    if tal:
        st.markdown("<div class='pg-sec'>Взятые таланты</div>",
                    unsafe_allow_html=True)
        chips = "".join(
            "<span class='pg-chip'>" + str(t) + "</span>"
            for t in tal
        )
        st.markdown(chips, unsafe_allow_html=True)
    else:
        st.caption("Талантов нет.")

    st.markdown("<div class='pg-sec'>Взять новый талант</div>",
                unsafe_allow_html=True)
    nm = st.text_input("Название таланта", key="pg_tal_new")
    kind = st.selectbox(
        "Тип",
        options=["basic", "prereq", "universal"],
        format_func=lambda k: {
            "basic": "Простой (400 XP)",
            "prereq": "С пререквизитом (600 XP)",
            "universal": "Универсальный (750 XP)",
        }.get(k, k),
        key="pg_tal_kind",
    )
    cost = P.TALENT_COSTS[kind]
    if st.button("Взять (" + str(cost) + " XP)", key="pg_tal_go",
                 disabled=not nm.strip() or free < cost):
        ok, msg = P.buy_talent(char, nm.strip(), cost)
        if ok:
            _save(char)
            st.success(msg)
            st.rerun()
        else:
            st.error(msg)


def _tab_psy(char):
    psy_rating = int(char.get("psy_rating", 0) or 0)
    if psy_rating <= 0:
        st.info("Персонаж не псайкер (PSY = 0).")
        return
    free = int(char.get("xp", 0) or 0)
    max_val = P.available_psy_value(char)
    st.markdown(
        "<div class='pg-info'>"
        "PSY: <b>" + str(psy_rating) + "</b> · "
        "Свободно XP: <b>" + str(free) + "</b> · "
        "Максимальный уровень техники по рангу: <b>"
        + str(max_val) + "</b>"
        "</div>",
        unsafe_allow_html=True,
    )

    powers = char.get("psychic_powers") or []
    if powers:
        st.markdown("<div class='pg-sec'>Известные техники</div>",
                    unsafe_allow_html=True)
        chips = "".join(
            "<span class='pg-chip'>" + str(p) + "</span>"
            for p in powers
        )
        st.markdown(chips, unsafe_allow_html=True)
    else:
        st.caption("Психосил нет.")

    st.markdown("<div class='pg-sec'>Изучить новую</div>",
                unsafe_allow_html=True)
    nm = st.text_input("Название техники", key="pg_psy_new")
    val = st.selectbox(
        "Уровень",
        options=[200, 300, 400],
        index=0,
        format_func=lambda v: str(v) + " XP",
        key="pg_psy_val",
    )
    if val > max_val:
        st.warning("Ранг слишком низок для уровня " + str(val) + ".")
    if st.button("Изучить (" + str(val) + " XP)", key="pg_psy_go",
                 disabled=not nm.strip() or free < val or val > max_val):
        ok, msg = P.buy_psy(char, nm.strip(), val)
        if ok:
            _save(char)
            st.success(msg)
            st.rerun()
        else:
            st.error(msg)
