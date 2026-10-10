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
from services.state_parser import parse_state
from services.state_applier import apply_changes
try:
    from ui.roll_card import SKILL_NAMES_RU as _SKILL_RU
except Exception:
    _SKILL_RU = {}

def _loc_name(x):
    if isinstance(x, dict):
        nm = x.get('name', '') or x.get('id', '')
    else:
        nm = str(x or '')
    if not nm:
        return ''
    return _SKILL_RU.get(nm, nm)



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


try:
    from services.i18n import (
        translate_skills as _ts,
        translate_talents as _tt,
    )
except Exception:
    def _ts(x): return x
    def _tt(x): return x


def _render_skills(char: dict, login: str, char_name: str) -> None:
    skills = _ts(char.get("skills")) or []
    if not skills:
        st.caption("Навыков нет.")
        return
    for i, s in enumerate(skills):
        nm = _loc_name(s)
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
    tal = _tt(char.get("talents")) or []
    psy_rating = int(char.get("psy_rating", 0) or 0)
    if psy_rating > 0 and psy:
        st.markdown("<div class='gx-sec'>Психосилы (PSY "
                    + str(psy_rating) + ")</div>", unsafe_allow_html=True)
        chips = "".join("<span class='gx-chip'>" + _loc_name(p) + "</span>"
                        for p in psy)
        st.markdown(chips, unsafe_allow_html=True)
    if tal:
        st.markdown("<div class='gx-sec'>Способности</div>",
                    unsafe_allow_html=True)
        chips = "".join("<span class='gx-chip'>" + _loc_name(t) + "</span>"
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
        if st.button("🏪 Рынок", use_container_width=True,
                     key="game_market"):
            st.session_state.screen = "market"
            st.rerun()
        if st.button("📚 Библиотека", use_container_width=True,
                     key="game_library"):
            st.session_state.screen = "library"
            st.rerun()
        if char.get("has_ship") and st.button("🚀 Корабль", use_container_width=True,
                     key="game_ship"):
            st.session_state.screen = "ship"
            st.rerun()
        # PATCH_86: кнопка Пси-силы (только если psy_rating > 0 и не blocked)
        try:
            from services.psy_archetypes import ensure_psy_fields
            _psy_changed = ensure_psy_fields(char)
            if _psy_changed:
                try:
                    from persistence.characters import save_character as _save_psy
                    _save_psy(login, char_name, char)
                except Exception:
                    pass
        except Exception as _e:
            print("[game] ensure_psy fail: " + type(_e).__name__)
        try:
            from services import psychic as _psy_mod
            _psy_blocked = _psy_mod.is_blocked(char)
            _psy_rating = int(char.get("psy_rating", 0) or 0)
        except Exception:
            _psy_blocked = True
            _psy_rating = 0
        if _psy_rating > 0 and not _psy_blocked:
            if st.button("\U0001F52E \u041f\u0441\u0438-\u0441\u0438\u043b\u044b", use_container_width=True,
                         key="game_psy"):
                st.session_state.screen = "psy"
                st.rerun()
        if st.button("⚔️ Бой", use_container_width=True,
                     key="game_combat"):
            st.session_state.screen = "combat"
            st.rerun()
        if st.button("👥 Компаньоны", use_container_width=True,
                     key="game_companions"):
            st.session_state.screen = "companions"
            st.rerun()
        if st.button("📖 Дневник", use_container_width=True,
                     key="game_journal"):
            st.session_state.screen = "journal"
            st.rerun()
        if st.button("🏆 Ачивки", use_container_width=True,
                     key="game_achievements"):
            st.session_state.screen = "achievements"
            st.rerun()
        if st.button("⚙️ Настройки", use_container_width=True,
                     key="game_settings"):
            st.session_state.screen = "game_settings"
            st.rerun()
        if st.button("Персонаж", use_container_width=True,
                     key="game_character"):
            st.session_state.screen = "character"
            st.rerun()
        if st.button("Хроники", use_container_width=True,
                     key="game_chronicles"):
            st.session_state.screen = "chronicles"
            st.rerun()
        if st.button("Развитие", use_container_width=True,
                     key="game_progression"):
            st.session_state.screen = "progression"
            st.rerun()
        if st.button("Обучение", use_container_width=True, key="game_tut"):
            st.session_state.tutorial_mode = True
            st.session_state.screen = "tutorial"
            st.rerun()
        if st.button("Главное меню", use_container_width=True,
                     key="game_to_menu"):
            _back_to_menu()
        with st.expander("📝 Заметки", expanded=False):
            try:
                from services.notes import get_notes, add_note, remove_note
                from persistence.characters import save_character as _sc
                _notes = get_notes(char)
                for _i, _n in enumerate(_notes):
                    _c1, _c2 = st.columns([5, 1])
                    with _c1:
                        _tag = _n.get("tag") or ""
                        _prefix = ("[" + _tag + "] ") if _tag else ""
                        st.caption(_prefix + str(_n.get("text", "")))
                    with _c2:
                        if st.button("✕", key="gnote_" + str(_i)):
                            remove_note(char, _i)
                            _sc(st.session_state.user_login,
                                st.session_state.active_character, char)
                            st.rerun()
                _txt = st.text_area("Новая заметка", key="g_note_new",
                                    height=60, label_visibility="collapsed")
                if st.button("Добавить заметку", key="g_note_add"):
                    if add_note(char, _txt, ""):
                        _sc(st.session_state.user_login,
                            st.session_state.active_character, char)
                        st.rerun()
            except Exception as _e:
                st.caption("Ошибка заметок: " + type(_e).__name__)

        with st.expander("💾 Экспорт персонажа", expanded=False):
            try:
                from services.save_load import (
                    export_character_json, import_character_json,
                )
                from persistence.characters import save_character as _sc
                st.download_button(
                    "Скачать .json",
                    data=export_character_json(char),
                    file_name=str(char.get("name", "hero")) + ".json",
                    mime="application/json",
                    use_container_width=True,
                    key="g_dl",
                )
                _up = st.file_uploader("Загрузить .json", type=["json"],
                                       key="g_up",
                                       label_visibility="collapsed")
                if _up is not None:
                    _new, _err = import_character_json(_up.getvalue())
                    if _err:
                        st.error(_err)
                    elif _new:
                        _nm = str(_new.get("name", "imported"))
                        _sc(st.session_state.user_login, _nm, _new)
                        st.success("Импорт: " + _nm)
            except Exception as _e:
                st.caption("Ошибка save/load: " + type(_e).__name__)

        # Автосейв и откат
        try:
            from services.autosave import (
                has_snapshot, load_snapshot, clear_snapshot,
            )
            if has_snapshot(st.session_state.user_login,
                            st.session_state.active_character):
                if st.button("↩ Откатить на ход назад",
                             use_container_width=True,
                             key="game_rollback"):
                    snap = load_snapshot(
                        st.session_state.user_login,
                        st.session_state.active_character)
                    if snap:
                        from persistence.characters import save_character
                        save_character(
                            st.session_state.user_login,
                            st.session_state.active_character, snap)
                        clear_snapshot(
                            st.session_state.user_login,
                            st.session_state.active_character)
                        st.rerun()
        except Exception as _e:
            print("[game] rollback fail: " + type(_e).__name__)

        # Экспорт приключения в Markdown
        try:
            from persistence.chats import load_history
            _hist = load_history(st.session_state.user_login,
                                 st.session_state.active_character)
            _md = ["# " + str(char.get("name", "Приключение")), ""]
            _bg = char.get("user_background") or ""
            if _bg:
                _md.append("**Предыстория.** " + str(_bg))
                _md.append("")
            for h in _hist:
                role = h.get("role")
                text = h.get("text", "")
                if role == "player":
                    _md.append("### 🧑 Игрок")
                else:
                    _md.append("### 🤖 Мастер")
                _md.append(str(text)[:4000])
                _md.append("")
            _md_text = "\n".join(_md)
            st.download_button(
                "📥 Скачать приключение (.md)",
                data=_md_text.encode("utf-8"),
                file_name=str(char.get("name", "hero")) + ".md",
                mime="text/markdown",
                use_container_width=True,
                key="game_export_md",
            )
        except Exception as _e:
            print("[game] export fail: " + type(_e).__name__)

        if st.button("Выход", use_container_width=True, key="game_exit"):
            _logout()
            _logout()
            _logout()


def _back_to_menu() -> None:
    # Возврат в главное меню: login сохраняем, чистим только сессию игры.
    for k in ("active_character", "_game_loading_pending",
              "_game_loading_ready", "_roll_dialog_state",
              "_attack_open", "_attack_weapon", "_attack_result",
              "_pending_chat"):
        st.session_state.pop(k, None)
    st.session_state.screen = "main_menu"
    st.rerun()


def _logout() -> None:
    # Полный выход: удаляем логин, сбрасываем landing-флаг.
    for k in ("user_login", "active_character", "orchestrator",
              "tutorial_mode", "roll_card_variant",
              "_post_login_landed_for", "_game_loading_pending",
              "_game_loading_ready", "_roll_dialog_state",
              "_attack_open", "_attack_weapon", "_attack_result",
              "_pending_chat"):
        st.session_state.pop(k, None)
    st.session_state.screen = "splash"
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
    try:
        from ui.loading_screen import full_screen_html as _fsh
        _fs = _fsh(theme, 100, phrase, subtitle="когитатор готовит сессию")
    except Exception as _e:
        print('[game] full_screen_html fail: ' + type(_e).__name__)
        _fs = full_html(theme, 100, phrase,
                        subtitle="когитатор готовит сессию")
    try:
        st.html(_fs)
    except Exception:
        st.markdown(_fs, unsafe_allow_html=True)

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
            _bg = str(char.get("user_background")
                      or char.get("background") or "").strip()
            _intro = "Начало приключения."
            if _bg:
                _intro = (
                    "Начало приключения. Предыстория героя: " + _bg
                    + " Начни первую сцену так, чтобы предыстория "
                    "естественно вплелась в обстановку и NPC её знали."
                )
            result = orch.process_turn(_intro, char, history=[])
        finally:
            placeholder.empty()
        roll_dict = result.roll.to_dict() if result.roll else None
        narrative = _pack_narrative(result.narrative, roll_dict)
        append_turn(login, char_name, "Начало приключения.", narrative)
        history = load_history(login, char_name)

    _render_messages(history)

    # Панель тем
    try:
        from ui.theme import render_theme_strip
        render_theme_strip(key_prefix="__game_theme")
    except Exception as _e:
        print("[game] theme_strip fail: " + type(_e).__name__)

    # Быстрые кнопки — БЕЗ st.rerun(), устанавливаем _pending_chat
    _qa = st.columns(4)
    if _qa[0].button("\U0001F50D Осмотреться",
                     key="qa_observe", use_container_width=True):
        st.session_state["_pending_chat"] = "Я осматриваюсь"
    if _qa[1].button("\U0001F4AC Говорить",
                     key="qa_talk", use_container_width=True):
        st.session_state["_pending_chat"] = \
            "Я пытаюсь заговорить с ближайшим существом"
    if _qa[2].button("\u2694\ufe0f Атака",
                     key="qa_attack", use_container_width=True):
        st.session_state["_pending_chat"] = "Я атакую ближайшего врага"
    if _qa[3].button("\U0001F3B2 Иное",
                     key="qa_other", use_container_width=True):
        st.session_state["_pending_chat"] = \
            "Я действую по обстоятельствам"

    # Единая точка чтения
    _typed = st.chat_input("Что делает твой персонаж?")
    _pending = st.session_state.pop("_pending_chat", None)
    if _typed and _typed.strip():
        prompt = _typed.strip()
    elif _pending:
        prompt = _pending
    else:
        prompt = None

    if prompt:
        try:
            from services.autosave import save_snapshot
            save_snapshot(
                st.session_state.user_login,
                st.session_state.active_character, char)
        except Exception as _e:
            print("[game] autosave fail: " + type(_e).__name__)
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.status("⚙️ Дух-машины обрабатывают запрос...",
                           expanded=True) as _status:
                st.write("Анализ действия игрока...")
                try:
                    orch = _get_orch()
                    result = orch.process_turn(prompt, char, history=history)
                    _status.update(label="✔ Ответ получен",
                                   state="complete", expanded=False)
                except Exception as _e:
                    _status.update(
                        label="⚠ Ошибка: " + type(_e).__name__,
                        state="error", expanded=True,
                    )
                    raise

        _evt_text = ""
        try:
            from services.events import roll_event
            from services.settings_game import event_chance_for
            _ch = event_chance_for(st.session_state.get("user_login"))
            _ev = roll_event(char, _ch)
            if _ev.get("fired"):
                _evt_text = str(_ev.get("text", ""))
        except Exception as _e:
            print("[game] event fail: " + type(_e).__name__)
        _narr_full = result.narrative or ""
        if _evt_text:
            _narr_full = _narr_full + "\n\n> ⚡ **Событие:** " + _evt_text
        clean_text, changes = parse_state(_narr_full)
        if changes:
            applied = apply_changes(char, changes)
            if applied:
                _save_char(login, char_name, char)
                print("[game] state applied: " + ", ".join(applied))

        if result.roll:
            roll_dict = result.roll.to_dict()
            cmd = result.command
            st.session_state["_roll_dialog_state"] = {
                "phase": "await",
                "prompt": prompt,
                "narrative": clean_text,
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

        st.markdown(clean_text)
        append_turn(login, char_name, prompt, clean_text)
        try:
            from services.journal import auto_log_turn
            auto_log_turn(char, prompt, clean_text)
        except Exception as _e:
            print("[game] journal fail: " + type(_e).__name__)
        try:
            from services.achievements import check_all, describe
            _hist_len = len(history) if history else 0
            _new = check_all(char, extra={
                "combat_win": "ПОБЕД" in (clean_text or "").upper(),
                "total_rolls": _hist_len,
            })
            if _new:
                for _k in _new:
                    _n, _d = describe(_k)
                    st.toast("🏆 Достижение: " + _n)
        except Exception as _e:
            print("[game] achi fail: " + type(_e).__name__)
        try:
            from persistence.characters import save_character as _sc
            _sc(login, char_name, char)
        except Exception as _e:
            print("[game] save fail: " + type(_e).__name__)

        st.rerun()
