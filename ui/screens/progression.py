# HOTFIX_15Y
# ui/screens/progression.py — экран «Развитие» (Rogue Trader).
from __future__ import annotations

import streamlit as st

from persistence.characters import load_character, save_character
from services import progression as P
from services.fallbacks import CHARACTERISTIC_NAMES


_CSS = '''<style>
.pg-head { text-align: center; padding: 8px 20px 4px 20px; }
.pg-title {
    font-family: Georgia, serif;
    font-size: 34px; letter-spacing: 5px;
    color: var(--fg);
    text-shadow: 0 0 22px var(--accent-glow);
    margin-bottom: 4px;
}
.pg-sub { color: var(--fg-dim); font-size: 13px; letter-spacing: 2px; }
.pg-rank {
    max-width: 620px; margin: 12px auto 18px auto;
    border: 1px solid var(--border);
    border-left: 3px solid var(--accent);
    border-radius: 6px;
    padding: 10px 16px;
    background: rgba(255,255,255,0.03);
    color: var(--fg);
}
.pg-rank .row {
    display: flex; justify-content: space-between;
    font-size: 13px; padding: 2px 0;
}
.pg-rank .lbl { color: var(--fg-dim); letter-spacing: 1px; }
.pg-rank .val { color: var(--fg); font-weight: 600; }
.pg-bar {
    height: 10px;
    background: rgba(255,255,255,0.06);
    border: 1px solid var(--border);
    border-radius: 4px; overflow: hidden;
    margin-top: 8px;
}
.pg-bar-fill {
    height: 100%;
    background: linear-gradient(90deg, var(--accent) 0%, var(--accent-soft) 100%);
    box-shadow: 0 0 10px var(--accent-glow);
}
.pg-char {
    display: flex; justify-content: space-between;
    border-bottom: 1px solid rgba(255,255,255,0.06);
    padding: 4px 0; font-size: 13px;
}
.pg-char .name { color: var(--fg); }
.pg-char .val { color: var(--accent-soft); font-weight: 600; }
.pg-char .note { color: var(--fg-dim); font-size: 11px; margin-left: 8px; }
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
        if st.button("В игру", use_container_width=True, key="pg_to_game"):
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
        "<div class='row'><span class='lbl'>РАНГ</span>"
        "<span class='val'>" + rank_name + "</span></div>"
        "<div class='row'><span class='lbl'>Потрачено XP</span>"
        "<span class='val'>" + str(spent) + "</span></div>"
        "<div class='row'><span class='lbl'>Свободно XP</span>"
        "<span class='val'>" + str(free_xp) + "</span></div>"
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
    st.caption("Свободно XP: " + str(free))
    for stat, val in stats.items():
        name = CHARACTERISTIC_NAMES.get(stat, stat)
        lvl = P.char_advance_level(char, stat)
        cost = P.char_advance_cost(char, stat)
        prof = "профильная" if P.is_proficient(char, stat) else "элитная"
        note = "+" + str(lvl * 5) + " / +15 · " + prof
        c1, c2, c3 = st.columns([3, 2, 2])
        with c1:
            st.markdown(
                "<div class='pg-char'>"
                "<span class='name'>" + name + "</span>"
                "<span class='val'>" + str(val) + "</span>"
                "<span class='note'>" + note + "</span>"
                "</div>",
                unsafe_allow_html=True,
            )
        with c2:
            if cost < 0:
                st.caption("максимум")
            else:
                st.caption("цена: " + str(cost) + " XP")
        with c3:
            if cost >= 0:
                disabled = free < cost
                if st.button("+5", key="pg_char_" + stat,
                             disabled=disabled, use_container_width=True):
                    ok, msg = P.buy_char_advance(char, stat)
                    if ok:
                        _save(char)
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)


def _tab_skills(char):
    skills = char.get("skills") or []
    free = int(char.get("xp", 0) or 0)
    st.caption("Свободно XP: " + str(free))
    st.caption("Trained — 100 / Experienced — 200 / Veteran — 300")
    known = []
    for s in skills:
        if isinstance(s, dict):
            known.append(str(s.get("name")))
        else:
            known.append(str(s))
    if known:
        st.markdown("**Уже известные:**")
        for nm in known:
            lvl = "Trained"
            for s in skills:
                if isinstance(s, dict) and str(s.get("name")) == nm:
                    lvl = str(s.get("level") or "Trained")
            c1, c2 = st.columns([3, 2])
            with c1:
                st.write(nm + " (" + lvl + ")")
            with c2:
                order = ["Trained", "Experienced", "Veteran"]
                if lvl in order and order.index(lvl) < len(order) - 1:
                    nxt = order[order.index(lvl) + 1]
                    cst = P.skill_cost(nxt)
                    if st.button("-> " + nxt + " (" + str(cst) + ")",
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
    st.markdown("---")
    st.markdown("**Добавить новый навык:**")
    new_nm = st.text_input("Название", key="pg_sk_new")
    if st.button("Купить Trained (100 XP)", key="pg_sk_new_go",
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
    st.caption("Свободно XP: " + str(free))
    st.caption("Базовый — 400 / с пререквизитом — 600 / Universal — 750")
    tal = char.get("talents") or []
    if tal:
        st.markdown("**Взятые таланты:**")
        st.write(", ".join(str(t) for t in tal))
    else:
        st.caption("Талантов нет.")
    st.markdown("---")
    nm = st.text_input("Название таланта", key="pg_tal_new")
    kind = st.selectbox(
        "Тип",
        options=["basic", "prereq", "universal"],
        format_func=lambda k: {
            "basic": "Базовый (400 XP)",
            "prereq": "С пререквизитом (600 XP)",
            "universal": "Universal (750 XP)",
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
    st.caption("PSY: " + str(psy_rating) + " · свободно XP: " + str(free))
    st.caption("Максимальное Value по рангу: " + str(max_val))
    powers = char.get("psychic_powers") or []
    if powers:
        st.markdown("**Известные техники:**")
        st.write(", ".join(str(p) for p in powers))
    else:
        st.caption("Психосил нет.")
    st.markdown("---")
    nm = st.text_input("Название техники", key="pg_psy_new")
    val = st.selectbox(
        "Value",
        options=[200, 300, 400],
        index=0,
        format_func=lambda v: str(v) + " XP",
        key="pg_psy_val",
    )
    if val > max_val:
        st.warning("Rank too low для Value " + str(val) + ".")
    if st.button("Изучить (" + str(val) + " XP)", key="pg_psy_go",
                 disabled=not nm.strip() or free < val or val > max_val):
        ok, msg = P.buy_psy(char, nm.strip(), val)
        if ok:
            _save(char)
            st.success(msg)
            st.rerun()
        else:
            st.error(msg)
