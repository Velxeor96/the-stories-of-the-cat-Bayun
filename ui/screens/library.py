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
        if st.button("← Назад", key="library_back", use_container_width=True):
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
    """Универсальный поиск по RAG-хранилищу."""
    candidates = [
        ("services.rag", ("search", "query", "retrieve", "get_context", "find")),
        ("services.knowledge", ("search", "query", "retrieve")),
        ("services.library", ("search", "query", "retrieve")),
        ("services.orchestrator", ("rag_query", "rag_search", "search")),
        ("orchestrator", ("rag_query", "rag_search", "search")),
    ]
    for mod_name, fn_names in candidates:
        try:
            mod = __import__(mod_name, fromlist=["*"])
        except Exception:
            continue
        for fn_name in fn_names:
            fn = getattr(mod, fn_name, None)
            if not callable(fn):
                continue
            for kw in ({"k": k}, {"top_k": k}, {}):
                try:
                    out = fn(query, **kw)
                except TypeError:
                    continue
                except Exception:
                    continue
                if out:
                    return out
    return []


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

