# PATCH_26
"""ui/screens/library.py — поиск по базе знаний."""
from __future__ import annotations
import streamlit as st


def _goto(screen: str) -> None:
    st.session_state.screen = screen


def render() -> None:
    login = st.session_state.get("user_login")
    if not login:
        _goto("main_menu")
        st.rerun()
        return

    st.markdown("<h2 style='font-family:Georgia,serif;'>📚 Библиотека</h2>",
                unsafe_allow_html=True)
    st.caption("Поиск по архивам. Введите запрос — увидите выдержки из базы.")

    c1, c2 = st.columns([4, 1])
    with c1:
        query = st.text_input("Запрос", key="lib_query",
                              placeholder="Кто такие друкхари?")
    with c2:
        if st.button("← Назад", use_container_width=True):
            _goto("game")
            st.rerun()

    if not query or not query.strip():
        st.info("Введите запрос.")
        return

    try:
        from services.rag import get_kb
        kb = get_kb()
    except Exception as e:
        st.error("База недоступна: " + str(e))
        return

    # Определяем фракцию по запросу, если возможно
    fid = None
    try:
        from services.fallbacks import FACTIONS
        low = query.lower()
        for k, data in FACTIONS.items():
            if data["name"].lower() in low or k in low:
                fid = k
                break
    except Exception:
        pass

    try:
        chunks = kb.search(query, top_k=5, faction=fid) or []
    except Exception as e:
        st.error("Поиск не удался: " + str(e))
        return

    if not chunks:
        st.warning("Ничего не найдено. Попробуйте другую формулировку.")
        return

    for c in chunks:
        src = c.get("source") or "—"
        fac = c.get("faction") or "general"
        text = c.get("text") or ""
        with st.expander("[" + str(fac) + "] " + str(src), expanded=True):
            st.markdown(text[:1500])
