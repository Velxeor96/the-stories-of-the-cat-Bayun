# PATCH_10_STYLE_V1
"""ui/screens/tutorial.py — туториал (тема-совместимый)."""
from __future__ import annotations

import streamlit as st

from core.config import Config
from services import tutorial_data as td
from services.tutorial import TutorialEngine, TutorialError
from ui.theme import current_theme_icon, render_theme_selector


TUTORIAL_CSS = """
<style>
.tut-hero { text-align: center; padding: 20px 0 8px 0; position: relative; }
.tut-hero .sigil {
    font-size: 64px;
    color: var(--accent);
    text-shadow: 0 0 30px var(--accent-glow), 0 0 60px var(--accent-glow);
    line-height: 1;
    animation: fadeInUp 0.6s ease-out;
}
.tut-hero h1 {
    font-family: Georgia, serif; font-size: 42px; color: var(--fg);
    margin: 6px 0 0 0; letter-spacing: 4px;
    text-shadow: 0 0 24px var(--accent-glow);
    animation: fadeInUp 0.7s ease-out;
}
.tut-hero .sub {
    color: var(--fg-dim); font-style: italic; margin-top: 10px;
    font-size: 14px; letter-spacing: 1px;
    animation: fadeInUp 0.9s ease-out;
}
.tut-card {
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 24px 24px 20px 24px;
    background: linear-gradient(180deg, var(--panel-hi) 0%, var(--bg) 100%);
    box-shadow: 0 8px 28px var(--shadow);
    min-height: 560px;
    transition: all 0.35s ease;
    position: relative;
    overflow: hidden;
}
.tut-card::before {
    content: '';
    position: absolute; top: 0; left: 0; right: 0; height: 3px;
    background: linear-gradient(90deg, transparent 0%, var(--accent) 50%, transparent 100%);
    opacity: 0.5;
}
.tut-card.magnus:hover { box-shadow: 0 10px 40px var(--shadow), 0 0 40px var(--accent-glow); }
.tut-card.selena:hover { box-shadow: 0 10px 40px var(--shadow), 0 0 40px var(--accent-glow); }
.tut-card h2 {
    font-family: Georgia, serif; color: var(--fg);
    margin: 0 0 6px 0; font-size: 25px; letter-spacing: 1px;
}
.tut-card .tagline {
    color: var(--fg-dim); font-style: italic; font-size: 13px;
    margin-bottom: 20px; line-height: 1.5;
}
.tut-card .sec {
    font-size: 11px; letter-spacing: 3px; color: var(--accent);
    text-transform: uppercase; margin: 18px 0 10px 0;
}
.stats-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
.stat {
    background: var(--bg-alt); border: 1px solid var(--border);
    border-radius: 8px; padding: 8px 6px 6px 6px; text-align: center;
    transition: all 0.2s;
}
.stat:hover {
    border-color: var(--accent);
    box-shadow: 0 0 12px var(--accent-glow);
}
.stat .num {
    display: block; font-family: Georgia, serif; font-size: 22px;
    font-weight: bold; color: var(--fg); line-height: 1.1;
}
.stat .lbl {
    display: block; font-size: 10px; color: var(--fg-dim);
    letter-spacing: 2px; margin-top: 2px;
}
.res-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.res {
    background: var(--bg-alt); border: 1px solid var(--border);
    border-radius: 8px; padding: 10px 12px; color: var(--fg);
    font-size: 14px; text-align: center;
}
.res .v {
    color: var(--fg); font-weight: bold; font-family: Georgia, serif;
    font-size: 18px; margin-left: 4px;
}
.tut-role-hint {
    color: var(--fg-dim); font-size: 13px; font-style: italic;
    margin-top: 16px; padding: 10px 12px; background: var(--bg-alt);
    border-radius: 8px; border-left: 3px solid var(--accent);
}
.tut-scene-header {
    font-family: Georgia, serif; font-size: 26px; color: var(--fg);
    border-bottom: 1px solid var(--border); padding-bottom: 10px;
    margin: 0 0 16px 0; letter-spacing: 1px;
    animation: fadeInUp 0.4s ease-out;
}
.tut-scene-header .num { color: var(--accent); font-weight: bold; margin-right: 12px; }
.tut-roll {
    border-left: 4px solid var(--border); padding: 12px 16px;
    background: var(--panel); border-radius: 4px; margin: 12px 0;
    font-family: 'Consolas', monospace;
    animation: slideIn 0.4s ease-out;
    box-shadow: 0 2px 10px var(--shadow);
}
.tut-roll .headline { font-weight: bold; font-size: 16px; letter-spacing: 1px; }
.tut-roll .detail { color: var(--fg); font-size: 13px; margin-top: 6px; }
.tut-scene-map { display: flex; gap: 6px; margin-top: 8px; }
.tut-scene-map .dot { flex: 1; height: 6px; border-radius: 3px; background: var(--border); transition: 0.3s; }
.tut-scene-map .dot.done { background: #2E7D32; box-shadow: 0 0 8px rgba(46,125,50,0.5); }
.tut-scene-map .dot.active { background: var(--accent); box-shadow: 0 0 10px var(--accent-glow); }
.tut-hint {
    background: var(--bg-alt); border-left: 3px solid var(--accent);
    padding: 10px 14px; border-radius: 4px; color: var(--fg-dim);
    font-size: 13px; margin: 10px 0;
    animation: fadeInUp 0.4s ease-out;
}
.tut-actions-label {
    color: var(--accent); font-size: 11px; letter-spacing: 3px;
    text-transform: uppercase; margin: 18px 0 8px 0;
}
</style>
"""


