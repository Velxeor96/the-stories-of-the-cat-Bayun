# PATCH_15F
# ui/screens/loads.py — архив сохранённых персонажей.
from __future__ import annotations

import streamlit as st

from ui.theme import _current  # noqa: F401


LOADS_CSS = '''<style>
.loads-head {
    text-align: center; padding: 20px 20px 6px 20px;
}
.loads-title {
    font-family: Georgia, serif;
    font-size: 36px; letter-spacing: 5px;
    color: var(--fg);
    text-shadow: 0 0 20px var(--accent-glow);
    margin-bottom: 6px;
}
.loads-sub {
    color: var(--fg-dim); font-style: italic;
    font-size: 14px; letter-spacing: 2px;
    margin-bottom: 20px;
}
.loads-card {
    border: 1px solid var(--accent);
    border-radius: 8px;
    padding: 12px 18px;
    margin-bottom: 6px;
    background: rgba(255,255,255,0.03);
    text-align: left;
}
.loads-card .name {
    font-family: Georgia, serif;
    font-size: 20px; color: var(--fg);
}
.loads-card .meta {
    color: var(--fg-dim); font-size: 13px;
    margin-top: 4px;
}
</style>'''


def render() -> None:
    st.markdown(LOADS_CSS, unsafe_allow_html=True)
    login = st.session_state.get("user_login")
    if not login:
        st.warning("Нет активной сессии.")
        _back()
        return

    st.markdown(
        "<div class='loads-head'>"
        "<div class='loads-title'>АРХИВ</div>"
        "<div class='loads-sub'>сохранённые судьбы</div>"
        "</div>",
        unsafe_allow_html=True,
    )

    names = _names(login)
    if not names:
        st.info("Архив пуст. Создайте первого персонажа в разделе «Новая игра».")
        _back()
        return

    for name in names:
        char = _load(login, name)
        fname = (char or {}).get("faction", "") or ""
        sub = (char or {}).get("subfaction", "") or ""
        rank = (char or {}).get("rank", "") or ""
        parts = [p for p in (fname, sub, rank) if p]
        meta = " · ".join(str(p) for p in parts) if parts else "—"

        st.markdown(
            "<div class='loads-card'>"
            "<div class='name'>" + str(name) + "</div>"
            "<div class='meta'>" + meta + "</div>"
            "</div>",
            unsafe_allow_html=True,
        )

        c1, c2, c3 = st.columns([2, 1, 1])
        with c2:
            if st.button("Играть", key="loads_play_" + str(name),
                         use_container_width=True):
                _play(login, name)
        with c3:
            if st.button("Удалить", key="loads_del_" + str(name),
                         use_container_width=True):
                st.session_state["_pending_del"] = str(name)
                st.rerun()

    pending = st.session_state.get("_pending_del")
    if pending:
        _dialog_delete(login, pending)

    st.markdown("---")
    _back()


def _names(login):
    try:
        from persistence.characters import list_characters
        return list(list_characters(login))
    except Exception as e:
        print("[loads] list fail: " + type(e).__name__ + ": " + str(e))
        return []


def _load(login, name):
    try:
        from persistence.characters import load_character
        return load_character(login, name)
    except Exception as e:
        print("[loads] load fail: " + type(e).__name__ + ": " + str(e))
        return None


def _play(login, name):
    try:
        from persistence.settings import set_setting
        set_setting(login, "last_character", name)
    except Exception as e:
        print("[loads] set_setting fail: " + type(e).__name__ + ": " + str(e))
    st.session_state.active_character = name
    st.session_state.screen = "game"
    st.rerun()


def _back():
    if st.button("← В главное меню", key="loads_back"):
        st.session_state.pop("_pending_del", None)
        st.session_state.screen = "main_menu"
        st.rerun()


@st.dialog("Подтверждение удаления")
def _dialog_delete(login, name):
    st.write("Удалить персонажа «" + str(name) + "»? Действие необратимо.")
    c1, c2 = st.columns(2)
    if c1.button("Удалить", type="primary", key="dlg_del_yes",
                 use_container_width=True):
        try:
            from persistence.characters import delete_character
            delete_character(login, name)
        except Exception as e:
            st.error("Ошибка: " + type(e).__name__ + ": " + str(e))
            return
        if st.session_state.get("active_character") == name:
            st.session_state.pop("active_character", None)
        st.session_state.pop("_pending_del", None)
        st.rerun()
    if c2.button("Отмена", key="dlg_del_no", use_container_width=True):
        st.session_state.pop("_pending_del", None)
        st.rerun()
