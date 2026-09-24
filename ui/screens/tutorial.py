# PATCH_TUT_V2D
# ui/screens/tutorial.py - UI туториала: интро, выбор, сцены, бой, финал.
from __future__ import annotations

import streamlit as st

from core.config import Config
from services import tutorial_data as td
from services.tutorial import TutorialEngine, TutorialError
from ui.theme import current_theme_icon, render_theme_selector


CSS = '''<style>
.tut-hero { text-align: center; padding: 20px 0 8px 0; }
.tut-hero .sigil { font-size: 64px; color: var(--accent);
    text-shadow: 0 0 30px var(--accent-glow), 0 0 60px var(--accent-glow);
    line-height: 1; }
.tut-hero h1 { font-family: Georgia, serif; font-size: 42px; color: var(--fg);
    margin: 6px 0 0 0; letter-spacing: 4px;
    text-shadow: 0 0 24px var(--accent-glow); }
.tut-hero .sub { color: var(--fg-dim); font-style: italic;
    margin-top: 10px; font-size: 14px; letter-spacing: 1px; }
.tut-card { border: 1px solid var(--border); border-radius: 16px;
    padding: 24px; background: linear-gradient(180deg, var(--panel-hi) 0%, var(--bg) 100%);
    box-shadow: 0 8px 28px var(--shadow); position: relative; overflow: hidden; }
.tut-card::before { content: ''; position: absolute; top: 0; left: 0;
    right: 0; height: 3px;
    background: linear-gradient(90deg, transparent 0%, var(--accent) 50%, transparent 100%);
    opacity: 0.5; }
.tut-card h2 { font-family: Georgia, serif; color: var(--fg);
    margin: 0 0 6px 0; font-size: 25px; letter-spacing: 1px; }
.tut-card .tagline { color: var(--fg-dim); font-style: italic;
    font-size: 13px; margin-bottom: 20px; line-height: 1.5; }
.tut-card .sec { font-size: 11px; letter-spacing: 3px; color: var(--accent);
    text-transform: uppercase; margin: 18px 0 10px 0; }
.tut-scene-header { font-family: Georgia, serif; font-size: 26px;
    color: var(--fg); border-bottom: 1px solid var(--border);
    padding-bottom: 10px; margin: 0 0 16px 0; letter-spacing: 1px; }
.tut-scene-header .num { color: var(--accent); font-weight: bold; margin-right: 12px; }
.tut-roll { border-left: 4px solid var(--border); padding: 12px 16px;
    background: var(--panel); border-radius: 4px; margin: 8px 0;
    font-family: Consolas, monospace;
    box-shadow: 0 2px 10px var(--shadow); }
.tut-roll .headline { font-weight: bold; font-size: 15px; letter-spacing: 1px; }
.tut-roll .detail { color: var(--fg); font-size: 13px; margin-top: 6px; }
.tut-scene-map { display: flex; gap: 6px; margin-top: 8px; }
.tut-scene-map .dot { flex: 1; height: 6px; border-radius: 3px; background: var(--border); }
.tut-scene-map .dot.done { background: #2E7D32; }
.tut-scene-map .dot.active { background: var(--accent);
    box-shadow: 0 0 10px var(--accent-glow); }
.tut-hint { background: var(--bg-alt); border-left: 3px solid var(--accent);
    padding: 10px 14px; border-radius: 4px; color: var(--fg-dim);
    font-size: 13px; margin: 10px 0; }
.tut-actions-label { color: var(--accent); font-size: 11px;
    letter-spacing: 3px; text-transform: uppercase; margin: 18px 0 8px 0; }
.g91-card { background: var(--panel); border: 1px solid var(--border);
    border-left: 4px solid var(--accent); border-radius: 10px;
    padding: 18px 22px; margin: 12px 0;
    box-shadow: 0 4px 18px var(--shadow); }
.g91-card .head { font-size: 11px; letter-spacing: 3px;
    color: var(--accent); text-transform: uppercase; margin-bottom: 8px; }
.g91-card .body { color: var(--fg); font-size: 15px; line-height: 1.7; }
.combat-box { background: var(--panel); border: 1px solid var(--border-hi);
    border-radius: 12px; padding: 14px 18px; margin: 12px 0; }
.combat-box .name { font-family: Georgia, serif; font-size: 17px;
    color: var(--fg); margin-bottom: 6px; }
.combat-box .hp-bar { height: 14px; border-radius: 7px;
    background: var(--bg-alt); border: 1px solid var(--border);
    overflow: hidden; margin-top: 6px; }
.combat-box .hp-fill-enemy { height: 100%;
    background: linear-gradient(90deg, #6A1B9A, #AB47BC); }
.combat-box .hp-fill-pc { height: 100%;
    background: linear-gradient(90deg, #B71C1C, #E53935); }
div[data-baseweb="tooltip"], [role="tooltip"] { display: none !important; }
.stButton > button:focus,
.stButton > button:focus-visible,
.stButton > button:active {
    outline: none !important;
    box-shadow: none !important; }
</style>'''


