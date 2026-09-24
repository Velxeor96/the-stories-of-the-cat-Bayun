# PATCH_16H
# ui/screens/chronicles.py — хроники: NPC, задачи, дневник, эффекты.
from __future__ import annotations

import streamlit as st

from persistence.characters import load_character


_CSS = '''<style>
.cn-wrap {
    max-width: 900px;
    margin: 0 auto;
    padding: 20px 24px 40px 24px;
}
.cn-title {
    font-family: Georgia, serif;
    font-size: 38px;
    letter-spacing: 8px;
    color: var(--fg);
    text-shadow: 0 0 24px var(--accent-glow);
    text-align: center;
    margin-bottom: 6px;
}
.cn-sub {
    color: var(--fg-dim);
    font-style: italic;
    letter-spacing: 3px;
    text-align: center;
    font-size: 13px;
    margin-bottom: 24px;
}
.cn-sec {
    font-size: 11px;
    letter-spacing: 4px;
    color: var(--accent);
    text-transform: uppercase;
    margin: 24px 0 10px 0;
    padding-bottom: 6px;
    border-bottom: 1px solid var(--border);
}
.cn-card {
    border: 1px solid var(--border);
    border-left: 3px solid var(--accent);
    border-radius: 8px;
    padding: 12px 16px;
    background: rgba(255,255,255,0.02);
    color: var(--fg);
    font-size: 14px;
    margin-bottom: 8px;
    line-height: 1.55;
}
.cn-card .meta {
    color: var(--fg-dim);
    font-size: 11px;
    letter-spacing: 1px;
    text-transform: uppercase;
    margin-bottom: 4px;
}
.cn-list {
    list-style: none;
    padding-left: 0;
    margin: 4px 0 0 0;
}
.cn-list li {
    padding: 6px 0;
    border-bottom: 1px dashed rgba(255,255,255,0.06);
}
.cn-list li:last-child { border-bottom: none; }
.cn-empty {
    color: var(--fg-dim);
    font-style: italic;
    font-size: 13px;
    padding: 8px 0;
}
.cn-journal {
    border-left: 3px solid var(--accent);
    padding-left: 18px;
    margin-left: 6px;
}
.cn-journal-entry {
    padding: 8px 0;
    color: var(--fg);
    font-size: 14px;
    border-bottom: 1px solid rgba(255,255,255,0.04);
    font-style: italic;
}
.cn-journal-entry:last-child { border-bottom: none; }
.cn-journal-entry .num {
    color: var(--accent);
    font-style: normal;
    font-size: 12px;
    letter-spacing: 2px;
    margin-right: 8px;
}
.cn-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
}
.cn-chip {
    display: inline-block;
    border: 1px solid var(--border-hi);
    border-radius: 12px;
    padding: 4px 12px;
    font-size: 13px;
    color: var(--fg);
    background: rgba(255,255,255,0.03);
}
.cn-loc {
    border: 1px solid var(--border-hi);
    border-left: 3px solid var(--accent);
    border-radius: 8px;
    padding: 12px 16px;
    background: rgba(255,255,255,0.02);
    color: var(--fg);
    font-size: 14px;
    margin-bottom: 8px;
}
.cn-loc .row {
    display: flex;
    justify-content: space-between;
    padding: 2px 0;
}
.cn-loc .lbl {
    color: var(--fg-dim);
    letter-spacing: 1px;
    text-transform: uppercase;
    font-size: 11px;
}
.cn-loc .val { color: var(--fg); }
</style>'''


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


def _list_items(items):
    if not items:
        return "<div class='cn-empty'>— нет —</div>"
    html = "<ul class='cn-list'>"
    for it in items:
        if isinstance(it, dict):
            text = str(it.get("text") or it.get("name") or it)
        else:
            text = str(it)
        html += "<li>" + text + "</li>"
    html += "</ul>"
    return html


def _chip_list(items):
    if not items:
        return "<div class='cn-empty'>— нет —</div>"
    out = []
    for it in items:
        if isinstance(it, dict):
            text = str(it.get("name") or it.get("text") or it)
        else:
            text = str(it)
        out.append("<span class='cn-chip'>" + text + "</span>")
    return "<div class='cn-chips'>" + "".join(out) + "</div>"


