# app.py
# Streamlit: визард + чат с Мастером.
# Сохранение:
#   - localStorage (автоматически, при каждом изменении)
#   - JSON-файлы (ручной экспорт/импорт)
# Расширенный [STATE]: wounds, fate, money, currency, quests, npcs, ship, etc.
# Сайдбар с табами + быстрые действия.

import json
import re
from datetime import datetime

import streamlit as st

try:
    from streamlit_local_storage import LocalStorage
    HAS_LS = True
except Exception:
    HAS_LS = False

from gigachat import GigaChat
from gigachat.models import Chat, Messages, MessagesRole, Function

from dice import roll_dice
from knowledge import KnowledgeBase

import factions_data
import character_creation as cc


# ============================================================
# НАСТРОЙКИ
# ============================================================
try:
    API_KEY = st.secrets["GIGACHAT_API_KEY"]
except Exception:
    API_KEY = "MDFhMDk2NGMtZGQ0Yi03NGJiLTkzNWEtODgzMWEwNjZjZDYzOjBkNDViZDZmLTYxYzQtNGYyNC1hYzFlLTczZGY5OWI5MDZiMw=="

MODEL = "GigaChat-2-Pro"
MAX_FUNCTION_ITERATIONS = 15
TOP_K_KNOWLEDGE = 5
MASTER_PROMPT_PATH = "prompts/master.txt"

LS_KEY = "wh40k_rpg_save"
SAVE_FORMAT = "wh40k_rpg_save"
SAVE_VERSION = 1

st.set_page_config(page_title="Warhammer 40K — RPG с ИИ-Мастером", layout="wide")


@st.cache_resource
def get_kb():
    return KnowledgeBase()


@st.cache_resource
def get_giga():
    return GigaChat(
        credentials=API_KEY,
        verify_ssl_certs=False,
        scope="GIGACHAT_API_PERS",
        model=MODEL,
    )


@st.cache_data
def get_master_prompt():
    with open(MASTER_PROMPT_PATH, encoding="utf-8") as f:
        return f.read()


# ============================================================
# LOCALSTORAGE — сохранение/загрузка
# ============================================================
def _ls_save(localS, sheet, chat_history):
    """Сохраняет персонажа и историю в localStorage."""
    if not HAS_LS or sheet is None:
        return
    try:
        payload = json.dumps({
            "format": SAVE_FORMAT,
            "version": SAVE_VERSION,
            "character": sheet,
            "chat_history": chat_history,
            "saved_at": datetime.now().isoformat(),
        }, ensure_ascii=False)
        localS.setItem(LS_KEY, payload)
    except Exception as e:
        print(f"[LS] ошибка сохранения: {e}")


def _ls_load(localS):
    """Возвращает dict {character, chat_history} или None."""
    if not HAS_LS:
        return None
    try:
        raw = localS.getItem(LS_KEY)
        if not raw:
            return None
        data = json.loads(raw)
        if data.get("format") != SAVE_FORMAT:
            return None
        return {
            "character": data.get("character"),
            "chat_history": data.get("chat_history", []),
        }
    except Exception as e:
        print(f"[LS] ошибка загрузки: {e}")
        return None


def _ls_clear(localS):
    if not HAS_LS:
        return
    try:
        localS.deleteItem(LS_KEY)
    except Exception:
        pass


# ============================================================
# FUNCTION CALLING
# ============================================================
ROLL_DICE_FUNCTION = Function(
    name="roll_dice",
    description="Бросить кубики.",
    parameters={
        "type": "object",
        "properties": {
            "expression": {"type": "string"},
            "reason":     {"type": "string"},
            "difficulty": {"type": "integer"},
        },
        "required": ["expression", "reason", "difficulty"],
    },
)


def call_roll_dice(args: dict) -> dict:
    try:
        return roll_dice(
            expression=args.get("expression", "1d100"),
            reason=args.get("reason", ""),
            difficulty=int(args.get("difficulty", 0)),
        )
    except Exception as e:
        return {"error": str(e)}


# ============================================================
# ПАРСЕР БРОСКОВ
# ============================================================
_LINE_PATTERN = re.compile(
    r"🎲\s*Бросок\s+(?P<formula>\S+)"
    r"(?:\s*\((?P<reason>[^)]+)\))?"
    r"[^\n]*?"
    r"выпало\s+\[?(?P<roll1>\d+)\]?"
    r"(?:\s*\+\s*\[?(?P<mod>\d+)\]?)?"
    r"(?:\s*=\s*\[?(?P<total>\d+)\]?)?",
    re.IGNORECASE,
)
_DIFF_PATTERN = re.compile(r"сложность\s+(\d+)", re.IGNORECASE)


def _compute_check_result(formula, total, difficulty):
    if difficulty <= 0 or "d100" not in formula.lower():
        return None, 0
    if total <= difficulty:
        return True, (difficulty - total) // 10
    return False, (total - difficulty) // 10


def parse_rolls_from_text(text: str):
    if not text:
        return text, []
    found_rolls, cleaned_lines = [], []
    for line in text.split("\n"):
        if "🎲" in line and "Бросок" in line:
            match = _LINE_PATTERN.search(line)
            if match:
                formula = match.group("formula")
                reason = match.group("reason") or ""
                roll1 = int(match.group("roll1"))
                mod = int(match.group("mod")) if match.group("mod") else 0
                total_str = match.group("total")
                total = int(total_str) if total_str else (roll1 + mod)
                diff_match = _DIFF_PATTERN.search(line)
                difficulty = int(diff_match.group(1)) if diff_match else 0
                success, margin = _compute_check_result(formula, total, difficulty)
                found_rolls.append({
                    "expression": formula, "reason": reason,
                    "rolls": [roll1], "modifier": mod, "total": total,
                    "difficulty": difficulty, "success": success,
                    "margin": margin, "_from_text": True,
                })
                continue
        cleaned_lines.append(line)
    cleaned = "\n".join(cleaned_lines).strip()
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned, found_rolls


