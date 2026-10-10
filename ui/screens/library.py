# PATCH_26
"""ui/screens/library.py — поиск по базе знаний."""
from __future__ import annotations
import streamlit as st


def _goto(screen: str) -> None:
    st.session_state.screen = screen


def render():
    """Чистый экран Библиотеки: запрос + ответ одним блоком."""
    import streamlit as st

    st.markdown("## 📚 Библиотека")

    c1, c2 = st.columns([5, 1])
    with c2:
        if st.button("← Назад", key="library_back", width="stretch"):
            st.session_state.screen = "main_menu"
            try:
                st.rerun()
            except AttributeError:
                st.experimental_rerun()
            return
    with c1:
        query = st.text_input(
            "Запрос",
            key="library_query",
            placeholder="Например: Что такое Инквизиция?",
            label_visibility="collapsed",
        )

    if not query:
        st.caption("Введите запрос — я поищу ответ в архивах.")
        return

    with st.spinner("Ищу в архивах..."):
        results = _library_search(query, k=6)

    if not results:
        st.warning("Ничего не найдено.")
        return

    parts = []
    for item in results:
        text = _library_chunk_text(item)
        if text and text.strip():
            parts.append(_library_clean(text).strip())

    combined = "\n\n".join(p for p in parts if p)
    if not combined.strip():
        st.info("Ничего полезного в найденных фрагментах.")
        return

    st.markdown("---")
    st.markdown(combined)


def _library_search(query, k=6):
    """Поиск по RAG через services.rag.get_kb() (PATCH_86)."""
    try:
        from services.rag import get_kb
        kb = get_kb()
    except Exception as e:
        print("[library] get_kb fail: " + type(e).__name__ + ": " + str(e))
        return []

    # Определяем фракцию по запросу, если возможно
    fid = None
    try:
        from services.fallbacks import FACTIONS
        low = str(query).lower()
        for fk, data in FACTIONS.items():
            nm = str(data.get("name", "") or "").lower()
            if (nm and nm in low) or (fk and fk.lower() in low):
                fid = fk
                break
    except Exception:
        pass

    # Основной вызов (с faction)
    try:
        chunks = kb.search(query, top_k=k, faction=fid) or []
    except TypeError:
        try:
            chunks = kb.search(query, top_k=k) or []
        except Exception as e:
            print("[library] search fail: " + type(e).__name__ + ": " + str(e))
            return []
    except Exception as e:
        print("[library] search fail: " + type(e).__name__ + ": " + str(e))
        return []

    return chunks


def _library_chunk_text(item):
    """Достаёт текст из чанка (str / dict / tuple / object)."""
    if item is None:
        return ""
    if isinstance(item, str):
        return item
    if isinstance(item, tuple) and len(item) >= 1:
        return _library_chunk_text(item[0])
    if isinstance(item, dict):
        for k in ("page_content", "text", "content", "chunk", "document"):
            if item.get(k):
                return str(item[k])
        return ""
    for attr in ("page_content", "text", "content"):
        v = getattr(item, attr, None)
        if v:
            return str(v)
    return str(item)


def _library_clean(text):
    """Убирает «== Заголовок ==» из источника, оставляет текст."""
    out = []
    for line in str(text).split("\n"):
        s = line.strip()
        if len(s) >= 4 and set(s) <= set("= "):
            continue
        if s.startswith("==") and s.endswith("=="):
            title = s.strip("= ").strip()
            if title:
                out.append("**" + title + "**")
            continue
        out.append(line)
    return "\n".join(out).strip()

