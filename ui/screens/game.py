# PATCH_15Z
# ui/screens/game.py — игровой экран: сайдбар + чат с Мастером.
from __future__ import annotations

import json
import random
import time
from typing import Optional

import streamlit as st

from persistence.chats import append_turn, load_history
from persistence.characters import CharacterError, load_character
from services.fallbacks import CHARACTERISTIC_NAMES
from services.orchestrator import Orchestrator
from ui.roll_card import (
    render_roll_card,
    render_spinner_html,
    render_dialog_await,
    render_dialog_rolling,
)
from ui.loading_screen import full_css, full_html, get_phrases


_ROLL_MARKER = "<!--ROLLCARD:"
_ROLL_MARKER_END = "-->"


# =====================================================================
# CSS
# =====================================================================
_SIDEBAR_CSS = '''<style>
.gx-sec {
    font-size: 11px; letter-spacing: 3px;
    color: var(--accent); text-transform: uppercase;
    margin: 14px 0 6px 0;
}
.gx-loc {
    border: 1px solid var(--border);
    border-left: 3px solid var(--accent);
    border-radius: 6px;
    padding: 8px 12px; margin: 6px 0 10px 0;
    background: rgba(255,255,255,0.02);
    font-size: 12px; color: var(--fg-dim);
    line-height: 1.55;
}
.gx-loc .row { display: flex; justify-content: space-between; padding: 1px 0; }
.gx-loc .lbl { color: var(--fg-dim); letter-spacing: 1px; font-size: 11px; }
.gx-loc .val { color: var(--fg); }
.gx-bar-wrap { display: flex; flex-direction: column; margin: 6px 0 10px 0; }
.gx-bar-head {
    display: flex; justify-content: space-between;
    font-size: 11px; letter-spacing: 2px;
    color: var(--fg-dim); text-transform: uppercase;
    margin-bottom: 4px;
}
.gx-bar-head .val { color: var(--fg); font-weight: 600; }
.gx-bar-track {
    width: 100%; height: 10px;
    background: rgba(255,255,255,0.06);
    border: 1px solid var(--border);
    border-radius: 4px; overflow: hidden;
}
.gx-bar-fill {
    height: 100%;
    transition: width 0.35s ease;
}
.gx-bar-fill.hp { background: linear-gradient(90deg, #5b1010 0%, #c83838 100%);
    box-shadow: 0 0 10px rgba(200,56,56,0.45); }
.gx-bar-fill.hp.low {
    background: linear-gradient(90deg, #7a0a0a 0%, #ff4040 100%);
    animation: gxPulse 1.2s ease-in-out infinite;
}
.gx-bar-fill.fate {
    background: linear-gradient(90deg, #6b4a0a 0%, #e0b040 100%);
    box-shadow: 0 0 10px rgba(224,176,64,0.4);
}
.gx-bar-fill.xp {
    background: linear-gradient(90deg, #103a52 0%, #4aa6d8 100%);
    box-shadow: 0 0 10px rgba(74,166,216,0.4);
}
@keyframes gxPulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.7; }
}
.gx-slot {
    border: 1px dashed var(--border);
    border-radius: 6px;
    padding: 6px 10px; margin: 4px 0;
    background: rgba(255,255,255,0.02);
    font-size: 12px;
}
.gx-slot .lbl { color: var(--fg-dim); letter-spacing: 1px; font-size: 11px; }
.gx-slot .val { color: var(--fg); }
.gx-chip {
    display: inline-block;
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 3px 10px; margin: 2px 3px 2px 0;
    font-size: 12px; color: var(--fg);
    background: rgba(255,255,255,0.03);
}
.gx-skill {
    display: flex; justify-content: space-between;
    border-bottom: 1px solid rgba(255,255,255,0.06);
    padding: 3px 0; font-size: 12px;
}
.gx-skill .name { color: var(--fg); }
.gx-skill .val { color: var(--accent-soft); font-weight: 600; }
</style>'''


# =====================================================================
# Helpers для истории чата
# =====================================================================
def _pack_narrative(narrative: str, roll: Optional[dict]) -> str:
    if not roll:
        return narrative
    try:
        payload = json.dumps(roll, ensure_ascii=False)
    except Exception:
        return narrative
    return narrative + "\n" + _ROLL_MARKER + payload + _ROLL_MARKER_END


