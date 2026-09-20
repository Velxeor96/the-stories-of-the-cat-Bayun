# PATCH_6B_7_V2
"""ui/screens/game.py — игровой экран: сайдбар + чат + карточка броска."""
from __future__ import annotations

import json
from typing import Optional

import streamlit as st

from persistence.chats import append_turn, load_history
from persistence.characters import CharacterError, load_character
from services.fallbacks import CHARACTERISTIC_NAMES
from services.orchestrator import Orchestrator

_ROLL_MARKER = "<!--ROLLCARD:"
_ROLL_MARKER_END = "-->"

_VARIANTS = ["ornate", "classic", "compact", "minimal"]
_VARIANT_LABELS = {
    "ornate":  "Орнамент",
    "classic": "Классика",
    "compact": "Компактная",
    "minimal": "Минимал",
}


def _pack_narrative(narrative: str, roll: Optional[dict]) -> str:
    if not roll:
        return narrative
    try:
        payload = json.dumps(roll, ensure_ascii=False)
    except Exception:
        return narrative
    return f"{narrative}\n{_ROLL_MARKER}{payload}{_ROLL_MARKER_END}"


def _unpack_narrative(text: str) -> tuple[str, Optional[dict]]:
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


def _render_roll_card(roll: Optional[dict], variant: str = "ornate") -> None:
    if not roll:
        return

    d100 = roll.get("roll", roll.get("d100", "?"))
    target = roll.get("target", "?")
    difficulty = roll.get("difficulty", "Ordinary")
    reason = roll.get("reason", "") or ""
    degrees = roll.get("degrees", 0)
    success = bool(roll.get("success"))
    crit_s = bool(roll.get("crit_success"))
    crit_f = bool(roll.get("crit_fail"))

    if crit_s:
        icon, color, label = "✨", "#FFD700", "КРИТИЧЕСКИЙ УСПЕХ"
    elif crit_f:
        icon, color, label = "💀", "#8B0000", "КРИТИЧЕСКИЙ ПРОВАЛ"
    elif success:
        icon, color, label = "✅", "#2E7D32", "УСПЕХ"
    else:
        icon, color, label = "❌", "#B71C1C", "ПРОВАЛ"

    sub_line = f"{reason} · маржá {degrees}" if reason else f"маржá {degrees}"

    if variant == "compact":
        st.markdown(
            f"<div style='color:{color};font-family:monospace;font-size:14px;"
            f"padding:4px 0;'>{icon} <b>{label}</b> &nbsp;·&nbsp; "
            f"d100=<b>{d100}</b> vs <b>{target}</b> &nbsp;·&nbsp; "
            f"{difficulty}, маржá {degrees}</div>",
            unsafe_allow_html=True,
        )
    elif variant == "minimal":
        st.markdown(
            f"<div style='color:{color};padding:2px 0;'>"
            f"{icon} <b>{label}</b>: d100={d100} / {target} ({difficulty})</div>",
            unsafe_allow_html=True,
        )
    elif variant == "classic":
        st.markdown(
            f"""<div style='border-left:4px solid {color};padding:10px 14px;
                background:#1a1a1d;border-radius:4px;margin:6px 0;
                font-family:monospace;'>
              <div style='color:{color};font-weight:bold;font-size:15px;'>
                {icon} {label}
              </div>
              <div style='color:#e8e0d0;font-size:14px;margin-top:4px;'>
                🎲 d100 = <b>{d100}</b> · порог <b>{target}</b> · {difficulty}
              </div>
              <div style='color:#a0a0a0;font-size:12px;margin-top:2px;'>
                {sub_line}
              </div>
            </div>""",
            unsafe_allow_html=True,
        )
    else:  # ornate
        st.markdown(
            f"""<div style='border:2px double {color};border-radius:12px;
                padding:14px 18px;margin:8px 0;
                background:linear-gradient(180deg,#1a1a1d 0%,#0e0e10 100%);
                text-align:center;font-family:Georgia,serif;'>
              <div style='color:{color};font-size:12px;letter-spacing:6px;'>◈ ◈ ◈</div>
              <div style='color:{color};font-size:22px;margin:6px 0;font-weight:bold;'>
                {icon} {label} {icon}
              </div>
              <div style='color:#e8e0d0;font-size:14px;'>
                🎲 d100 = <b>{d100}</b> &nbsp;·&nbsp; Порог = <b>{target}</b>
              </div>
              <div style='color:#a0a0a0;font-size:12px;margin-top:6px;'>
                {sub_line}
              </div>
              <div style='color:{color};font-size:12px;letter-spacing:6px;margin-top:6px;'>◈ ◈ ◈</div>
            </div>""",
            unsafe_allow_html=True,
        )