def _get_engine() -> TutorialEngine:
    if "tutorial_engine" not in st.session_state:
        st.session_state.tutorial_engine = TutorialEngine(Config.load())
    return st.session_state.tutorial_engine


def _ensure_state() -> None:
    if "tutorial_state" not in st.session_state:
        st.session_state.tutorial_state = None


def _render_character_picker() -> None:
    st.markdown(TUTORIAL_CSS, unsafe_allow_html=True)
    icon = current_theme_icon()
    st.markdown(
        f"""<div class='tut-hero'>
            <div class='sigil'>{icon}</div>
            <h1>ПОТЕНТ</h1>
            <div class='sub'>Обучение Вольного Торговца · шесть сцен · две судьбы</div>
        </div>""",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='text-align:center; color:var(--fg-dim); max-width:720px; "
        "margin: 12px auto 28px auto; font-style:italic;'>"
        "Прежде чем создать своего персонажа — пройди короткий курс. "
        "Шесть сцен научат тебя проверкам, бою, социальным взаимодействиям "
        "и космическим сражениям.</p>",
        unsafe_allow_html=True,
    )
    c1, c2 = st.columns(2, gap="large")
    with c1:
        _render_char_card("magnus", "▶  Играть за Магнуса")
    with c2:
        _render_char_card("selena", "▶  Играть за Селену")
    st.markdown("<br>", unsafe_allow_html=True)
    cc1, cc2, cc3 = st.columns([1, 2, 1])
    with cc2:
        if st.button("⏭  Пропустить обучение", use_container_width=True,
                     key="btn_skip_tut"):
            _finish()