def _get_engine():
    if "tutorial_engine" not in st.session_state:
        st.session_state.tutorial_engine = TutorialEngine(Config.load())
    return st.session_state.tutorial_engine


def _ensure_state():
    if "tutorial_state" not in st.session_state:
        st.session_state.tutorial_state = None
    if "tut_intro_page" not in st.session_state:
        st.session_state.tut_intro_page = 0
    if "tut_stat_dialog" not in st.session_state:
        st.session_state.tut_stat_dialog = None


@st.dialog("Справка")
def _stat_dialog(key):
    info = td.CHARACTERISTIC_HELP.get(key)
    if not info:
        st.write("Нет справки.")
        return
    st.markdown("### " + info["name"])
    st.caption(info["short"])
    st.markdown(info["body"])
    if st.button("Закрыть", use_container_width=True, key="dlg_close"):
        st.session_state.tut_stat_dialog = None
        st.rerun()


def _maybe_open_dialog():
    k = st.session_state.get("tut_stat_dialog")
    if k:
        _stat_dialog(k)


def _render_intro():
    page = st.session_state.tut_intro_page or 0
    pages = td.INTRO_PAGES
    icon = current_theme_icon()
    st.markdown(
        "<div class='tut-hero'><div class='sigil'>" + str(icon) + "</div>"
        "<h1>G-91</h1>"
        "<div class='sub'>Дух Машины корабля «Погибель»</div></div>",
        unsafe_allow_html=True)
    cur = pages[page]
    body_lines = cur["body"].split(chr(10))
    body_html = "<br>".join(body_lines)
    st.markdown(
        "<div class='g91-card'><div class='head'>// " + cur["title"] +
        " //</div><div class='body'>" + body_html + "</div></div>",
        unsafe_allow_html=True)
    st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
    is_last = page >= len(pages) - 1
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("Назад", use_container_width=True, key="intro_back",
                     disabled=(page == 0)):
            st.session_state.tut_intro_page = page - 1
            st.rerun()
    with c2:
        if is_last:
            if st.button("Выбрать персонажа", use_container_width=True,
                         type="primary", key="intro_done"):
                st.session_state.tut_intro_page = None
                st.rerun()
        else:
            if st.button("Далее", use_container_width=True, type="primary",
                         key="intro_next"):
                st.session_state.tut_intro_page = page + 1
                st.rerun()
    with c3:
        if st.button("Пропустить", use_container_width=True, key="intro_skip"):
            st.session_state.tut_intro_page = None
            st.rerun()