def _unpack_narrative(text: str) -> tuple:
    if _ROLL_MARKER not in text:
        return text, None
    head, tail = text.split(_ROLL_MARKER, 1)
    if _ROLL_MARKER_END not in tail:
        return text, None
    payload, _ = tail.split(_ROLL_MARKER_END, 1)
    try:
        roll = json.loads(payload)
    except Exception:
        return text, None
    return head.rstrip(), roll


def _save_char(login: str, name: str, char: dict) -> bool:
    try:
        from persistence.characters import save_character
        save_character(login, name, char)
        return True
    except Exception as e:
        print("[game] save_character fail: " + type(e).__name__ + ": " + str(e))
        return False


# =====================================================================
# Bars / Location / Armour / Equipment
# =====================================================================
def _bar(label: str, cur: int, mx: int, cls: str) -> str:
    if mx <= 0:
        pct = 0
    else:
        pct = int(max(0, min(100, cur * 100.0 / mx)))
    low = ""
    if cls == "hp" and mx > 0 and cur * 100.0 / mx <= 25:
        low = " low"
    return (
        "<div class='gx-bar-wrap'>"
        "<div class='gx-bar-head'><span>" + label + "</span>"
        "<span class='val'>" + str(cur) + " / " + str(mx) + "</span></div>"
        "<div class='gx-bar-track'><div class='gx-bar-fill " + cls + low +
        "' style='width:" + str(pct) + "%;'></div></div>"
        "</div>"
    )


def _render_bars(char: dict) -> None:
    w = char.get("wounds") or {}
    fp = char.get("fate_points") or {}
    xp = int(char.get("xp", 0) or 0)
    xp_next = 500
    html = ""
    html += _bar("Раны", int(w.get("current", 0)), int(w.get("max", 0)), "hp")
    html += _bar("Судьба", int(fp.get("current", 0)), int(fp.get("max", 0)), "fate")
    html += _bar("Опыт", xp, xp_next, "xp")
    st.markdown(html, unsafe_allow_html=True)


def _render_location(char: dict) -> None:
    loc = char.get("location") or {}
    if isinstance(loc, str):
        loc = {"place": loc}
    world = loc.get("world") or loc.get("planet") or "—"
    place = loc.get("place") or loc.get("name") or "—"
    date = char.get("game_date") or "—"
    desc = loc.get("description") or loc.get("desc") or ""
    html = (
        "<div class='gx-loc'>"
        "<div class='row'><span class='lbl'>МИР</span>"
        "<span class='val'>" + str(world) + "</span></div>"
        "<div class='row'><span class='lbl'>МЕСТО</span>"
        "<span class='val'>" + str(place) + "</span></div>"
        "<div class='row'><span class='lbl'>ДАТА</span>"
        "<span class='val'>" + str(date) + "</span></div>"
    )
    if desc:
        html += ("<div style='margin-top:6px;color:var(--fg-dim);'>"
                 + str(desc) + "</div>")
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


def _armour_slots(char: dict) -> dict:
    a = char.get("armour")
    if not isinstance(a, dict):
        a = {}
    return {
        "head": a.get("head") or "",
        "body": a.get("body") or "",
        "arms": a.get("arms") or "",
        "legs": a.get("legs") or "",
        "notes": a.get("notes") or "",
    }


def _slot_label(k: str) -> str:
    return {
        "head": "Голова", "body": "Торс",
        "arms": "Руки", "legs": "Ноги",
    }.get(k, k)


def _item_name(it) -> str:
    if isinstance(it, str):
        return it
    if isinstance(it, dict):
        return str(it.get("name") or it.get("title") or "предмет")
    return str(it)


def _render_armour(char: dict, login: str, char_name: str) -> None:
    slots = _armour_slots(char)
    html = ""
    for k in ("head", "body", "arms", "legs"):
        v = slots.get(k) or "—"
        html += (
            "<div class='gx-slot'>"
            "<div class='lbl'>" + _slot_label(k) + "</div>"
            "<div class='val'>" + str(v) + "</div>"
            "</div>"
        )
    st.markdown(html, unsafe_allow_html=True)
    equip = char.get("equipment") or []
    if equip:
        with st.popover("Надеть из рюкзака", use_container_width=True):
            idx = st.selectbox(
                "Предмет",
                options=list(range(len(equip))),
                format_func=lambda i: _item_name(equip[i]),
                key="armour_equip_pick",
            )
            slot = st.selectbox(
                "Слот",
                options=["head", "body", "arms", "legs"],
                format_func=_slot_label,
                key="armour_equip_slot",
            )
            if st.button("Надеть", key="armour_equip_do"):
                item = equip.pop(idx)
                armour = char.setdefault("armour", {})
                armour[slot] = _item_name(item)
                if _save_char(login, char_name, char):
                    st.rerun()
    for k in ("head", "body", "arms", "legs"):
        if slots.get(k):
            if st.button("Снять: " + _slot_label(k),
                         key="armour_off_" + k,
                         use_container_width=True):
                armour = char.setdefault("armour", {})
                removed = armour.get(k)
                armour[k] = ""
                if removed:
                    char.setdefault("equipment", []).append(removed)
                if _save_char(login, char_name, char):
                    st.rerun()