def _render_char_card(cid: str, btn_label: str) -> None:
    char = td.CHARACTERS[cid]
    cls = "magnus" if cid == "magnus" else "selena"
    tagline = ("Потомок древней династии. Командует с детства."
               if cid == "magnus"
               else "Наследница торговой династии. Выросла среди сделок.")
    role_hint = ("▸ Тяжёлый, живучий, лидер. Командование и запугивание."
                 if cid == "magnus"
                 else "▸ Умный, ловкий, дипломат. Восприятие и торговля.")
    stats_order = [
        ("WS", "Рукопашный"), ("BS", "Стрельба"), ("S", "Сила"),
        ("T", "Стойкость"), ("Ag", "Ловкость"), ("Int", "Интеллект"),
        ("Per", "Восприятие"), ("WP", "Воля"), ("Fel", "Общительность"),
    ]
    stats_html = ""
    for k, label in stats_order:
        v = char["characteristics"].get(k, "—")
        stats_html += (
            f"<div class='stat'><span class='num'>{v}</span>"
            f"<span class='lbl'>{k}</span></div>"
        )
    html = f"""<div class='tut-card {cls}'>
        <h2>{char['name']}</h2>
        <div class='tagline'>{tagline}</div>
        <div class='sec'>Характеристики</div>
        <div class='stats-grid'>{stats_html}</div>
        <div class='sec'>Ресурсы</div>
        <div class='res-grid'>
            <div class='res'>Раны<span class='v'>{char['wounds']}</span></div>
            <div class='res'>Судьба<span class='v'>{char['fate_points']}</span></div>
        </div>
        <div class='tut-role-hint'>{role_hint}</div>
    </div>"""
    st.markdown(html, unsafe_allow_html=True)
    st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)
    if st.button(btn_label, use_container_width=True, type="primary",
                 key=f"btn_{cid}"):
        _start(cid)


def _start(character_id: str) -> None:
    engine = _get_engine()
    state = engine.initial_state(character_id)
    st.session_state.tutorial_state = state
    st.rerun()


def _finish() -> None:
    login = st.session_state.get("user_login")
    if login:
        try:
            from persistence.settings import set_setting
            set_setting(login, "seen_tutorial", True)
        except Exception as e:
            print(f"[tutorial] set_setting: {e}")
    for k in ("tutorial_state", "tutorial_engine"):
        st.session_state.pop(k, None)
    st.session_state.screen = "wizard"
    st.rerun()


def _render_roll_card(roll: dict) -> None:
    if not roll:
        return
    success = roll.get("success", False)
    crit_s = roll.get("crit_success", False)
    crit_f = roll.get("crit_fail", False)
    color = "#2E7D32" if success else "#B71C1C"
    label = "УСПЕХ" if success else "ПРОВАЛ"
    if crit_s:
        color, label = "#FFD700", "КРИТИЧЕСКИЙ УСПЕХ"
    elif crit_f:
        color, label = "#8B0000", "КРИТИЧЕСКИЙ ПРОВАЛ"
    roll_v = roll.get("roll", "?")
    target_v = roll.get("target", "?")
    reason_v = roll.get("reason", "")
    degrees_v = roll.get("degrees", 0)
    html = (
        f"<div class='tut-roll' style='border-left-color:{color};"
        f"box-shadow:0 0 20px {color}44, 0 4px 14px var(--shadow);'>"
        f"<div class='headline' style='color:{color};'>"
        f"{label} &nbsp;·&nbsp; d100 = {roll_v} / {target_v}</div>"
        f"<div class='detail'>{reason_v} · маржá {degrees_v}</div>"
        f"</div>"
    )
    st.markdown(html, unsafe_allow_html=True)


def _scene_map(state: dict) -> str:
    cur = state["scene_idx"]
    dots = ""
    for i in range(len(td.SCENES)):
        cls = "dot"
        if i < cur:
            cls += " done"
        elif i == cur:
            cls += " active"
        dots += f"<div class='{cls}'></div>"
    return f"<div class='tut-scene-map'>{dots}</div>"