# ============================================================
# ПАРСЕР [STATE]
# ============================================================
_STATE_RE = re.compile(r"\[STATE\](.*?)\[/STATE\]", re.DOTALL | re.IGNORECASE)


def parse_state_block(text: str):
    if not text:
        return text, {}
    match = _STATE_RE.search(text)
    if not match:
        return text, {}
    block = match.group(1)
    updates = {}
    for line in block.strip().split("\n"):
        line = line.strip()
        if not line or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if key:
            updates[key] = value
    cleaned = _STATE_RE.sub("", text).strip()
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned, updates


def _parse_signed_int(value: str):
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def apply_state_updates(sheet: dict, updates: dict) -> dict:
    if not updates or not isinstance(sheet, dict):
        return sheet

    if "wounds" in updates:
        val = _parse_signed_int(updates["wounds"])
        if val is not None:
            if "wounds" not in sheet or not isinstance(sheet["wounds"], dict):
                sheet["wounds"] = {"current": val, "max": val}
            else:
                sheet["wounds"]["current"] = val

    if "fate" in updates:
        val = _parse_signed_int(updates["fate"])
        if val is not None:
            if "fate_points" not in sheet or not isinstance(sheet["fate_points"], dict):
                sheet["fate_points"] = {"current": val, "max": val}
            else:
                sheet["fate_points"]["current"] = val

    for key in ("insanity", "corruption", "xp"):
        if key in updates:
            val = _parse_signed_int(updates[key])
            if val is not None:
                sheet[key] = val

    if "money" in updates:
        val = _parse_signed_int(updates["money"])
        if val is not None:
            if updates["money"].strip().startswith(("+", "-")):
                sheet["money"] = sheet.get("money", 0) + val
            else:
                sheet["money"] = val

    for key, value in updates.items():
        if key.startswith("extra_money_"):
            currency = key[len("extra_money_"):].strip()
            val = _parse_signed_int(value)
            if val is None or not currency:
                continue
            extra = sheet.setdefault("extra_currencies", {})
            if value.strip().startswith(("+", "-")):
                extra[currency] = extra.get(currency, 0) + val
            else:
                extra[currency] = val
            if extra[currency] <= 0:
                extra.pop(currency, None)

    for key, value in updates.items():
        if key.startswith("special_"):
            res = key[len("special_"):].strip()
            val = _parse_signed_int(value)
            if val is None or not res:
                continue
            sr = sheet.setdefault("special_resources", {})
            if value.strip().startswith(("+", "-")):
                sr[res] = sr.get(res, 0) + val
            else:
                sr[res] = val
            if sr[res] <= 0:
                sr.pop(res, None)

    for key, value in updates.items():
        if key.startswith("reputation_"):
            fac = key[len("reputation_"):].strip()
            val = _parse_signed_int(value)
            if val is None or not fac:
                continue
            rep = sheet.setdefault("reputation", {})
            if value.strip().startswith(("+", "-")):
                rep[fac] = rep.get(fac, 0) + val
            else:
                rep[fac] = val

    if "location" in updates:
        sheet["location"] = updates["location"]
    if "date" in updates:
        sheet["game_date"] = updates["date"]

    for short in ["quest", "npc", "effect", "companion", "goal"]:
        plural = {
            "quest": "quests", "npc": "npcs", "effect": "effects",
            "companion": "companions", "goal": "goals",
        }[short]
        add_key = f"{short}_add"
        rem_key = f"{short}_remove"
        if add_key in updates:
            items = [i.strip() for i in updates[add_key].split(";") if i.strip()]
            lst = sheet.setdefault(plural, [])
            for it in items:
                if it not in lst:
                    lst.append(it)
        if rem_key in updates:
            items = [i.strip() for i in updates[rem_key].split(";") if i.strip()]
            sheet[plural] = [x for x in sheet.get(plural, []) if x not in items]

    if "journal" in updates:
        entry = updates["journal"].strip()
        if entry:
            sheet.setdefault("journal", []).append(entry)

    for ch in cc.CHARACTERISTICS:
        key = f"characteristic_{ch.lower()}"
        if key in updates:
            val = _parse_signed_int(updates[key])
            if val is not None:
                sheet.setdefault("characteristics", {})[ch] = val
                sheet.setdefault("bonuses", {})[ch] = val // 10

    if sheet.get("ship"):
        ship = sheet["ship"]
        if "ship_hull" in updates:
            val = _parse_signed_int(updates["ship_hull"])
            if val is not None:
                ship.setdefault("hull", {"current": val, "max": val})["current"] = val
        if "ship_crew" in updates:
            val = _parse_signed_int(updates["ship_crew"])
            if val is not None:
                ship.setdefault("crew", {"current": val, "max": val})["current"] = val
        if "ship_status" in updates:
            ship["status"] = updates["ship_status"]
        if "ship_note" in updates:
            ship["notes"] = (ship.get("notes", "") + "\n" + updates["ship_note"]).strip()

    return sheet


# ============================================================
# РЕНДЕР БРОСКА
# ============================================================
def format_roll_text(r: dict) -> str:
    expr = r.get("expression", "?")
    reason = r.get("reason", "")
    rolls = r.get("rolls", [])
    mod = r.get("modifier", 0)
    total = r.get("total", 0)
    difficulty = r.get("difficulty", 0)
    success = r.get("success")
    margin = r.get("margin", 0)
    header = f"🎲 Бросок {expr}"
    if reason:
        header += f" ({reason})"
    header += ": "
    roll1 = rolls[0] if rolls else total
    if mod:
        detail = f"выпало [{roll1}] + {mod} = {total}"
    else:
        detail = f"выпало [{roll1}]"
    if "1d100" in expr.lower() and difficulty > 0 and success is not None:
        if success:
            detail += f" — ✅ УСПЕХ (сложность {difficulty}, степеней успеха: {margin})"
        else:
            detail += f" — ❌ ПРОВАЛ (сложность {difficulty}, степеней провала: {margin})"
    return header + detail