def _render_character_picker():
    icon = current_theme_icon()
    st.markdown(
        "<div class='tut-hero'><div class='sigil'>" + str(icon) + "</div>"
        "<h1>ПОТЕНТ</h1>"
        "<div class='sub'>Обучение Вольного Торговца · шесть сцен · две судьбы</div></div>",
        unsafe_allow_html=True)
    st.markdown(
        "<p style='text-align:center;color:var(--fg-dim);max-width:720px;"
        "margin:12px auto 24px auto;font-style:italic;'>"
        "Нажми на любую характеристику, чтобы получить справку. "
        "Потом выбери персонажа и начни обучение.</p>",
        unsafe_allow_html=True)
    c1, c2 = st.columns(2, gap="large")
    with c1:
        _render_char_card("magnus", "Играть за Магнуса")
    with c2:
        _render_char_card("selena", "Играть за Селену")
    st.markdown("<br>", unsafe_allow_html=True)
    cc1, cc2, cc3 = st.columns([1, 2, 1])
    with cc2:
        if st.button("Пропустить обучение", use_container_width=True,
                     key="btn_skip_tut"):
            _finish("create")


def _render_char_card(cid, btn_label):
    char = td.CHARACTERS[cid]
    tagline = char.get("background", "")
    role_hint = char.get("tagline", "")
    st.markdown(
        "<div class='tut-card'><h2>" + char["name"] + "</h2>"
        "<div class='tagline'>" + tagline + "</div>"
        "<div class='sec'>Характеристики · нажми для справки</div>",
        unsafe_allow_html=True)
    order = ["WS", "BS", "S", "T", "Ag", "Int", "Per", "WP", "Fel"]
    rows = [order[0:3], order[3:6], order[6:9]]
    for row in rows:
        cols = st.columns(3)
        for i, key in enumerate(row):
            v = char["characteristics"].get(key, "?")
            with cols[i]:
                if st.button(key + " · " + str(v), use_container_width=True,
                             key="stat_" + cid + "_" + key):
                    st.session_state.tut_stat_dialog = key
                    st.rerun()
    res_html = (
        "<div class='sec'>Ресурсы</div>"
        "<div style='display:flex;gap:8px;margin-bottom:10px;'>"
        "<div style='flex:1;background:var(--bg-alt);border:1px solid var(--border);"
        "border-radius:8px;padding:10px;text-align:center;color:var(--fg);'>"
        "Раны <b>" + str(char["wounds_max"]) + "</b></div>"
        "<div style='flex:1;background:var(--bg-alt);border:1px solid var(--border);"
        "border-radius:8px;padding:10px;text-align:center;color:var(--fg);'>"
        "Судьба <b>" + str(char["fate_points"]) + "</b></div></div>"
        "<div style='background:var(--bg-alt);border-left:3px solid var(--accent);"
        "border-radius:8px;padding:10px 12px;color:var(--fg-dim);"
        "font-size:13px;font-style:italic;'>" + role_hint + "</div></div>"
    )
    st.markdown(res_html, unsafe_allow_html=True)
    st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)
    if st.button(btn_label, use_container_width=True, type="primary",
                 key="btn_" + cid):
        _start(cid)


def _start(character_id):
    engine = _get_engine()
    state = engine.initial_state(character_id)
    st.session_state.tutorial_state = state
    st.rerun()


def _weapons_to_sheet(weapon_ids):
    out = []
    for wid in weapon_ids:
        w = td.WEAPONS.get(wid)
        if not w:
            continue
        if w["type"] == "melee":
            stats = ("Ближний бой, " + w["dmg"] + ", Пробой " +
                     str(w["pen"]))
        elif w["type"] == "ranged":
            stats = (str(w["range_m"]) + "м, " + str(w["rof"]) + ", " +
                     w["dmg"] + ", Пробой " + str(w["pen"]))
        else:
            stats = w["dmg"]
        out.append({
            "name": w["name"],
            "stats": stats,
            "weight": "-",
            "notes": w.get("special", ""),
        })
    return out


