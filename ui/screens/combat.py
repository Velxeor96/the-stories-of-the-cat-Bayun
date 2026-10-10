# PATCH_29
"""ui/screens/combat.py — экран боя + пси-силы + компаньоны."""
from __future__ import annotations
import streamlit as st
from services.combat import CombatState, ZONE_RU


def _goto(screen: str) -> None:
    st.session_state.screen = screen


def _init_combat(char: dict) -> CombatState:
    cs = CombatState()
    stats = char.get("characteristics") or {}
    ag = int(stats.get("Ag", 30))
    w = char.get("wounds") or {}
    hp = int(w.get("current", 10) or 10)
    hp_max = int(w.get("max", 10) or 10)

    fid = char.get("faction_id") or ""
    dmg = {"eldar": "1d10+2", "orks": "1d10+4", "tau": "1d10+3"}.get(
        fid, "1d10+3")

    cs.add(char.get("name", "Игрок"), hp_max, ag, "player",
           is_player=True, zone="mid", weapon_dmg=dmg)
    cs.participants[char.get("name", "Игрок")]["hp"] = hp

    # компаньоны
    comp = char.get("companions") or []
    for c in comp[:2]:
        if not isinstance(c, dict) or not c.get("alive", True):
            continue
        cs.add(c.get("name", "Спутник"), int(c.get("hp", 8)),
               25, "player", is_player=False, zone="mid",
               weapon_dmg="1d10+2")

    enemies = {
        "eldar": "Друкхари-налётчик", "imperium": "Отступник-гвардеец",
        "chaos": "Культист", "orks": "Орк-боевик",
        "tau": "Дрон-стражник", "necrons": "Некрон-воин",
        "drukhari": "Гладиатор Арены", "tyranids": "Генокрад-гибрид",
    }
    en = enemies.get(fid, "Противник")
    cs.add(en, 10, 25, "enemy", is_player=False, zone="mid",
           weapon_dmg="1d10+2")
    cs.roll_all()
    st.session_state["_combat_state"] = cs
    return cs