def _render_equipment(char: dict, login: str, char_name: str) -> None:
    equip = char.get("equipment") or []
    if equip:
        chips = "".join(
            "<span class='gx-chip'>" + _item_name(it) + "</span>"
            for it in equip
        )
        st.markdown(chips, unsafe_allow_html=True)
    else:
        st.caption("Рюкзак пуст.")
    with st.popover("Добавить предмет", use_container_width=True):
        nm = st.text_input("Название", key="equip_add_name")
        if st.button("Добавить", key="equip_add_do") and nm.strip():
            char.setdefault("equipment", []).append(nm.strip())
            if _save_char(login, char_name, char):
                st.rerun()
    if equip:
        with st.popover("Удалить предмет", use_container_width=True):
            idx = st.selectbox(
                "Предмет",
                options=list(range(len(equip))),
                format_func=lambda i: _item_name(equip[i]),
                key="equip_del_pick",
            )
            if st.button("Удалить", key="equip_del_do"):
                equip.pop(idx)
                if _save_char(login, char_name, char):
                    st.rerun()


# =====================================================================
# Weapons
# =====================================================================
def _weapon_get(w, key: str, default=None):
    if isinstance(w, dict):
        return w.get(key, default)
    return default


def _weapon_name(w) -> str:
    if isinstance(w, str):
        return w
    if isinstance(w, dict):
        return str(w.get("name") or w.get("title") or "Оружие")
    return str(w)


def _weapon_skill(w, char: dict) -> str:
    sk = _weapon_get(w, "skill")
    if sk:
        return str(sk)
    kind = str(_weapon_get(w, "type", "") or "").lower()
    if "melee" in kind or "рук" in kind:
        return "WS"
    return "BS"


def _weapon_damage(w):
    return _weapon_get(w, "damage") or _weapon_get(w, "dmg") or ""


@st.dialog("Атака")
def _attack_dialog(login: str, char_name: str, char: dict) -> None:
    w = st.session_state.get("_attack_weapon")
    if not w:
        st.write("Нет выбранного оружия.")
        if st.button("Закрыть", key="atk_close0"):
            st.session_state.pop("_attack_open", None)
            st.session_state.pop("_attack_weapon", None)
            st.rerun()
        return
    name = _weapon_name(w)
    skill = _weapon_skill(w, char)
    dmg = _weapon_damage(w)
    st.markdown("**" + name + "**")
    st.caption("Навык: " + skill + ((" · урон: " + str(dmg)) if dmg else ""))

    diffs = ["Trivial", "Easy", "Routine", "Ordinary",
             "Challenging", "Difficult", "Hard", "Very Hard", "Hellish"]
    labels = {
        "Trivial": "Тривиальная (+60)",
        "Easy": "Лёгкая (+30)",
        "Routine": "Рутинная (+20)",
        "Ordinary": "Обычная (+10)",
        "Challenging": "Вызов (0)",
        "Difficult": "Трудная (-10)",
        "Hard": "Тяжёлая (-20)",
        "Very Hard": "Очень тяжёлая (-30)",
        "Hellish": "Адская (-60)",
    }
    diff = st.selectbox("Сложность", options=diffs, index=3,
                        format_func=lambda d: labels.get(d, d),
                        key="atk_diff")

    if st.button("Бросить", type="primary", key="atk_roll",
                 use_container_width=True):
        base = 45
        try:
            stats = char.get("characteristics") or {}
            base = int(stats.get(skill, stats.get(skill.upper(), 45)) or 45)
        except Exception:
            base = 45
        from core.roll_engine import check as roll_check
        r = roll_check(base, difficulty=diff, reason=name)
        st.session_state["_attack_result"] = r.to_dict()

    res = st.session_state.get("_attack_result")
    if res:
        render_roll_card(res, fresh=True)
        if res.get("success"):
            damage_line = ""
            if dmg:
                try:
                    import random as _rnd
                    parts = str(dmg).split("+")
                    total = 0
                    rolls = []
                    for p in parts:
                        p = p.strip().lower()
                        if "d" in p:
                            a, b = p.split("d", 1)
                            n = int(a) if a else 1
                            f = int(b)
                            s = sum(_rnd.randint(1, f) for _ in range(n))
                            total += s
                            rolls.append(p + "=" + str(s))
                        elif p.isdigit():
                            total += int(p)
                            rolls.append(p)
                    damage_line = "Урон: " + " + ".join(rolls) + " = " + str(total)
                except Exception:
                    damage_line = "Урон: " + str(dmg)
            if damage_line:
                st.info(damage_line)
            if st.button("Отправить Мастеру", type="primary",
                         key="atk_send", use_container_width=True):
                msg = ("Атакую: " + name + " [" + skill + " " + str(res.get("roll"))
                       + "/" + str(res.get("target")) + " " + diff + "]"
                       + ((" " + damage_line) if damage_line else ""))
                st.session_state["_pending_chat"] = msg
                st.session_state.pop("_attack_open", None)
                st.session_state.pop("_attack_weapon", None)
                st.session_state.pop("_attack_result", None)
                st.rerun()
    if st.button("Отмена", key="atk_cancel", use_container_width=True):
        st.session_state.pop("_attack_open", None)
        st.session_state.pop("_attack_weapon", None)
        st.session_state.pop("_attack_result", None)
        st.rerun()