def render_roll(r: dict):
    if not isinstance(r, dict):
        st.warning(f"Некорректный результат броска: {r}")
        return
    if "error" in r:
        st.error(f"Ошибка броска: {r['error']}")
        return
    text = format_roll_text(r)
    expr = r.get("expression", "").lower()
    difficulty = r.get("difficulty", 0)
    if "1d100" in expr and difficulty > 0:
        (st.success if r.get("success") else st.error)(text)
    else:
        st.info(text)


# ============================================================
# БЫСТРЫЕ ДЕЙСТВИЯ
# ============================================================
def _find_in_equipment(sheet, roots):
    for i, e in enumerate(sheet.get("equipment", [])):
        el = e.lower()
        for root in roots:
            if root in el:
                return i, e
    return None, None


def quick_fate_point(sheet):
    fate = sheet.get("fate_points", {})
    if fate.get("current", 0) < 1:
        return None, "Нет Очков Судьбы"
    fate["current"] -= 1
    return "Игрок потратил 1 Очко Судьбы. Опиши, как судьба повернулась в его пользу.", None


def quick_grenade(sheet):
    idx, item = _find_in_equipment(sheet, ["гранат"])
    if idx is None:
        return None, "Нет гранат"
    sheet["equipment"].pop(idx)
    return f"Игрок использовал гранату: {item}. Опиши взрыв.", None


def quick_medkit(sheet):
    idx, item = _find_in_equipment(sheet, ["аптеч", "медипак", "медпак"])
    if idx is None:
        return None, "Нет аптечки"
    sheet["equipment"].pop(idx)
    w = sheet.get("wounds", {})
    before = w.get("current", 0)
    max_w = w.get("max", before)
    after = min(max_w, before + 2)
    w["current"] = after
    return f"Игрок использовал аптечку ({item}). Раны: {before} → {after}.", None


def quick_stimulant(sheet):
    idx, item = _find_in_equipment(sheet, ["стимул", "боевой наркотик"])
    if idx is None:
        return None, "Нет стимуляторов"
    sheet["equipment"].pop(idx)
    sheet.setdefault("effects", []).append("Стимулятор (+10 Ag, 3 хода)")
    return f"Игрок принял стимулятор: {item}. Добавлен эффект «Стимулятор (+10 Ag, 3 хода)».", None


def quick_remove_effect(sheet, effect_name):
    effects = sheet.get("effects", [])
    if effect_name in effects:
        effects.remove(effect_name)
        return f"Игрок снял эффект: {effect_name}.", None
    return None, "Эффект не найден"


def _send_quick_action(msg, sheet, chat_history, localS):
    """Отправляет [ДЕЙСТВИЕ] как user-сообщение и сохраняет."""
    chat_history.append({"role": "user", "content": f"[ДЕЙСТВИЕ] {msg}", "rolls": []})
    cc.save_chat_history(sheet.get("name", "unnamed"), chat_history)
    cc.save_character(sheet)
    _ls_save(localS, sheet, chat_history)


# ============================================================
# ВИЗАРД
# ============================================================
def init_wizard():
    if "wizard_step" not in st.session_state:
        st.session_state.wizard_step = 0
    if "wizard_data" not in st.session_state:
        st.session_state.wizard_data = {
            "generation_method": None, "faction_id": None, "subfaction_id": None,
            "archetype_id": None, "extra_choices": {}, "characteristics": {},
            "name": "", "age": "", "appearance": "", "background": "",
            "sheet": None, "dice_rolled_once": False, "reroll_used": False,
        }


def wizard_go(step: int):
    st.session_state.wizard_step = step