def _finalize(char: dict, login: str, char_name: str, cs: CombatState) -> list:
    events = []
    res = cs.player_result()
    try:
        from services.effects import add_injury, add_insanity, roll_injury
        w = char.setdefault("wounds", {})
        w["current"] = res.get("hp", w.get("current", 10))
        if cs.outcome == "win":
            char["xp"] = int(char.get("xp", 0) or 0) + 25
            events.append("+25 XP")
        hp_pct = res.get("hp_pct", 100)
        max_hit = res.get("max_hit_taken", 0)
        hp_max = max(1, res.get("hp_max", 1))
        if hp_pct < 25 or max_hit >= hp_max * 4 // 10:
            name, stat, pen = roll_injury()
            add_injury(char, name, stat, pen, source="бой")
            events.append("Травма: " + name)
        if hp_pct < 10:
            add_insanity(char, 3, "тяжёлый бой")
            events.append("+3 Безумия")
    except Exception as e:
        events.append("err: " + str(e))
    try:
        from persistence.characters import save_character
        save_character(login, char_name, char)
    except Exception as e:
        events.append("save err: " + str(e))
    return events


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

    if "_combat_state" not in st.session_state:
        _init_combat(char)
    cs = st.session_state.get("_combat_state")
    if not cs:
        _goto("game")
        st.rerun()
        return

    st.markdown("<h2 style='font-family:Georgia,serif;'>⚔️ Бой</h2>",
                unsafe_allow_html=True)
    c1, c2 = st.columns([2, 1])
    with c1:
        st.caption("Раунд " + str(cs.round)
                   + " · Ход: " + str(cs.current() or "—"))
    with c2:
        if st.button("← Выйти", width="stretch"):
            st.session_state.pop("_combat_state", None)
            _goto("game")
            st.rerun()

    for name, p in cs.participants.items():
        pct = max(0, p["hp"] * 100 // max(1, p["hp_max"]))
        icon = "🧑" if p["is_player"] else ("👹" if p["side"] == "enemy" else "🤝")
        st.markdown(
            "<div style='border:1px solid #333;border-radius:6px;"
            "padding:8px 12px;margin:4px 0;'>"
            + icon + " <b>" + name + "</b> · "
            + ZONE_RU.get(p["zone"], p["zone"])
            + " · HP " + str(p["hp"]) + "/" + str(p["hp_max"])
            + (" · <i>защита</i>" if p.get("defended") else "")
            + "</div>",
            unsafe_allow_html=True)
        st.progress(pct / 100.0)

    st.markdown("---")

    if cs.is_over():
        if cs.outcome == "win":
            st.success("🏆 Победа!")
        else:
            st.error("💀 Поражение.")
        if st.button("Вернуться в игру", type="primary",
                     width="stretch"):
            events = _finalize(char, login, char_name, cs)
            st.session_state.pop("_combat_state", None)
            tail = (" [" + "; ".join(events) + "]") if events else ""
            st.session_state["_pending_chat"] = (
                "[БОЙ ЗАВЕРШЁН. "
                + ("Победа." if cs.outcome == "win" else "Поражение.")
                + tail + "]")
            _goto("game")
            st.rerun()
        return

    cur = cs.current()
    is_player = cur and cs.participants.get(cur, {}).get("is_player", False)

    if not is_player:
        st.info("Ход противника...")
        if st.button("Продолжить", width="stretch"):
            pcs = [n for n, p in cs.participants.items()
                   if p["side"] == "player" and p["hp"] > 0]
            if cur and pcs:
                cs.attack(cur, pcs[0], 30)
            cs.next_turn()
            st.rerun()
        return

    st.markdown("**Твой ход.**")
    b1, b2, b3, b4 = st.columns(4)
    with b1:
        if st.button("⚔️ Атака", type="primary", width="stretch"):
            en = cs.alive_enemies("player")
            if en:
                stats = char.get("characteristics") or {}
                base = int(stats.get("BS", 30))
                cs.attack(cur, en[0], base)
                cs.next_turn()
                st.rerun()
    with b2:
        if st.button("➡️ Ближе", width="stretch"):
            cs.move(cur, "closer")
            st.rerun()
    with b3:
        if st.button("🛡 Защита", width="stretch"):
            cs.defend(cur)
            cs.next_turn()
            st.rerun()
    with b4:
        if st.button("⏭ Пропустить", width="stretch"):
            cs.next_turn()
            st.rerun()

    # пси-силы
    try:
        from services.psychic import get_powers, get_charge, PSY_POWERS, cast
        powers = get_powers(char)
        if powers:
            charge = get_charge(char)
            st.markdown("**🔮 Пси-силы** (заряд " + str(charge) + ")")
            pc = st.columns(min(4, len(powers)))
            for i, pkey in enumerate(powers[:4]):
                p = PSY_POWERS.get(pkey, {})
                with pc[i]:
                    label = p.get("name", pkey) + " (" + str(p.get("cost", 2)) + ")"
                    if st.button(label, key="psy_" + pkey,
                                 width="stretch"):
                        res = cast(char, pkey)
                        if not res.get("ok"):
                            st.error(res.get("reason", "ошибка"))
                        else:
                            st.success(res.get("text", ""))
                            if res.get("damage", 0) > 0:
                                en = cs.alive_enemies("player")
                                if en:
                                    cs.participants[en[0]]["hp"] = max(
                                        0,
                                        cs.participants[en[0]]["hp"]
                                        - int(res["damage"]))
                                    cs.log.append("Разрушитель: "
                                                  + str(res["damage"])
                                                  + " урона по " + en[0])
                            cs.next_turn()
                            from persistence.characters import save_character
                            save_character(login, char_name, char)
                            st.rerun()
    except Exception as _e:
        print("[combat] psy fail: " + type(_e).__name__)

    if cs.log:
        with st.expander("📜 Лог боя", expanded=True):
            for line in cs.log[-20:]:
                st.caption(line)