def _finish(action):
    login = st.session_state.get("user_login")
    if login:
        try:
            from persistence.settings import set_setting
            set_setting(login, "seen_tutorial", True)
        except Exception as e:
            print("[tutorial] set_setting: " + str(e))
    if action == "continue":
        state = st.session_state.get("tutorial_state")
        if state and login:
            try:
                from persistence.characters import save_character
                from services.character_creation import build_character
                char_id = state["character_id"]
                tpl = td.CHARACTERS[char_id]
                data = build_character(
                    name=tpl["name"],
                    gender=tpl["gender"],
                    age=str(tpl.get("age", 30)),
                    appearance="",
                    user_background=tpl.get("background", ""),
                    faction_id="imperium",
                    subfaction_id="rogue_trader",
                    archetype_id=None,
                    characteristics=dict(tpl["characteristics"]),
                )
                data["faction"] = "imperium"
                data["faction_id"] = "imperium"
                data["subfaction"] = "rogue_trader"
                data["subfaction_id"] = "rogue_trader"
                data["background"] = tpl.get("background", "")
                data["wounds"] = {
                    "current": state["wounds_max"],
                    "max": state["wounds_max"],
                }
                data["fate_points"] = {
                    "current": state["fate_max"],
                    "max": state["fate_max"],
                }
                data["armour"] = dict(tpl.get("armour", {}))
                data["weapons"] = _weapons_to_sheet(tpl.get("weapons", []))
                data["xp"] = 300
                data["psy_rating"] = 0
                data["psychic_powers"] = []
                save_character(login, data["name"], data)
                try:
                    from persistence.settings import set_setting
                    set_setting(login, "last_character", data["name"])
                except Exception as e:
                    print("[tutorial] set_setting last_character: " + str(e))
                st.session_state.active_character = data["name"]
            except Exception as e:
                print("[tutorial] save_character: " + str(e))
                st.session_state.screen = "wizard"
                st.rerun()
                return
    for k in ("tutorial_state", "tutorial_engine", "tut_intro_page"):
        st.session_state.pop(k, None)
    if action == "continue":
        st.session_state.screen = "game"
    else:
        st.session_state.screen = "wizard"
    st.rerun()


def _render_roll_card(roll):
    if not roll:
        return
    success = roll.get("success", False)
    crit_s = roll.get("crit_success", False)
    crit_f = roll.get("crit_fail", False)
    color = "#2E7D32" if success else "#B71C1C"
    label = "УСПЕХ" if success else "ПРОВАЛ"
    if crit_s:
        color = "#FFD700"
        label = "КРИТИЧЕСКИЙ УСПЕХ"
    elif crit_f:
        color = "#8B0000"
        label = "КРИТИЧЕСКИЙ ПРОВАЛ"
    roll_v = roll.get("roll", "?")
    target_v = roll.get("target", "?")
    reason_v = roll.get("reason", "")
    degrees_v = roll.get("degrees", 0)
    st.markdown(
        "<div class='tut-roll' style='border-left-color:" + color + ";'>"
        "<div class='headline' style='color:" + color + ";'>" + label +
        " &nbsp;·&nbsp; d100 = " + str(roll_v) + " / " + str(target_v) + "</div>"
        "<div class='detail'>" + str(reason_v) + " · маржа " + str(degrees_v) +
        "</div></div>",
        unsafe_allow_html=True)


def _scene_map(state):
    cur = state["scene_idx"]
    dots = ""
    for i in range(len(td.SCENES)):
        cls = "dot"
        if i < cur:
            cls += " done"
        elif i == cur:
            cls += " active"
        dots += "<div class='" + cls + "'></div>"
    return "<div class='tut-scene-map'>" + dots + "</div>"


def _render_combat_log_entry(entry):
    txt = entry.get("text")
    if txt:
        st.markdown(txt)
        return
    if "roll" in entry:
        _render_roll_card(entry["roll"])