def render_wizard(localS):
    init_wizard()
    step = st.session_state.wizard_step
    data = st.session_state.wizard_data

    st.title("⚔️ Создание персонажа")
    st.progress((step + 1) / 8)
    st.caption(f"Шаг {step + 1} из 8")

    if step == 0:
        st.header("Как генерировать характеристики?")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🎲 Броски кубиков (2d10 + модификатор)", use_container_width=True):
                data["generation_method"] = "dice"; wizard_go(1); st.rerun()
        with col2:
            if st.button("⚖️ Распределение очков (point-buy)", use_container_width=True):
                data["generation_method"] = "pointbuy"; wizard_go(1); st.rerun()

    elif step == 1:
        st.header("Выбери фракцию")
        for fid in factions_data.FACTION_ORDER:
            f = factions_data.FACTIONS[fid]
            with st.container(border=True):
                cols = st.columns([1, 8, 2])
                with cols[0]: st.markdown(f"### {f['icon']}")
                with cols[1]:
                    st.markdown(f"**{f['name']}**")
                    st.caption(f["description"])
                with cols[2]:
                    if st.button("Выбрать", key=f"faction_{fid}", use_container_width=True):
                        data["faction_id"] = fid
                        data["subfaction_id"] = None
                        data["archetype_id"] = None
                        wizard_go(2); st.rerun()
        if st.button("← Назад"): wizard_go(0); st.rerun()

    elif step == 2:
        fid = data["faction_id"]
        f = factions_data.FACTIONS[fid]
        st.header(f"{f['icon']} {f['name']} — выбери путь")
        for sid, sub in f["subfactions"].items():
            with st.container(border=True):
                cols = st.columns([8, 2])
                with cols[0]:
                    st.markdown(f"**{sub['name']}**")
                    st.caption(sub["description"])
                with cols[1]:
                    if st.button("Выбрать", key=f"sub_{sid}", use_container_width=True):
                        data["subfaction_id"] = sid
                        data["archetype_id"] = None
                        wizard_go(3); st.rerun()
        if st.button("← Назад"): wizard_go(1); st.rerun()

    elif step == 3:
        fid = data["faction_id"]
        sid = data["subfaction_id"]
        sub = factions_data.FACTIONS[fid]["subfactions"][sid]
        st.header(f"{sub['name']} — выбери архетип")
        for aid, arch in sub["archetypes"].items():
            with st.container(border=True):
                cols = st.columns([8, 2])
                with cols[0]:
                    st.markdown(f"**{arch['name']}**")
                    st.caption(arch["description"])
                with cols[1]:
                    if st.button("Выбрать", key=f"arch_{aid}", use_container_width=True):
                        data["archetype_id"] = aid
                        data["extra_choices"] = {}
                        wizard_go(4 if sub.get("extra_choices") else 5)
                        st.rerun()
        if st.button("← Назад"): wizard_go(2); st.rerun()

    elif step == 4:
        fid = data["faction_id"]
        sid = data["subfaction_id"]
        sub = factions_data.FACTIONS[fid]["subfactions"][sid]
        st.header("Дополнительные параметры")
        for key, spec in sub.get("extra_choices", {}).items():
            st.subheader(spec["label"])
            choice = st.radio(spec["label"], options=spec["options"],
                              key=f"extra_{key}", label_visibility="collapsed")
            data["extra_choices"][spec["label"]] = choice
        cols = st.columns(2)
        with cols[0]:
            if st.button("← Назад"): wizard_go(3); st.rerun()
        with cols[1]:
            if st.button("Далее →", use_container_width=True): wizard_go(5); st.rerun()

    elif step == 5:
        fid = data["faction_id"]
        sid = data["subfaction_id"]
        sub = factions_data.FACTIONS[fid]["subfactions"][sid]
        dice_mod = sub.get("dice_modifier", 25)
        st.header("Характеристики")
        if data["generation_method"] == "dice":
            if not data.get("dice_rolled_once"):
                st.write(f"Бросок **2d10 + {dice_mod}**.")
                if st.button("🎲 Бросить кубики", use_container_width=True):
                    data["characteristics"] = cc.generate_by_dice(dice_mod)
                    data["dice_rolled_once"] = True
                    st.rerun()
            else:
                for ch in cc.CHARACTERISTICS:
                    val = data["characteristics"][ch]
                    st.write(f"**{cc.CHARACTERISTIC_NAMES_RU[ch]}**: {val} (+{cc.char_bonus(val)})")
                st.write("---")
                if not data.get("reroll_used"):
                    rt = st.selectbox("Перебросить одну?",
                                      options=["—"] + cc.CHARACTERISTICS,
                                      format_func=lambda x: "—" if x == "—" else cc.CHARACTERISTIC_NAMES_RU[x])
                    if st.button("Перебросить") and rt != "—":
                        data["characteristics"] = cc.reroll_one(data["characteristics"], rt, dice_mod)
                        data["reroll_used"] = True
                        st.rerun()
                cols = st.columns(2)
                with cols[0]:
                    if st.button("← Назад"):
                        wizard_go(4 if sub.get("extra_choices") else 3); st.rerun()
                with cols[1]:
                    if st.button("Далее →", use_container_width=True): wizard_go(6); st.rerun()
        else:
            if "pointbuy_values" not in st.session_state:
                st.session_state.pointbuy_values = {ch: 25 for ch in cc.CHARACTERISTICS}
            pv = st.session_state.pointbuy_values
            for ch in cc.CHARACTERISTICS:
                pv[ch] = st.slider(cc.CHARACTERISTIC_NAMES_RU[ch], 25, 45, pv[ch], key=f"pb_{ch}")
            spent = sum(v - 25 for v in pv.values())
            left = 100 - spent
            st.write(f"**Осталось: {left}**")
            cols = st.columns(2)
            with cols[0]:
                if st.button("← Назад"):
                    wizard_go(4 if sub.get("extra_choices") else 3); st.rerun()
            with cols[1]:
                if st.button("Далее →", disabled=(left < 0), use_container_width=True):
                    data["characteristics"] = dict(pv); wizard_go(6); st.rerun()

    elif step == 6:
        st.header("Имя и детали")
        data["name"] = st.text_input("Имя *", value=data.get("name", ""))
        data["age"] = st.text_input("Возраст", value=data.get("age", ""))
        data["appearance"] = st.text_area("Внешность", value=data.get("appearance", ""), height=100)
        data["background"] = st.text_area("Предыстория", value=data.get("background", ""), height=150)
        cols = st.columns(2)
        with cols[0]:
            if st.button("← Назад"): wizard_go(5); st.rerun()
        with cols[1]:
            if st.button("Собрать лист →", use_container_width=True):
                if not data["name"].strip():
                    st.error("Введи имя")
                else:
                    wizard_go(7); st.rerun()

    elif step == 7:
        st.header("Лист персонажа")
        if not data.get("sheet"):
            with st.spinner("Мастер составляет лист..."):
                try:
                    fid, sid, aid = data["faction_id"], data["subfaction_id"], data["archetype_id"]
                    f = factions_data.FACTIONS[fid]
                    sub = f["subfactions"][sid]
                    arch = sub["archetypes"][aid]
                    sheet = cc.generate_full_sheet(
                        kb=get_kb(), faction_id=fid, subfaction_id=sid, archetype_id=aid,
                        faction_name=f["name"], subfaction_name=sub["name"], archetype_name=arch["name"],
                        extra_choices=data.get("extra_choices", {}),
                        characteristics=data["characteristics"],
                        name=data["name"], age=data.get("age", ""),
                        appearance=data.get("appearance", ""), background=data.get("background", ""),
                    )
                    sheet["generation_method"] = data["generation_method"]
                    data["sheet"] = sheet
                except Exception as e:
                    st.error(f"Ошибка: {e}")
                    if st.button("← Назад"): wizard_go(6); st.rerun()
                    return

        sheet = data["sheet"]
        st.subheader(sheet["name"])
        st.caption(f"{sheet.get('faction','')} → {sheet.get('subfaction','')} → {sheet.get('archetype','')}")

        cols = st.columns(9)
        for i, ch in enumerate(cc.CHARACTERISTICS):
            cols[i].metric(ch, f"{sheet['characteristics'][ch]}", f"+{sheet['bonuses'][ch]}")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Раны", f"{sheet['wounds']['current']}/{sheet['wounds']['max']}")
        c2.metric("Судьба", f"{sheet['fate_points']['current']}/{sheet['fate_points']['max']}")
        c3.metric("Порча", sheet.get("corruption", 0))
        c4.metric("Пси-Рейтинг", sheet.get("psy_rating", 0))

        c1, c2 = st.columns(2)
        c1.metric(f"💰 {sheet.get('currency','Троны')}", sheet.get("money", 0))
        c2.metric("🚀 Корабль", sheet["ship"]["name"] if sheet.get("ship") else "нет")

        with st.expander("Снаряжение"):
            for e in sheet.get("equipment", []): st.write(f"- {e}")

        if sheet.get("background"):
            with st.expander("Предыстория"):
                st.write(sheet["background"])

        st.write("---")
        cols = st.columns([1, 1, 2])
        with cols[0]:
            if st.button("← Назад"): data["sheet"] = None; wizard_go(6); st.rerun()
        with cols[1]:
            if st.button("🔄 Перегенерировать", use_container_width=True):
                data["sheet"] = None; st.rerun()
        with cols[2]:
            if st.button("✅ Подтвердить и начать игру", type="primary", use_container_width=True):
                path = cc.save_character(sheet)
                st.session_state.character = sheet
                st.session_state.character_path = path
                st.session_state.chat_history = []
                cc.save_chat_history(sheet.get("name", "unnamed"), [])
                _ls_save(localS, sheet, [])  # перезаписать LS новым
                st.session_state.wizard_step = 0
                st.session_state.wizard_data = {}
                st.session_state.in_wizard = False
                st.rerun()


