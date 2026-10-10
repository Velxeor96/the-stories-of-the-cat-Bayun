"""ui/screens/psy.py — экран психосил (PATCH_83)."""
from __future__ import annotations


def _get_char(arg):
    """Универсальный разбор: state или char."""
    if not isinstance(arg, dict):
        return {}
    if isinstance(arg.get("character"), dict):
        return arg["character"]
    if isinstance(arg.get("char"), dict):
        return arg["char"]
    return arg


def _rerun():
    import streamlit as st
    try:
        st.rerun()
    except AttributeError:
        try:
            st.experimental_rerun()
        except Exception:
            pass


def render(char_or_state, on_result=None) -> None:
    """Отрисовывает экран психосил.

    char_or_state — словарь персонажа или state с полем character.
    on_result(text, result) — необязательный колбэк для чата.
    """
    import streamlit as st
    from services import psychic

    try:
        from services.psy_archetypes import ensure_psy_fields
        ensure_psy_fields(_get_char(char_or_state))
    except Exception:
        pass

    char = _get_char(char_or_state)

    st.markdown("## 🔮 Пси-силы")

    if not char:
        st.warning("Персонаж не загружен.")
        return

    if psychic.is_blocked(char):
        st.error(psychic.get_blocked_reason(char) or "Эта фракция не имеет психосил.")
        return

    rating = int(char.get("psy_rating", 0) or 0)
    if rating <= 0:
        st.info("Персонаж не является псайкером (psy_rating = 0).")
        return

    charge = int(char.get("psy_charge", 0) or 0)
    max_charge = rating * 3
    corruption = int(char.get("corruption", 0) or 0)
    insanity = int(char.get("insanity", 0) or 0)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("psy_rating", rating)
    c2.metric("Пси-заряд", str(charge) + " / " + str(max_charge))
    c3.metric("Порча", corruption)
    c4.metric("Безумие", insanity)

    fid = str(char.get("faction_id", "")).lower()
    if fid == "chaos":
        favor = psychic.get_all_favor(char)
        st.markdown("### Благосклонность богов")
        cols = st.columns(len(favor))
        for i, (god, lvl) in enumerate(favor.items()):
            cols[i].metric(god.capitalize(), "ур. " + str(lvl))

    catalog = psychic.full_catalog(char)
    if not catalog:
        st.warning("Нет доступных дисциплин.")
        return

    def _fire(pid):
        res = psychic.cast(char, pid)
        text = res.get("text") or res.get("reason", "")
        if on_result:
            try:
                on_result(text, res)
            except TypeError:
                on_result(text)
        else:
            st.session_state.setdefault("chat_pending", []).append(text)
        _rerun()

    for did, ddata in catalog.items():
        dname = ddata.get("name", did)
        favor_lvl = ddata.get("favor_level")
        header = "### " + dname
        if favor_lvl is not None:
            header += "  —  favor: ур. " + str(favor_lvl)
        st.markdown(header)

        for p in ddata.get("powers", []):
            pid = p["id"]
            available = p.get("available", False)
            cost = p.get("cost", 0)
            need_favor = p.get("favor_level", 0)
            min_r = p.get("min_rating", 1)

            col1, col2 = st.columns([5, 1])
            with col1:
                label = "**" + p["name"] + "** — " + str(cost) + " заряда"
                if not available:
                    if favor_lvl is not None and need_favor > favor_lvl:
                        label += "  🔒 (нужен favor " + str(need_favor) + ")"
                    elif min_r > rating:
                        label += "  🔒 (нужен psy_rating " + str(min_r) + ")"
                    else:
                        label += "  🔒"
                st.markdown(label)
                st.caption(p.get("desc", ""))
            with col2:
                if available:
                    if st.button("▶", key="cast_" + pid,
                                 help="Применить: " + p["name"]):
                        _fire(pid)
            st.markdown("---")


def render_entry() -> None:
    """PATCH_88: обёртка для app.py. Сама достаёт активного персонажа."""
    import streamlit as st
    login = st.session_state.get("user_login")
    name = st.session_state.get("active_character")
    if not login or not name:
        st.session_state.screen = "main_menu"
        st.rerun()
        return
    try:
        from persistence.characters import load_character
        char = load_character(login, name)
    except Exception as e:
        st.error("Не удалось загрузить персонажа: " + str(e))
        if st.button("В главное меню", key="psy_back_err"):
            st.session_state.screen = "main_menu"
            st.rerun()
        return
    render(char)
    st.markdown("---")
    if st.button("\u2190 В игру", key="psy_back", width="stretch"):
        st.session_state.screen = "game"
        st.rerun()