def _render_combat_ui(state):
    c = state.get("combat")
    if not c:
        return
    enemy = c["enemy"]
    st.markdown(
        "<div class='combat-box'>"
        "<div class='name'>" + enemy["name"] + " · Раунд " +
        str(c["round"]) + "</div>"
        "<div style='font-size:12px;color:var(--fg-dim);'>Раны: " +
        str(enemy["wounds"]) + " / " + str(enemy["wounds_max"]) + "</div>"
        "<div class='hp-bar'><div class='hp-fill-enemy' style='width:" +
        str(int(100 * enemy["wounds"] / max(1, enemy["wounds_max"]))) +
        "%;'></div></div></div>",
        unsafe_allow_html=True)
    pc = td.CHARACTERS[state["character_id"]]
    st.markdown(
        "<div class='combat-box'>"
        "<div class='name'>" + pc["name"] + " · Ран " +
        str(state["wounds"]) + " / " + str(state["wounds_max"]) + "</div>"
        "<div class='hp-bar'><div class='hp-fill-pc' style='width:" +
        str(int(100 * state["wounds"] / max(1, state["wounds_max"]))) +
        "%;'></div></div></div>",
        unsafe_allow_html=True)
    if c["log"]:
        with st.container(border=True):
            for entry in c["log"][-14:]:
                _render_combat_log_entry(entry)
    if c["over"]:
        if st.button("Продолжить", use_container_width=True, type="primary",
                     key="cmb_resolve"):
            engine = _get_engine()
            engine.combat_resolve(state)
            st.session_state.tutorial_state = state
            st.rerun()
        return
    if c["turn"] == "enemy":
        if st.button("Ход врага", use_container_width=True, type="primary",
                     key="cmb_enemy"):
            engine = _get_engine()
            engine.combat_enemy_turn(state)
            st.session_state.tutorial_state = state
            st.rerun()
        return
    st.markdown("<div class='tut-actions-label'>Твой ход</div>",
                unsafe_allow_html=True)
    cols = st.columns(2)
    char = td.CHARACTERS[state["character_id"]]
    weapons = [td.WEAPONS[w] for w in char["weapons"] if w in td.WEAPONS]
    with cols[0]:
        for w in weapons:
            if w["type"] == "ranged":
                label = "Выстрел: " + w["name"] + " (" + w["dmg"] + ")"
                if st.button(label, use_container_width=True,
                             key="act_ranged_" + w["id"]):
                    engine = _get_engine()
                    engine.combat_player_action(
                        state, {"kind": "attack_ranged", "weapon": w["id"]})
                    st.session_state.tutorial_state = state
                    st.rerun()
        if "warp_bolt" in char.get("tutorial_abilities", []):
            if st.button("Варп-выстрел (психосила, WP)",
                         use_container_width=True, key="act_psy"):
                engine = _get_engine()
                engine.combat_player_action(state, {"kind": "psy_bolt"})
                st.session_state.tutorial_state = state
                st.rerun()
    with cols[1]:
        for w in weapons:
            if w["type"] == "melee":
                label = "Удар: " + w["name"] + " (" + w["dmg"] + ")"
                if st.button(label, use_container_width=True,
                             key="act_melee_" + w["id"]):
                    engine = _get_engine()
                    engine.combat_player_action(
                        state, {"kind": "attack_melee", "weapon": w["id"]})
                    st.session_state.tutorial_state = state
                    st.rerun()
        if st.button("Граната (2d10)",
                     use_container_width=True, key="act_grenade"):
            engine = _get_engine()
            engine.combat_player_action(state, {"kind": "grenade"})
            st.session_state.tutorial_state = state
            st.rerun()
        if st.button("Прицелиться (+20)",
                     use_container_width=True, key="act_aim"):
            engine = _get_engine()
            engine.combat_player_action(state, {"kind": "aim"})
            st.session_state.tutorial_state = state
            st.rerun()