def _render_weapons(char: dict, login: str, char_name: str) -> None:
    weapons = char.get("weapons") or []
    if not weapons:
        st.caption("Оружия нет.")
        return
    for i, w in enumerate(weapons):
        name = _weapon_name(w)
        dmg = _weapon_damage(w)
        st.markdown(
            "<div class='gx-slot'><div class='lbl'>" + name + "</div>"
            + ("<div class='val'>Урон: " + str(dmg) + "</div>" if dmg else "")
            + "</div>",
            unsafe_allow_html=True,
        )
        if st.button("Атаковать: " + name,
                     key="atk_btn_" + str(i),
                     use_container_width=True):
            st.session_state["_attack_open"] = True
            st.session_state["_attack_weapon"] = w
            st.session_state.pop("_attack_result", None)
            st.rerun()


# =====================================================================
# Skills / Abilities
# =====================================================================
def _skill_name(s) -> str:
    if isinstance(s, str):
        return s
    if isinstance(s, dict):
        return str(s.get("name") or s.get("title") or "навык")
    return str(s)


def _skill_value(s, char: dict) -> str:
    if isinstance(s, dict):
        v = s.get("value") or s.get("total")
        if isinstance(v, (int, float)):
            return str(int(v))
        ch = s.get("characteristic") or s.get("char")
        if ch:
            stats = char.get("characteristics") or {}
            base = stats.get(ch, stats.get(str(ch).upper()))
            if isinstance(base, (int, float)):
                return str(int(base))
    return ""


def _render_skills(char: dict, login: str, char_name: str) -> None:
    skills = char.get("skills") or []
    if not skills:
        st.caption("Навыков нет.")
        return
    for i, s in enumerate(skills):
        nm = _skill_name(s)
        v = _skill_value(s, char)
        st.markdown(
            "<div class='gx-skill'><span class='name'>" + nm + "</span>"
            "<span class='val'>" + v + "</span></div>",
            unsafe_allow_html=True,
        )
        if st.button("Проверить: " + nm,
                     key="sk_btn_" + str(i),
                     use_container_width=True):
            st.session_state["_pending_chat"] = "Проверяю: " + nm
            st.rerun()


def _render_abilities(char: dict) -> None:
    psy = char.get("psychic_powers") or []
    tal = char.get("talents") or []
    psy_rating = int(char.get("psy_rating", 0) or 0)
    if psy_rating > 0 and psy:
        st.markdown("<div class='gx-sec'>Психосилы (PSY "
                    + str(psy_rating) + ")</div>", unsafe_allow_html=True)
        chips = "".join("<span class='gx-chip'>" + _skill_name(p) + "</span>"
                        for p in psy)
        st.markdown(chips, unsafe_allow_html=True)
    if tal:
        st.markdown("<div class='gx-sec'>Способности</div>",
                    unsafe_allow_html=True)
        chips = "".join("<span class='gx-chip'>" + _skill_name(t) + "</span>"
                        for t in tal)
        st.markdown(chips, unsafe_allow_html=True)
    if not psy and not tal and psy_rating == 0:
        st.caption("Способностей нет.")