def render():
    st.markdown(_CSS, unsafe_allow_html=True)

    char = _load()
    if not char:
        st.warning("Нет активного персонажа.")
        if st.button("В главное меню", key="cn_back_none"):
            st.session_state.screen = "main_menu"
            st.rerun()
        return

    st.markdown(
        "<div class='cn-wrap'>"
        "<div class='cn-title'>ХРОНИКИ</div>"
        "<div class='cn-sub'>"
        + str(char.get("name", "")) + " · дела и пути"
        "</div>"
        "</div>",
        unsafe_allow_html=True,
    )

    # --- Локация ---
    loc = char.get("location") or {}
    if isinstance(loc, str):
        loc = {"place": loc}
    world = loc.get("world") or loc.get("planet") or "—"
    place = loc.get("place") or loc.get("name") or "—"
    date = char.get("game_date") or "—"
    desc = loc.get("description") or loc.get("desc") or ""
    html = (
        "<div class='cn-wrap'><div class='cn-sec'>Текущая локация</div>"
        "<div class='cn-loc'>"
        "<div class='row'><span class='lbl'>Мир</span>"
        "<span class='val'>" + str(world) + "</span></div>"
        "<div class='row'><span class='lbl'>Место</span>"
        "<span class='val'>" + str(place) + "</span></div>"
        "<div class='row'><span class='lbl'>Дата</span>"
        "<span class='val'>" + str(date) + "</span></div>"
    )
    if desc:
        html += ("<div style='margin-top:8px;color:var(--fg-dim);'>"
                 + str(desc) + "</div>")
    html += "</div></div>"
    st.markdown(html, unsafe_allow_html=True)

    # --- NPC ---
    npcs = char.get("npcs") or []
    st.markdown(
        "<div class='cn-wrap'><div class='cn-sec'>Известные персоны</div>"
        + _list_items(npcs) +
        "</div>",
        unsafe_allow_html=True,
    )

    # --- Задачи ---
    quests = char.get("quests") or []
    st.markdown(
        "<div class='cn-wrap'><div class='cn-sec'>Задачи</div>"
        + _list_items(quests) +
        "</div>",
        unsafe_allow_html=True,
    )

    # --- Компаньоны ---
    comp = char.get("companions") or []
    st.markdown(
        "<div class='cn-wrap'><div class='cn-sec'>Спутники</div>"
        + _chip_list(comp) +
        "</div>",
        unsafe_allow_html=True,
    )

    # --- Эффекты ---
    effects = char.get("effects") or []
    st.markdown(
        "<div class='cn-wrap'><div class='cn-sec'>Активные эффекты</div>"
        + _chip_list(effects) +
        "</div>",
        unsafe_allow_html=True,
    )

    # --- Репутация ---
    rep = char.get("reputation") or {}
    if isinstance(rep, dict) and rep:
        st.markdown(
            "<div class='cn-wrap'><div class='cn-sec'>Репутация</div>"
            + _list_items([str(k) + ": " + str(v) for k, v in rep.items()])
            + "</div>",
            unsafe_allow_html=True,
        )

    # --- Дневник ---
    journal = char.get("journal") or []
    st.markdown("<div class='cn-wrap'><div class='cn-sec'>Дневник</div>",
                unsafe_allow_html=True)
    if journal:
        html = "<div class='cn-journal'>"
        for i, entry in enumerate(reversed(journal[-30:]), 1):
            if isinstance(entry, dict):
                text = str(entry.get("text") or entry)
            else:
                text = str(entry)
            html += ("<div class='cn-journal-entry'>"
                     "<span class='num'>" + str(i) + "</span>"
                     + text + "</div>")
        html += "</div>"
        st.markdown(html, unsafe_allow_html=True)
    else:
        st.markdown("<div class='cn-empty'>Записей пока нет.</div>",
                    unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # --- Кнопки ---
    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Персонаж", use_container_width=True,
                     key="cn_to_char"):
            st.session_state.screen = "character"
            st.rerun()
    with c2:
        if st.button("В игру", use_container_width=True,
                     type="primary", key="cn_to_game"):
            st.session_state.screen = "game"
            st.rerun()