def render() -> None:
    st.markdown(TUTORIAL_CSS, unsafe_allow_html=True)
    _ensure_state()

    if st.session_state.tutorial_state is None:
        _render_character_picker()
        return

    state = st.session_state.tutorial_state
    if state.get("module_complete"):
        _render_finish_screen(state)
        return

    char = td.CHARACTERS[state["character_id"]]
    engine = _get_engine()
    scene_idx = state["scene_idx"]
    total = len(td.SCENES)
    scene = td.SCENES[scene_idx]
    scene_title = td.SCENE_TITLES.get(scene["id"], scene["id"])

    with st.sidebar:
        st.markdown(
            f"<div style='font-family:Georgia,serif; font-size:18px; "
            f"color:var(--fg); letter-spacing:1px;'>{char['name']}</div>",
            unsafe_allow_html=True,
        )
        st.caption(f"Обучение · {'муж.' if char['gender']=='male' else 'жен.'}")
        st.markdown(
            f"<div style='font-size:11px; letter-spacing:3px; color:var(--accent); "
            f"margin:12px 0 4px 0;'>ПРОГРЕСС · {scene_idx+1}/{total}</div>",
            unsafe_allow_html=True,
        )
        st.markdown(_scene_map(state), unsafe_allow_html=True)
        st.markdown("<hr>", unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Раны", f"{state['wounds']}/{char['wounds']}")
        with col2:
            st.metric("Судьба", state["fate_points"])
        st.metric("Фактор Прибыли", state["profit_factor"])
        st.markdown("<hr>", unsafe_allow_html=True)
        render_theme_selector(key_prefix="tut")
        st.markdown("<hr>", unsafe_allow_html=True)
        if st.button("⏭  Пропустить обучение", use_container_width=True):
            _finish()

    st.markdown(
        f"<div class='tut-scene-header'>"
        f"<span class='num'>{scene_idx + 1}/{total}</span>{scene_title}</div>",
        unsafe_allow_html=True,
    )

    for h in state["history"]:
        role = "user" if h["role"] == "player" else "assistant"
        with st.chat_message(role):
            st.markdown(h["text"])

    pending_roll = state.get("pending_roll")
    pending_post = state.get("pending_post")
    if pending_roll or pending_post:
        if pending_roll:
            _render_roll_card(pending_roll)
        if pending_post:
            with st.chat_message("assistant"):
                st.markdown(pending_post)
        if st.button("Далее  →", use_container_width=True, type="primary",
                     key=f"adv_{scene_idx}_{state['step_id']}_{len(state['history'])}"):
            engine.advance(state)
            st.session_state.tutorial_state = state
            st.rerun()
        return

    try:
        step = engine.get_current_step(state)
    except TutorialError as e:
        st.error(f"Ошибка: {e}")
        return

    if step.get("hint"):
        st.markdown(
            f"<div class='tut-hint'>🎓 {step['hint']}</div>",
            unsafe_allow_html=True,
        )

    options = step.get("options", [])
    if options:
        st.markdown(
            "<div class='tut-actions-label'>Варианты действий</div>",
            unsafe_allow_html=True,
        )
        for i, opt in enumerate(options):
            key = f"opt_{scene_idx}_{state['step_id']}_{i}"
            if st.button(opt["label"], use_container_width=True, key=key):
                try:
                    engine.choose_option(state, i)
                except TutorialError as e:
                    st.error(f"Ошибка: {e}")
                    return
                st.session_state.tutorial_state = state
                st.rerun()


def _render_finish_screen(state: dict) -> None:
    icon = current_theme_icon()
    st.markdown(
        f"<div style='text-align:center; padding:80px 0;'>"
        f"<div style='font-size:72px; color:var(--accent); "
        f"text-shadow: 0 0 30px var(--accent-glow), 0 0 60px var(--accent-glow);"
        f"animation: fadeInUp 0.7s ease-out;'>🏆</div>"
        f"<div style='font-family:Georgia,serif; font-size:38px; "
        f"color:var(--accent); letter-spacing:3px; margin-top:16px; "
        f"text-shadow: 0 0 20px var(--accent-glow);'>"
        f"ОБУЧЕНИЕ ЗАВЕРШЕНО</div>"
        f"<div style='color:var(--fg-dim); margin-top:16px; font-style:italic; "
        f"font-size:15px;'>"
        f"Ты готов создать своего собственного Вольного Торговца.</div>"
        f"</div>",
        unsafe_allow_html=True,
    )
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        if st.button("▶  Создать персонажа", use_container_width=True,
                     type="primary", key="btn_finish_module"):
            _finish()