# =====================================================================
# Sidebar
# =====================================================================
def _render_sidebar(char: dict, login: str, char_name: str) -> None:
    with st.sidebar:
        st.markdown("### " + str(char.get("name", "—")))
        st.caption(str(char.get("faction", "")) + " · "
                   + str(char.get("subfaction", "")))
        st.caption(
            ("Мужской" if char.get("gender") == "male" else "Женский")
            + " · " + str(char.get("age", "?")) + " лет"
        )
        st.markdown("<div class='gx-sec'>Локация</div>",
                    unsafe_allow_html=True)
        _render_location(char)
        _render_bars(char)
        st.markdown("<div class='gx-sec'>Характеристики</div>",
                    unsafe_allow_html=True)
        stats = char.get("characteristics") or {}
        cols = st.columns(3)
        for i, (key, val) in enumerate(stats.items()):
            with cols[i % 3]:
                st.metric(CHARACTERISTIC_NAMES.get(key, key), val)
        with st.expander("Экипировка", expanded=False):
            _render_armour(char, login, char_name)
            st.markdown("---")
            _render_equipment(char, login, char_name)
        with st.expander("Оружие", expanded=False):
            _render_weapons(char, login, char_name)
        with st.expander("Навыки", expanded=False):
            _render_skills(char, login, char_name)
        with st.expander("Способности", expanded=False):
            _render_abilities(char)
        st.markdown("---")
        if st.button("Развитие", use_container_width=True,
                     key="game_progression"):
            st.session_state.screen = "progression"
            st.rerun()
        if st.button("Обучение", use_container_width=True, key="game_tut"):
            st.session_state.tutorial_mode = True
            st.session_state.screen = "tutorial"
            st.rerun()
        if st.button("Выйти в меню", use_container_width=True, key="game_exit"):
            _logout()


def _logout() -> None:
    for k in ("user_login", "active_character", "orchestrator",
              "tutorial_mode", "roll_card_variant"):
        st.session_state.pop(k, None)
    st.session_state.screen = "main_menu"
    st.rerun()


def _get_orch() -> Orchestrator:
    if "orchestrator" not in st.session_state:
        from core.config import Config
        cfg = Config.load()
        st.session_state.orchestrator = Orchestrator(cfg, use_rag=True)
    return st.session_state.orchestrator


def _render_messages(history: list) -> None:
    for msg in history:
        role = msg.get("role")
        text = msg.get("text", "")
        if role == "player":
            with st.chat_message("user"):
                st.markdown(text)
            continue
        clean_text, roll = _unpack_narrative(text)
        with st.chat_message("assistant"):
            if roll:
                render_roll_card(roll, fresh=False)
            st.markdown(clean_text)


# =====================================================================
# Interactive roll dialog
# =====================================================================
@st.dialog("Бросок d100")
def _roll_dialog() -> None:
    pend = st.session_state.get("_roll_dialog_state")
    if not pend:
        st.session_state.pop("_roll_dialog_state", None)
        st.rerun()
        return

    phase = pend.get("phase", "await")
    roll = pend.get("roll")
    cmd_info = pend.get("command_info", {})

    if phase == "await":
        render_dialog_await(cmd_info)
        c1, c2 = st.columns(2)
        with c1:
            if st.button("БРОСИТЬ", type="primary",
                         use_container_width=True, key="rd_go"):
                pend["phase"] = "rolling"
                st.session_state["_roll_dialog_state"] = pend
                st.rerun()
        with c2:
            if st.button("ОТМЕНИТЬ", use_container_width=True, key="rd_cancel"):
                st.session_state.pop("_roll_dialog_state", None)
                st.rerun()
        return

    if phase == "rolling":
        placeholder = st.empty()
        for i in range(30):
            n = random.randint(1, 100)
            with placeholder:
                render_dialog_rolling(n)
            time.sleep(0.08)
        pend["phase"] = "reveal"
        st.session_state["_roll_dialog_state"] = pend
        st.rerun()
        return

    if phase == "reveal":
        if roll:
            render_roll_card(roll, fresh=True)
        time.sleep(2.5)
        pend["phase"] = "done"
        st.session_state["_roll_dialog_state"] = pend
        st.rerun()
        return

    if phase == "done":
        _finalize_pending_turn(pend)
        return

    st.session_state.pop("_roll_dialog_state", None)
    st.rerun()