# ============================================================
# СТАРТОВЫЙ ЭКРАН
# ============================================================
def _download_save_payload(sheet, chat_history):
    return json.dumps({
        "format": SAVE_FORMAT,
        "version": SAVE_VERSION,
        "character": sheet,
        "chat_history": chat_history,
        "saved_at": datetime.now().isoformat(),
    }, ensure_ascii=False, indent=2)


def render_start_screen(localS):
    st.title("⚔️ Warhammer 40,000 — RPG с ИИ-Мастером")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🆕 Новая игра")
        if st.button("Создать персонажа", type="primary", use_container_width=True):
            st.session_state.wizard_step = 0
            st.session_state.wizard_data = {}
            st.session_state.in_wizard = True
            st.rerun()

    with col2:
        st.subheader("📥 Загрузить из файла")
        uploaded = st.file_uploader("JSON-файл сохранения", type=["json"],
                                     label_visibility="collapsed")
        if uploaded is not None:
            try:
                data = json.loads(uploaded.read().decode("utf-8"))
                if data.get("format") != SAVE_FORMAT:
                    st.error("Не наш формат сохранения.")
                elif not data.get("character"):
                    st.error("Файл без персонажа.")
                else:
                    st.session_state.character = data["character"]
                    st.session_state.chat_history = data.get("chat_history", [])
                    st.session_state.in_wizard = False
                    cc.save_character(data["character"])
                    cc.save_chat_history(data["character"].get("name", "unnamed"),
                                         st.session_state.chat_history)
                    _ls_save(localS, data["character"], st.session_state.chat_history)
                    st.success("Персонаж загружен!")
                    st.rerun()
            except Exception as e:
                st.error(f"Ошибка чтения файла: {e}")

    st.write("---")
    st.subheader("📂 Продолжить")

    chars = cc.list_characters()
    if not chars:
        st.info("Нет сохранённых персонажей.")
    else:
        for c in chars:
            with st.container(border=True):
                cols = st.columns([4, 1, 1, 1])
                with cols[0]:
                    st.markdown(f"**{c['name']}**")
                    st.caption(f"{c.get('faction','')} → {c.get('subfaction','')} → {c.get('archetype','')}")
                with cols[1]:
                    if st.button("▶️ Играть", key=f"load_{c['name']}", use_container_width=True):
                        sheet = cc.load_character(c["path"])
                        chat = cc.load_chat_history(c["name"])
                        st.session_state.character = sheet
                        st.session_state.character_path = c["path"]
                        st.session_state.chat_history = chat
                        st.session_state.in_wizard = False
                        _ls_save(localS, sheet, chat)
                        st.rerun()
                with cols[2]:
                    # Скачать сейв (лист + история)
                    try:
                        sheet_data = cc.load_character(c["path"])
                        chat_data = cc.load_chat_history(c["name"])
                        payload = _download_save_payload(sheet_data, chat_data)
                        st.download_button(
                            "💾",
                            data=payload,
                            file_name=f"{c['name']}_save.json",
                            mime="application/json",
                            key=f"dl_{c['name']}",
                            use_container_width=True,
                            help="Скачать сохранение (лист + история)",
                        )
                    except Exception:
                        st.caption("—")
                with cols[3]:
                    if st.button("🗑", key=f"del_{c['name']}", use_container_width=True,
                                 help="Удалить персонажа"):
                        cc.delete_character(c["path"])
                        cc.delete_chat_history(c["name"])
                        st.rerun()

    st.write("---")

    # Кнопка очистки localStorage
    cols = st.columns([3, 2, 3])
    with cols[1]:
        if st.button("🗑 Очистить сохранение в браузере", use_container_width=True,
                     help="Удаляет автосохранение. Файлы на диске не тронутся."):
            _ls_clear(localS)
            st.toast("Автосохранение очищено", icon="✅")


# ============================================================
# САЙДБАР
# ============================================================
def _render_quick_actions(sheet, chat_history, localS):
    st.markdown("**⚡ Быстрые действия**")
    cols = st.columns(2)
    with cols[0]:
        if st.button("🔥 Очко Судьбы", use_container_width=True, help="Потратить Очко Судьбы"):
            msg, err = quick_fate_point(sheet)
            if err:
                st.toast(err, icon="⚠️")
            else:
                _send_quick_action(msg, sheet, chat_history, localS)
                st.rerun()
    with cols[1]:
        if st.button("💣 Граната", use_container_width=True):
            msg, err = quick_grenade(sheet)
            if err:
                st.toast(err, icon="⚠️")
            else:
                _send_quick_action(msg, sheet, chat_history, localS)
                st.rerun()
    cols = st.columns(2)
    with cols[0]:
        if st.button("🏥 Аптечка", use_container_width=True):
            msg, err = quick_medkit(sheet)
            if err:
                st.toast(err, icon="⚠️")
            else:
                _send_quick_action(msg, sheet, chat_history, localS)
                st.rerun()
    with cols[1]:
        if st.button("⚡ Стимулятор", use_container_width=True):
            msg, err = quick_stimulant(sheet)
            if err:
                st.toast(err, icon="⚠️")
            else:
                _send_quick_action(msg, sheet, chat_history, localS)
                st.rerun()

    effects = sheet.get("effects", [])
    if effects:
        eff_to_remove = st.selectbox(
            "Снять эффект", options=["—"] + effects,
            key="effect_remove_select", label_visibility="collapsed",
        )
        if eff_to_remove != "—" and st.button("✖️ Снять эффект", use_container_width=True):
            msg, err = quick_remove_effect(sheet, eff_to_remove)
            if err:
                st.toast(err, icon="⚠️")
            else:
                _send_quick_action(msg, sheet, chat_history, localS)
                st.rerun()