def _logout() -> None:
    for k in ("user_login", "active_character", "orchestrator",
              "tutorial_mode", "roll_card_variant"):
        st.session_state.pop(k, None)
    st.session_state.screen = "splash"
    st.rerun()


def _get_orch() -> Orchestrator:
    if "orchestrator" not in st.session_state:
        from core.config import Config
        cfg = Config.load()
        st.session_state.orchestrator = Orchestrator(cfg, use_rag=True)
    return st.session_state.orchestrator


def _render_sidebar(char: dict) -> None:
    with st.sidebar:
        st.markdown(f"### {char['name']}")
        st.caption(f"{char['faction']} · {char['subfaction']}")
        st.caption(
            f"{'Мужской' if char['gender'] == 'male' else 'Женский'} · "
            f"{char['age']} лет"
        )

        st.markdown("---")
        st.metric("Раны", f"{char['wounds']['current']} / {char['wounds']['max']}")
        st.metric("Судьба",
                  f"{char['fate_points']['current']} / {char['fate_points']['max']}")

        c1, c2 = st.columns(2)
        with c1:
            st.metric("Ранг", char.get("rank", 1))
        with c2:
            st.metric("XP", f"{char.get('xp', 0)} / 500")

        c1, c2 = st.columns(2)
        with c1:
            st.metric("Порча", char.get("corruption", 0))
        with c2:
            st.metric("Деньги", f"{char.get('money', 0)} {char.get('currency', '')}")

        st.markdown("---")
        st.markdown("#### Характеристики")
        stats = char.get("characteristics", {})
        cols = st.columns(3)
        for i, (key, val) in enumerate(stats.items()):
            with cols[i % 3]:
                st.metric(CHARACTERISTIC_NAMES.get(key, key), val)

        st.markdown("---")
        st.markdown("#### Настройки")
        if "roll_card_variant" not in st.session_state:
            st.session_state.roll_card_variant = "ornate"

        current_idx = _VARIANTS.index(st.session_state.roll_card_variant) \
            if st.session_state.roll_card_variant in _VARIANTS else 0
        choice = st.selectbox(
            "🎨 Карточка броска",
            options=_VARIANTS,
            index=current_idx,
            format_func=lambda v: _VARIANT_LABELS.get(v, v),
            key="_roll_card_variant_widget",
        )
        if choice != st.session_state.roll_card_variant:
            st.session_state.roll_card_variant = choice

        st.markdown("---")
        if st.button("🎓 Обучение", use_container_width=True):
            st.session_state.tutorial_mode = True
            st.session_state.screen = "tutorial"
            st.rerun()

        if st.button("🚪 Выйти в меню", use_container_width=True):
            _logout()


def _render_messages(history: list[dict]) -> None:
    variant = st.session_state.get("roll_card_variant", "ornate")
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
                _render_roll_card(roll, variant=variant)
            st.markdown(clean_text)


def render() -> None:
    login = st.session_state.get("user_login")
    char_name = st.session_state.get("active_character")

    if not login or not char_name:
        st.warning("Нет активного персонажа.")
        if st.button("← В меню"):
            _logout()
        return

    try:
        char = load_character(login, char_name)
    except CharacterError as e:
        st.error(str(e))
        if st.button("← К созданию персонажа"):
            st.session_state.screen = "wizard"
            st.rerun()
        return

    _render_sidebar(char)

    st.markdown(
        f"<h2 style='font-family: Georgia, serif;'>🎮 {char['name']}</h2>",
        unsafe_allow_html=True,
    )

    history = load_history(login, char_name)

    init_key = f"__init_scene__{login}__{char_name}"
    if not history and init_key not in st.session_state:
        st.session_state[init_key] = True
        with st.spinner("Мастер открывает сцену…"):
            orch = _get_orch()
            result = orch.process_turn("Начало приключения.", char, history=[])
            roll_dict = result.roll.to_dict() if result.roll else None
            narrative = _pack_narrative(result.narrative, roll_dict)
            append_turn(login, char_name, "Начало приключения.", narrative)
            history = load_history(login, char_name)

    _render_messages(history)

    if prompt := st.chat_input("Что делает твой персонаж?"):
        with st.chat_message("user"):
            st.markdown(prompt)

        variant = st.session_state.get("roll_card_variant", "ornate")
        with st.chat_message("assistant"):
            with st.spinner("Мастер ведёт сцену…"):
                orch = _get_orch()
                result = orch.process_turn(prompt, char, history=history)
            if result.roll:
                _render_roll_card(result.roll.to_dict(), variant=variant)
            st.markdown(result.narrative)

        roll_dict = result.roll.to_dict() if result.roll else None
        narrative_to_save = _pack_narrative(result.narrative, roll_dict)
        append_turn(login, char_name, prompt, narrative_to_save)
        st.rerun()
