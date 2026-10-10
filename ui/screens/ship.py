# PATCH_30B
"""ui/screens/ship.py — экран корабля."""
from __future__ import annotations
import streamlit as st

from services.ship import get_ship, warp_travel, repair, requisition


def _goto(screen: str) -> None:
    st.session_state.screen = screen


def _to_int(v, default=0):
    try:
        return int(str(v).strip() or default)
    except Exception:
        return default


def _bar(label, cur, mx):
    cur = _to_int(cur, 0)
    mx = _to_int(mx, 1) or 1
    pct = max(0, min(100, cur * 100 // mx))
    st.markdown("**" + label + ":** " + str(cur) + " / " + str(mx))
    st.progress(pct / 100.0)


def render() -> None:
    login = st.session_state.get("user_login")
    char_name = st.session_state.get("active_character")
    if not login or not char_name:
        _goto("main_menu")
        st.rerun()
        return

    from persistence.characters import load_character, save_character
    try:
        char = load_character(login, char_name)
    except Exception as e:
        st.error("Ошибка: " + str(e))
        return

    s = get_ship(char)

    st.markdown("<h2 style='font-family:Georgia,serif;'>🚀 Корабль</h2>",
                unsafe_allow_html=True)
    c1, c2 = st.columns([3, 1])
    with c1:
        st.markdown("**«" + str(s.get("name") or "—") + "»** · "
                    + str(s.get("class") or "—") + " · "
                    + str(s.get("type") or "—"))
        if s.get("description"):
            st.caption(str(s.get("description")))
    with c2:
        if st.button("← Назад", width="stretch"):
            _goto("game")
            st.rerun()

    _bar("Корпус", s.get("hull", 0), s.get("hull_max", 100))
    _bar("Экипаж", s.get("crew", 0), s.get("crew_max", 1))
    _bar("Мораль", s.get("morale", 0), s.get("morale_max", 100))
    _bar("Топливо", s.get("fuel", 0), s.get("fuel_max", 100))
    _bar("Припасы", s.get("supplies", 0), s.get("supplies_max", 100))

    st.markdown("---")
    st.markdown("**Вооружение:** "
                + ", ".join(str(w) for w in (s.get("weapons") or [])))
    st.markdown("**Системы:** "
                + ", ".join(str(f) for f in (s.get("features") or [])))

    st.markdown("---")
    st.markdown("### Действия")
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("🌀 Варп-прыжок", width="stretch"):
            res = warp_travel(char, distance_ly=5)
            if not res.get("ok"):
                st.error(res.get("reason", "ошибка"))
            else:
                st.success(res.get("event", ""))
                save_character(login, char_name, char)
                st.rerun()
    with c2:
        if st.button("🔧 Ремонт (5 припасов)", width="stretch"):
            res = repair(char, 20)
            if not res.get("ok"):
                st.error(res.get("reason", "ошибка"))
            else:
                st.success("Корпус: " + str(res.get("hull", "?")))
                save_character(login, char_name, char)
                st.rerun()
    with c3:
        if st.button("📦 Реквизиция (10 припасов)", width="stretch"):
            res = requisition(char)
            if not res.get("ok"):
                st.error(res.get("reason", "ошибка"))
            else:
                st.success("Получено " + str(res.get("gold", 0)) + " тронов")
                save_character(login, char_name, char)
                st.rerun()