def _finalize_pending_turn(pend: dict) -> None:
    login = st.session_state.get("user_login")
    char_name = pend.get("char_name") or st.session_state.get("active_character")
    prompt = pend.get("prompt", "")
    narrative = pend.get("narrative", "")
    roll_dict = pend.get("roll")
    if login and char_name and prompt:
        try:
            append_turn(login, char_name, prompt,
                        _pack_narrative(narrative, roll_dict))
        except Exception as e:
            print("[game] append_turn fail: "
                  + type(e).__name__ + ": " + str(e))
    st.session_state.pop("_roll_dialog_state", None)
    st.rerun()




def _run_game_loading() -> None:
    st.markdown(full_css(), unsafe_allow_html=True)
    try:
        from ui.theme import _current
        theme = _current()
    except Exception:
        theme = "dark"
    pool = get_phrases(theme)
    import random as _rnd
    phrase = pool[0]
    st.markdown(
        full_html(theme, 100, phrase,
                  subtitle="когитатор готовит сессию"),
        unsafe_allow_html=True,
    )
    try:
        _get_orch()
    except Exception as e:
        print("[game] orch init fail: "
              + type(e).__name__ + ": " + str(e))


# =====================================================================
# render
# =====================================================================
def render() -> None:
    login = st.session_state.get("user_login")
    char_name = st.session_state.get("active_character")
    if not login or not char_name:
        st.session_state.screen = "main_menu"
        st.rerun()
        return

    if st.session_state.get("_game_loading_pending"):
        _run_game_loading()
        st.session_state.pop("_game_loading_pending", None)
        st.session_state["_game_loading_ready"] = True
        st.rerun()
        return

    if st.session_state.pop("_game_loading_ready", False):
        pass

    try:
        char = load_character(login, char_name)
    except CharacterError as e:
        st.error(str(e))
        if st.button("К созданию персонажа"):
            st.session_state.screen = "wizard"
            st.rerun()
        return

    st.markdown(_SIDEBAR_CSS, unsafe_allow_html=True)

    if st.session_state.get("_roll_dialog_state"):
        _roll_dialog()
        return

    if st.session_state.get("_attack_open"):
        _attack_dialog(login, char_name, char)
        return

    _render_sidebar(char, login, char_name)

    st.markdown(
        "<h2 style='font-family: Georgia, serif;'>"
        + str(char.get("name", "")) + "</h2>",
        unsafe_allow_html=True,
    )

    history = load_history(login, char_name)

    init_key = "__init_scene__" + str(login) + "__" + str(char_name)
    if not history and init_key not in st.session_state:
        st.session_state[init_key] = True
        placeholder = st.empty()
        with placeholder:
            st.markdown(render_spinner_html(), unsafe_allow_html=True)
        try:
            orch = _get_orch()
            result = orch.process_turn("Начало приключения.", char, history=[])
        finally:
            placeholder.empty()
        roll_dict = result.roll.to_dict() if result.roll else None
        narrative = _pack_narrative(result.narrative, roll_dict)
        append_turn(login, char_name, "Начало приключения.", narrative)
        history = load_history(login, char_name)

    _render_messages(history)

    pending = st.session_state.pop("_pending_chat", None)
    prompt = st.chat_input("Что делает твой персонаж?") or pending

    if prompt:
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            placeholder = st.empty()
            with placeholder:
                st.markdown(render_spinner_html(), unsafe_allow_html=True)
            try:
                orch = _get_orch()
                result = orch.process_turn(prompt, char, history=history)
            finally:
                placeholder.empty()

        if result.roll:
            roll_dict = result.roll.to_dict()
            cmd = result.command
            st.session_state["_roll_dialog_state"] = {
                "phase": "await",
                "prompt": prompt,
                "narrative": result.narrative,
                "roll": roll_dict,
                "char_name": char_name,
                "command_info": {
                    "skill": str(getattr(cmd, "skill", "") or "Проверка")
                             if cmd else "Проверка",
                    "difficulty": str(getattr(cmd, "difficulty", "Ordinary"))
                                  if cmd else "Ordinary",
                    "target": roll_dict.get("target", "?"),
                },
            }
            st.rerun()
            return

        st.markdown(result.narrative)
        append_turn(login, char_name, prompt, result.narrative)
        st.rerun()
