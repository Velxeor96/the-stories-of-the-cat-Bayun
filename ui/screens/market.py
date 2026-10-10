# PATCH_26
"""ui/screens/market.py — рынок / реквизиция."""
from __future__ import annotations
import streamlit as st

from services.trade import CATALOG, get_price, try_buy, sell_item


def _goto(screen: str) -> None:
    st.session_state.screen = screen


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

    st.markdown("<h2 style='font-family:Georgia,serif;'>🏪 Рынок</h2>",
                unsafe_allow_html=True)
    c1, c2 = st.columns([3, 1])
    with c1:
        st.markdown("**Троны:** " + str(int(char.get("money", 0) or 0)))
    with c2:
        if st.button("← Назад", width="stretch"):
            _goto("game")
            st.rerun()

    fel = int((char.get("characteristics") or {}).get("Fel", 30))

    st.markdown("### Товары")
    for i, item in enumerate(CATALOG):
        price = get_price(item, fel)
        c1, c2, c3 = st.columns([4, 2, 1])
        with c1:
            st.markdown("**" + item["name"] + "**")
        with c2:
            st.markdown("Цена: " + str(price) + " тронов")
        with c3:
            if st.button("Купить", key="buy_" + str(i),
                         width="stretch"):
                res = try_buy(char, item, fel)
                if not res.get("ok"):
                    st.error(res.get("reason", "ошибка"))
                else:
                    save_character(login, char_name, char)
                    st.success("Куплено: " + item["name"])
                    st.rerun()

    st.markdown("---")
    st.markdown("### Продать из инвентаря")
    try:
        from services.inventory import get_inventory, CATEGORIES, CATEGORY_RU
        inv = get_inventory(char)
        had_any = False
        for cat in CATEGORIES:
            for it in inv.get(cat) or []:
                nm = it.get("name") if isinstance(it, dict) else str(it)
                c1, c2, c3 = st.columns([4, 2, 1])
                with c1:
                    st.markdown(nm)
                with c2:
                    st.caption(CATEGORY_RU.get(cat, cat))
                with c3:
                    if st.button("Продать", key="sell_" + cat + "_"
                                 + str(nm)[:20], width="stretch"):
                        res = sell_item(char, nm, fel)
                        if not res.get("ok"):
                            st.error(res.get("reason", "ошибка"))
                        else:
                            save_character(login, char_name, char)
                            st.success("Продано за "
                                       + str(res["price"]) + " тронов")
                            st.rerun()
                had_any = True
        if not had_any:
            st.caption("Инвентарь пуст.")
    except Exception as e:
        st.warning("Ошибка инвентаря: " + str(e))