def render_character_sidebar(sheet, kb, model, localS, chat_history):
    st.header("👤 Персонаж")
    st.write(f"**{sheet['name']}**")
    st.caption(f"{sheet.get('faction','')} → {sheet.get('subfaction','')} → {sheet.get('archetype','')}")

    wounds = sheet.get("wounds", {"current": 0, "max": 0})
    fate = sheet.get("fate_points", {"current": 0, "max": 0})

    c1, c2 = st.columns(2)
    c1.metric("❤️ Раны", f"{wounds.get('current', 0)}/{wounds.get('max', 0)}")
    c2.metric("🍀 Судьба", f"{fate.get('current', 0)}/{fate.get('max', 0)}")
    c1, c2 = st.columns(2)
    c1.metric("🌀 Порча", sheet.get("corruption", 0))
    c2.metric("🧠 Безумие", sheet.get("insanity", 0))

    st.write("---")
    _render_quick_actions(sheet, chat_history, localS)
    st.write("---")

    tabs = st.tabs(["👤 Перс", "🎒 Инвент", "🌍 Мир", "🚀 Корабль", "📝 Заметки"])

    with tabs[0]:
        with st.expander("📊 Характеристики", expanded=False):
            for ch in cc.CHARACTERISTICS:
                val = sheet["characteristics"].get(ch, 0)
                bon = sheet.get("bonuses", {}).get(ch, val // 10)
                st.write(f"**{ch}**: {val} (+{bon})")
        arm = sheet.get("armour", {})
        if arm:
            with st.expander("🛡️ Броня", expanded=False):
                st.write(f"Голова: **{arm.get('head', 0)}** | Тело: **{arm.get('body', 0)}**")
                st.write(f"Руки: **{arm.get('arms', 0)}** | Ноги: **{arm.get('legs', 0)}**")
                if arm.get("notes"): st.caption(arm["notes"])
        weapons = sheet.get("weapons", [])
        if weapons:
            with st.expander(f"⚔️ Оружие ({len(weapons)})", expanded=False):
                for w in weapons:
                    st.markdown(f"**{w.get('name','')}**")
                    st.caption(w.get("stats", ""))
                    if w.get("notes"): st.caption(f"_{w['notes']}_")
        talents = sheet.get("talents", [])
        if talents:
            with st.expander(f"✨ Таланты ({len(talents)})", expanded=False):
                for t in talents: st.write(f"• {t}")
        skills = sheet.get("skills", [])
        if skills:
            with st.expander(f"📖 Навыки ({len(skills)})", expanded=False):
                for s in skills:
                    st.write(f"• **{s['name']}** ({s.get('characteristic','')}): {s.get('value','')}")
        powers = sheet.get("psychic_powers", [])
        if powers:
            with st.expander(f"🔮 Психосилы ({len(powers)})", expanded=False):
                for p in powers: st.write(f"• {p}")

    with tabs[1]:
        st.markdown(f"### 💰 {sheet.get('currency', 'Троны')}: **{sheet.get('money', 0)}**")
        extra = sheet.get("extra_currencies", {})
        if extra:
            st.markdown("**Чужие валюты:**")
            for cur, amt in extra.items(): st.write(f"• {cur}: **{amt}**")
        sr = sheet.get("special_resources", {})
        if sr:
            st.markdown("**Особые ресурсы:**")
            for res, amt in sr.items(): st.write(f"• {res}: **{amt}**")
        equipment = sheet.get("equipment", [])
        st.markdown(f"### 🎒 Снаряжение ({len(equipment)})")
        if equipment:
            for e in equipment: st.write(f"• {e}")
        else:
            st.caption("— пусто —")
        companions = sheet.get("companions", [])
        if companions:
            st.markdown("**🐾 Спутники:**")
            for c in companions: st.write(f"• {c}")

    with tabs[2]:
        loc = sheet.get("location", "")
        date = sheet.get("game_date", "")
        if loc: st.markdown(f"📍 **Локация:** {loc}")
        if date: st.markdown(f"⏱️ **Время:** {date}")
        quests = sheet.get("quests", [])
        if quests:
            st.markdown("**📋 Задачи:**")
            for q in quests: st.write(f"• {q}")
        npcs = sheet.get("npcs", [])
        if npcs:
            st.markdown("**👥 NPC:**")
            for n in npcs: st.write(f"• {n}")
        effects = sheet.get("effects", [])
        if effects:
            st.markdown("**⚡ Эффекты:**")
            for e in effects: st.write(f"• {e}")
        goals = sheet.get("goals", [])
        if goals:
            st.markdown("**🎯 Цели:**")
            for g in goals: st.write(f"• {g}")
        rep = sheet.get("reputation", {})
        if rep:
            st.markdown("**🌍 Репутация:**")
            for k, v in rep.items():
                if v != 0:
                    sign = "+" if v > 0 else ""
                    st.write(f"• {k}: **{sign}{v}**")

    with tabs[3]:
        ship = sheet.get("ship")
        if not ship:
            st.info("У персонажа нет корабля.")
        else:
            st.markdown(f"### 🚀 {ship['name']}")
            st.caption(f"{ship.get('class','')} • {ship.get('type','')}")
            if ship.get("status"): st.write(f"**Статус:** {ship['status']}")
            st.write(ship.get("description", ""))
            hull = ship.get("hull", {})
            crew = ship.get("crew", {})
            c1, c2 = st.columns(2)
            c1.metric("Корпус", f"{hull.get('current',0)}/{hull.get('max',0)}")
            c2.metric("Экипаж", f"{crew.get('current',0)}/{crew.get('max',0)}")
            if ship.get("weapons"):
                st.markdown("**Оружие:**")
                for w in ship["weapons"]: st.write(f"• {w}")
            if ship.get("features"):
                st.markdown("**Особенности:**")
                for f in ship["features"]: st.write(f"• {f}")
            if ship.get("notes"):
                st.markdown("**Заметки:**")
                st.write(ship["notes"])

    with tabs[4]:
        notes_key = f"notes_field_{sheet.get('name', 'unnamed')}"
        if notes_key not in st.session_state:
            st.session_state[notes_key] = sheet.get("notes", "")

        def _save_notes():
            st.session_state.character["notes"] = st.session_state[notes_key]
            try:
                cc.save_character(st.session_state.character)
                _ls_save(localS, st.session_state.character,
                         st.session_state.get("chat_history", []))
            except Exception:
                pass

        st.markdown("**📝 Мои заметки**")
        st.text_area("Заметки", key=notes_key, height=200,
                     label_visibility="collapsed",
                     placeholder="Имена NPC, планы, зацепки, долги...",
                     on_change=_save_notes)
        journal = sheet.get("journal", [])
        if journal:
            st.markdown("**📖 Дневник событий**")
            for entry in journal: st.write(f"• {entry}")

    st.write("---")
    st.caption(f"📚 Чанков: {kb.chunk_count} | 💬 Ходов: {len(chat_history)}")

    # ---- Экспорт / импорт ----
    with st.expander("⚙️ Экспорт / Импорт"):
        try:
            payload = _download_save_payload(sheet, chat_history)
            st.download_button(
                "💾 Скачать сейв (лист + история)",
                data=payload,
                file_name=f"{sheet.get('name','unnamed')}_save.json",
                mime="application/json",
                use_container_width=True,
            )
        except Exception as e:
            st.caption(f"Ошибка: {e}")

        uploaded = st.file_uploader("📥 Загрузить сейв", type=["json"],
                                     key="sidebar_upload",
                                     label_visibility="collapsed")
        if uploaded is not None:
            try:
                data = json.loads(uploaded.read().decode("utf-8"))
                if data.get("format") != SAVE_FORMAT:
                    st.error("Не наш формат.")
                else:
                    st.session_state.character = data["character"]
                    st.session_state.chat_history = data.get("chat_history", [])
                    _ls_save(localS, data["character"], st.session_state.chat_history)
                    st.rerun()
            except Exception as e:
                st.error(f"Ошибка: {e}")

    with st.expander("🛠 Отладка"):
        log_data = {
            "character": sheet,
            "chat_history": chat_history,
            "meta": {"model": model, "chunks_in_db": kb.chunk_count,
                     "vector_mode": kb.is_vector_mode,
                     "exported_at": datetime.now().isoformat()},
        }
        st.download_button(
            "📥 Скачать логи",
            data=json.dumps(log_data, ensure_ascii=False, indent=2),
            file_name=f"session_{sheet.get('name','unnamed')}.json",
            mime="application/json", use_container_width=True,
        )
        if st.button("👁 Последний запрос", use_container_width=True):
            st.session_state.show_last_request = not st.session_state.get("show_last_request", False)
        if st.session_state.get("show_last_request"):
            st.code(st.session_state.get("last_request_to_giga", "—"), language="text")

    st.write("---")
    if st.button("🔄 Начать историю заново", use_container_width=True):
        st.session_state.chat_history = []
        cc.save_chat_history(sheet.get("name", "unnamed"), [])
        _ls_save(localS, sheet, [])
        st.rerun()

    if st.button("Выйти в меню", use_container_width=True):
        cc.save_chat_history(sheet.get("name", "unnamed"), chat_history)
        _ls_save(localS, sheet, chat_history)
        st.session_state.character = None
        st.session_state.chat_history = []
        st.session_state.show_last_request = False
        st.rerun()


# ============================================================
# ЧАТ
# ============================================================
def build_intro_message(sheet: dict) -> str:
    return (
        f"=== ПЕРСОНАЖ ИГРОКА ===\n"
        f"{json.dumps(sheet, ensure_ascii=False, indent=2)}\n\n"
        f"=== ЗАДАЧА ===\n"
        f"Начни игру. Опиши первую сцену от второго лица.\n\n"
        f"ЖЁСТКИЕ ТРЕБОВАНИЯ:\n"
        f"1. Раса: {sheet.get('faction','?')}. Субфракция: {sheet.get('subfaction','?')}. "
        f"Архетип: {sheet.get('archetype','?')}.\n"
        f"2. Окружение ДОЛЖНО соответствовать расе.\n"
        f"3. Длина: 3-5 предложений. Закончи на моменте для решения игрока.\n"
        f"4. Не вводи NPC, чуждых расе персонажа."
    )


def render_chat(localS):
    kb = get_kb()
    giga = get_giga()
    master_prompt = get_master_prompt()

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    with st.sidebar:
        render_character_sidebar(st.session_state.character, kb, MODEL,
                                 localS, st.session_state.chat_history)

    st.title("🎲 Игра")

    if not st.session_state.chat_history:
        intro_user = build_intro_message(st.session_state.character)
        with st.spinner("Мастер готовит вступление..."):
            try:
                resp = giga.chat(Chat(messages=[
                    Messages(role=MessagesRole.SYSTEM, content=master_prompt),
                    Messages(role=MessagesRole.USER, content=intro_user),
                ]))
                intro_text = resp.choices[0].message.content
                intro_text, state_updates = parse_state_block(intro_text)
                intro_text, intro_rolls = parse_rolls_from_text(intro_text)
                if state_updates:
                    st.session_state.character = apply_state_updates(
                        st.session_state.character, state_updates)
                    try:
                        new_path = cc.save_character(st.session_state.character)
                        st.session_state.character_path = new_path
                    except Exception:
                        pass
                st.session_state.chat_history.append({
                    "role": "assistant", "content": intro_text, "rolls": intro_rolls,
                })
                cc.save_chat_history(st.session_state.character.get("name", "unnamed"),
                                     st.session_state.chat_history)
                _ls_save(localS, st.session_state.character,
                         st.session_state.chat_history)
            except Exception as e:
                st.error(f"Ошибка вступления: {e}")

    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            for r in msg.get("rolls", []):
                render_roll(r)
            st.markdown(msg["content"])

    user_input = st.chat_input("Что делаешь?")
    if not user_input:
        return

    st.session_state.chat_history.append({"role": "user", "content": user_input, "rolls": []})
    with st.chat_message("user"):
        st.markdown(user_input)
    cc.save_chat_history(st.session_state.character.get("name", "unnamed"),
                         st.session_state.chat_history)
    _ls_save(localS, st.session_state.character, st.session_state.chat_history)

    context = kb.format_context(user_input, top_k=TOP_K_KNOWLEDGE)
    sheet_json = json.dumps(st.session_state.character, ensure_ascii=False, indent=2)
    parts = [f"=== АКТУАЛЬНЫЙ ЛИСТ ПЕРСОНАЖА ===\n{sheet_json}"]
    if context:
        parts.append(context)
    parts.append(f"=== СООБЩЕНИЕ ИГРОКА ===\n{user_input}")
    enriched = "\n\n".join(parts)

    giga_messages = [Messages(role=MessagesRole.SYSTEM, content=master_prompt)]
    last_idx = len(st.session_state.chat_history) - 1
    for i, m in enumerate(st.session_state.chat_history):
        role = MessagesRole.USER if m["role"] == "user" else MessagesRole.ASSISTANT
        content = m["content"]
        if i == last_idx and m["role"] == "user":
            content = enriched
        giga_messages.append(Messages(role=role, content=content))

    last_user_msg = next(
        (m.content for m in reversed(giga_messages) if m.role == MessagesRole.USER), "")
    st.session_state.last_request_to_giga = last_user_msg

    with st.chat_message("assistant"):
        rolls_to_render = []
        final_text = None
        with st.spinner("Мастер думает..."):
            for _ in range(MAX_FUNCTION_ITERATIONS):
                try:
                    resp = giga.chat(Chat(
                        messages=giga_messages,
                        functions=[ROLL_DICE_FUNCTION],
                        function_call="auto",
                    ))
                except Exception:
                    try:
                        resp = giga.chat(Chat(messages=giga_messages))
                    except Exception as e2:
                        st.error(f"Ошибка GigaChat: {e2}")
                        break
                msg = resp.choices[0].message
                if getattr(msg, "function_call", None):
                    fn_name = msg.function_call.name
                    try:
                        fn_args = json.loads(msg.function_call.arguments)
                    except Exception:
                        fn_args = {}
                    if fn_name == "roll_dice":
                        result = call_roll_dice(fn_args)
                        rolls_to_render.append(result)
                        giga_messages.append(Messages(
                            role=MessagesRole.ASSISTANT, content="",
                            function_call=msg.function_call))
                        giga_messages.append(Messages(
                            role=MessagesRole.FUNCTION,
                            content=json.dumps(result, ensure_ascii=False),
                            name=fn_name))
                        continue
                final_text = msg.content
                break

        state_updates = {}
        text_rolls = []
        if final_text:
            final_text, state_updates = parse_state_block(final_text)
            final_text, text_rolls = parse_rolls_from_text(final_text)

        if state_updates:
            st.session_state.character = apply_state_updates(
                st.session_state.character, state_updates)
            try:
                new_path = cc.save_character(st.session_state.character)
                st.session_state.character_path = new_path
            except Exception as e:
                print(f"[STATE] ошибка: {e}")

        all_rolls = rolls_to_render + text_rolls
        for r in all_rolls:
            render_roll(r)

        if final_text:
            st.markdown(final_text)
            st.session_state.chat_history.append({
                "role": "assistant", "content": final_text, "rolls": all_rolls,
            })
            cc.save_chat_history(st.session_state.character.get("name", "unnamed"),
                                 st.session_state.chat_history)
            _ls_save(localS, st.session_state.character,
                     st.session_state.chat_history)
            if state_updates:
                st.rerun()
        elif not all_rolls:
            st.markdown("_Не удалось получить ответ._")


# ============================================================
# ГЛАВНАЯ
# ============================================================
def main():
    localS = LocalStorage() if HAS_LS else None

    if "character" not in st.session_state: st.session_state.character = None
    if "in_wizard" not in st.session_state: st.session_state.in_wizard = False
    if "chat_history" not in st.session_state: st.session_state.chat_history = []
    if "show_last_request" not in st.session_state: st.session_state.show_last_request = False

        # ---- Автовосстановление из localStorage ----
    if localS and not st.session_state.get("ls_restore_done") and not st.session_state.character:
        attempts = st.session_state.get("ls_attempts", 0)
        if attempts < 4:
            loaded = _ls_load(localS)
            if loaded and loaded.get("character"):
                char = loaded["character"]
                chat = loaded.get("chat_history", [])

                # Если LS вернул пустую историю — пробуем подтянуть из файла
                if not chat:
                    try:
                        file_chat = cc.load_chat_history(char.get("name", ""))
                        if file_chat:
                            chat = file_chat
                    except Exception:
                        pass

                st.session_state.character = char
                st.session_state.chat_history = chat
                st.session_state.ls_restore_done = True
            else:
                st.session_state.ls_attempts = attempts + 1
                st.rerun()
        else:
            st.session_state.ls_restore_done = True

    # ---- Роутинг ----
    if st.session_state.character:
        render_chat(localS)
    elif st.session_state.in_wizard:
        render_wizard(localS)
    else:
        render_start_screen(localS)


if __name__ == "__main__":
    main()