def render():
    st.markdown(CSS, unsafe_allow_html=True)
    _ensure_state()
    _maybe_open_dialog()
    if st.session_state.tut_intro_page is not None:
        _render_intro()
        return
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
            "<div style='font-family:Georgia,serif;font-size:18px;"
            "color:var(--fg);letter-spacing:1px;'>" + char["name"] + "</div>",
            unsafe_allow_html=True)
        gender_ru = "муж." if char["gender"] == "male" else "жен."
        st.caption("Обучение · " + gender_ru)
        st.markdown(
            "<div style='font-size:11px;letter-spacing:3px;color:var(--accent);"
            "margin:12px 0 4px 0;'>ПРОГРЕСС · " + str(scene_idx + 1) + "/" +
            str(total) + "</div>",
            unsafe_allow_html=True)
        st.markdown(_scene_map(state), unsafe_allow_html=True)
        st.markdown("<hr>", unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Раны", str(state["wounds"]) + "/" +
                      str(state["wounds_max"]))
        with col2:
            st.metric("Судьба", state["fate_points"])
        st.metric("Фактор Прибыли", state["profit_factor"])
        st.markdown("<hr>", unsafe_allow_html=True)
        try:
            render_theme_selector(key_prefix="tut")
        except Exception as e:
            print("[tutorial] theme: " + str(e))
        st.markdown("<hr>", unsafe_allow_html=True)
        if st.button("Пропустить обучение", use_container_width=True,
                     key="side_skip"):
            _finish("create")
    st.markdown(
        "<div class='tut-scene-header'>"
        "<span class='num'>" + str(scene_idx + 1) + "/" + str(total) +
        "</span>" + scene_title + "</div>",
        unsafe_allow_html=True)
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
        adv_key = ("adv_" + str(scene_idx) + "_" + state["step_id"] + "_" +
                   str(len(state["history"])))
        if st.button("Далее", use_container_width=True, type="primary",
                     key=adv_key):
            engine.advance(state)
            st.session_state.tutorial_state = state
            st.rerun()
        return
    if state.get("combat"):
        _render_combat_ui(state)
        return
    try:
        step = engine.get_current_step(state)
    except TutorialError as e:
        st.error("Ошибка: " + str(e))
        return
    if step.get("hint"):
        st.markdown("<div class='tut-hint'>" + step["hint"] + "</div>",
                    unsafe_allow_html=True)
    options = step.get("options", [])
    if options:
        st.markdown("<div class='tut-actions-label'>Варианты действий</div>",
                    unsafe_allow_html=True)
        for i, opt in enumerate(options):
            key = ("opt_" + str(scene_idx) + "_" + state["step_id"] + "_" +
                   str(i))
            if st.button(opt["label"], use_container_width=True, key=key):
                try:
                    engine.choose_option(state, i)
                except TutorialError as e:
                    st.error("Ошибка: " + str(e))
                    return
                st.session_state.tutorial_state = state
                st.rerun()


def _render_finish_screen(state):
    icon = current_theme_icon()
    st.markdown(
        "<div style='text-align:center;padding:60px 0 30px 0;'>"
        "<div style='font-size:72px;color:var(--accent);"
        "text-shadow:0 0 30px var(--accent-glow),0 0 60px var(--accent-glow);'>" +
        str(icon) + "</div>"
        "<div style='font-family:Georgia,serif;font-size:38px;color:var(--accent);"
        "letter-spacing:3px;margin-top:16px;"
        "text-shadow:0 0 20px var(--accent-glow);'>ОБУЧЕНИЕ ЗАВЕРШЕНО</div>"
        "<div style='color:var(--fg-dim);margin-top:16px;font-style:italic;"
        "font-size:15px;'>Ты готов продолжить путь Вольного Торговца.</div>"
        "</div>",
        unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Продолжить этим персонажем", use_container_width=True,
                     type="primary", key="finish_go_continue"):
            _finish("continue")
    with c2:
        if st.button("Создать своего персонажа", use_container_width=True,
                     key="finish_go_create"):
            _finish("create")
