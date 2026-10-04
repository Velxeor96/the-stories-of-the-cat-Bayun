# PATCH_41
"""ui/screens/progression.py — развитие: характеристики и таланты."""
from __future__ import annotations
import streamlit as st


def _goto(screen: str) -> None:
    st.session_state.screen = screen


RANKS = [
    (0, "Ранг 1"), (2000, "Ранг 2"), (5000, "Ранг 3"),
    (9000, "Ранг 4"), (14000, "Ранг 5"), (20000, "Ранг 6"),
    (27000, "Ранг 7"), (35000, "Ранг 8"),
]
CHAR_COSTS = {
    "Intermediate": [250, 500, 750],
    "Trained": [500, 750, 1000],
}


def _current_rank(spent: int) -> tuple:
    idx = 0
    for i, (thr, _) in enumerate(RANKS):
        if spent >= thr:
            idx = i
    return idx + 1, RANKS[idx][1]


def _next_threshold(spent: int):
    for thr, _ in RANKS:
        if spent < thr:
            return thr
    return RANKS[-1][0]


def _render_characteristics_tab(char: dict, login: str, char_name: str) -> None:
    from persistence.characters import save_character

    xp = int(char.get("xp", 0) or 0)
    stats = char.get("characteristics") or {}
    advances = char.get("advances") or {}

    st.markdown("### Улучшение характеристик (+5)")
    st.caption("Стоимость: «Intermediate» = 250/500/750, «Trained» = 500/750/1000 "
               "за 1-й, 2-й и 3-й уровень. Максимум +15.")

    for code in ["WS", "BS", "S", "T", "Ag", "Int", "Per", "WP", "Fel"]:
        cur = int(stats.get(code, 0) or 0)
        lvl = int((advances.get(code) or {}).get("count", 0))
        if lvl >= 3:
            cost_str = "макс"
        else:
            tier = "Trained" if lvl > 0 else "Intermediate"
            cost_str = str(CHAR_COSTS[tier][min(lvl, 2)])

        c1, c2, c3 = st.columns([3, 2, 1])
        with c1:
            st.markdown("**" + code + ":** " + str(cur)
                        + " (+" + str(lvl * 5) + " от прокачки)")
        with c2:
            st.caption("Стоимость: " + cost_str + " XP")
        with c3:
            if lvl < 3 and st.button("↑", key="adv_" + code,
                                     use_container_width=True):
                try:
                    cost = int(cost_str)
                except Exception:
                    st.error("Максимум.")
                    continue
                if xp < cost:
                    st.error("Мало XP.")
                else:
                    char["xp"] = xp - cost
                    char["xp_spent"] = int(char.get("xp_spent", 0) or 0) + cost
                    stats[code] = cur + 5
                    adv = char.setdefault("advances", {})
                    per = adv.setdefault(code, {})
                    per["count"] = lvl + 1
                    save_character(login, char_name, char)
                    st.rerun()


def _render_talents_tab(char: dict, login: str, char_name: str) -> None:
    from persistence.characters import save_character
    from services.talents_registry import list_available, buy_talent

    talents = list_available(char)
    if not talents:
        st.info("Для вашей фракции таланты ещё не добавлены. "
                "Мы работаем над этим — сейчас доступны для Некронов.")
        return

    owned = [t for t in talents if t["owned"]]
    avail = [t for t in talents if not t["owned"] and t["available"]]
    locked = [t for t in talents if not t["owned"] and not t["available"]]

    xp = int(char.get("xp", 0) or 0)
    st.markdown("**Свободно XP:** " + str(xp))
    st.caption("Изучено: " + str(len(owned))
               + " | Доступно: " + str(len(avail))
               + " | Заблокировано: " + str(len(locked)))

    # === Доступные ===
    if avail:
        st.markdown("### 🟢 Доступные")
        for t in avail:
            with st.container(border=True):
                c1, c2 = st.columns([5, 1])
                with c1:
                    st.markdown("**" + t["name"] + "** "
                                + "(Tier " + str(t["tier"]) + " · "
                                + t["category"] + ")")
                    st.caption(t["description"])
                    st.markdown("*Эффект:* " + t["effect"])
                with c2:
                    st.markdown("**" + str(t["cost"]) + " XP**")
                    if st.button("Изучить", key="talent_buy_" + t["id"],
                                 type="primary",
                                 use_container_width=True):
                        ok, msg = buy_talent(char, t["id"])
                        if ok:
                            save_character(login, char_name, char)
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)

    # === Заблокированные ===
    if locked:
        with st.expander("🔒 Заблокированные (" + str(len(locked)) + ")"):
            for t in locked:
                st.markdown("**" + t["name"] + "** — "
                            + str(t["cost"]) + " XP — *"
                            + t.get("reason", "") + "*")

    # === Изученные ===
    if owned:
        with st.expander("✓ Изученные (" + str(len(owned)) + ")"):
            for t in owned:
                st.markdown("✓ **" + t["name"] + "** — " + t["effect"])


def render() -> None:
    login = st.session_state.get("user_login")
    char_name = st.session_state.get("active_character")
    if not login or not char_name:
        _goto("main_menu")
        st.rerun()
        return

    from persistence.characters import load_character
    try:
        char = load_character(login, char_name)
    except Exception as e:
        st.error("Ошибка: " + str(e))
        return

    st.markdown("<h2 style='font-family:Georgia,serif;'>📈 Развитие</h2>",
                unsafe_allow_html=True)

    c1, c2 = st.columns([3, 1])
    with c1:
        xp = int(char.get("xp", 0) or 0)
        spent = int(char.get("xp_spent", 0) or 0)
        total = xp + spent
        rank, rank_name = _current_rank(total)
        nxt = _next_threshold(total)
        st.markdown("**Свободно XP:** " + str(xp)
                    + " · **Всего набрано:** " + str(total)
                    + " · **Ранг:** " + rank_name)
        if nxt > total:
            st.progress(min(100, total * 100 // max(1, nxt)) / 100.0)
    with c2:
        if st.button("← Назад", use_container_width=True):
            _goto("game")
            st.rerun()

    st.markdown("---")

    tab_chars, tab_talents = st.tabs(["📊 Характеристики", "🌟 Таланты"])
    with tab_chars:
        _render_characteristics_tab(char, login, char_name)
    with tab_talents:
        _render_talents_tab(char, login, char_name)
