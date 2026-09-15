# app.py
# Streamlit-приложение: визард создания персонажа + чат с Мастером.
# Совместимо с gigachat 0.2.x.
#
# Механика бросков:
# - GigaChat пишет броски текстом (function calling не работает).
# - Мы парсим строки, сами считаем успех/провал, рендерим плашками.
# - Броски СОХРАНЯЮТСЯ в chat_history и восстанавливаются при перерисовке.

import json
import re
from datetime import datetime

import streamlit as st

from gigachat import GigaChat
from gigachat.models import Chat, Messages, MessagesRole, Function

from dice import roll_dice
from knowledge import KnowledgeBase

import factions_data
import character_creation as cc

from init_db import ensure_db


# ============================================================
# НАСТРОЙКИ
# ============================================================
# Ключ GigaChat читается из .streamlit/secrets.toml (локально)
# или из st.secrets (Streamlit Cloud).
# Fallback — для служебных скриптов, запускаемых без Streamlit-контекста.
try:
    API_KEY = st.secrets["GIGACHAT_API_KEY"]
except Exception:
    API_KEY = "MDFhMDk2NGctZGQ0Yi03NGJiLTkzNWEtODgzMWEwNjZjZDYzOjBkNDViZDZmLTYxYzQtNGYyNC1hYzFlLTczZGY5OWI5MDZiMw=="

MODEL = "GigaChat-2-Pro"
MAX_FUNCTION_ITERATIONS = 15
TOP_K_KNOWLEDGE = 5

MASTER_PROMPT_PATH = "prompts/master.txt"


# ============================================================
# ИНИЦИАЛИЗАЦИЯ
# ============================================================
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
# FUNCTION CALLING (оставляем на случай, если модель научится)
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


def _compute_check_result(formula: str, total: int, difficulty: int):
    """Сами считаем успех/провал. Только для 1d100 с difficulty > 0."""
    if difficulty <= 0 or "d100" not in formula.lower():
        return None, 0
    if total <= difficulty:
        return True, (difficulty - total) // 10
    return False, (total - difficulty) // 10


def parse_rolls_from_text(text: str):
    """
    Ищет строки бросков, извлекает их, возвращает (очищенный_текст, [броски]).
    Строки с бросками полностью удаляются из текста — они рендерятся отдельно.
    """
    if not text:
        return text, []

    found_rolls = []
    cleaned_lines = []

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
                    "expression": formula,
                    "reason": reason,
                    "rolls": [roll1],
                    "modifier": mod,
                    "total": total,
                    "difficulty": difficulty,
                    "success": success,
                    "margin": margin,
                    "_from_text": True,
                })
                continue

        cleaned_lines.append(line)

    cleaned = "\n".join(cleaned_lines).strip()
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned, found_rolls


# ============================================================
# ФОРМАТИРОВАНИЕ И РЕНДЕР БРОСКА
# ============================================================
def format_roll_text(r: dict) -> str:
    """Собирает читаемый текст броска. БЕЗ ✅/❌, если это не проверка."""
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

    is_check = "1d100" in expr.lower()
    if is_check and difficulty > 0 and success is not None:
        if success:
            detail += f" — ✅ УСПЕХ (сложность {difficulty}, степеней успеха: {margin})"
        else:
            detail += f" — ❌ ПРОВАЛ (сложность {difficulty}, степеней провала: {margin})"

    return header + detail


def render_roll(r: dict):
    """Рендерит плашку броска. Цвета зависят от типа броска и результата."""
    if not isinstance(r, dict):
        st.warning(f"Некорректный результат броска: {r}")
        return
    if "error" in r:
        st.error(f"Ошибка броска: {r['error']}")
        return

    text = format_roll_text(r)
    expr = r.get("expression", "").lower()
    difficulty = r.get("difficulty", 0)
    is_check = "1d100" in expr

    if is_check and difficulty > 0:
        if r.get("success"):
            st.success(text)
        else:
            st.error(text)
    else:
        st.info(text)


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


def render_wizard():
    init_wizard()
    step = st.session_state.wizard_step
    data = st.session_state.wizard_data

    st.title("⚔️ Создание персонажа")
    st.progress((step + 1) / 8)
    st.caption(f"Шаг {step + 1} из 8")

    if step == 0:
        st.header("Как генерировать характеристики?")
        st.write("Выбери способ. **Это решение нельзя изменить после подтверждения.**")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🎲 Броски кубиков (2d10 + модификатор)", use_container_width=True):
                data["generation_method"] = "dice"; wizard_go(1); st.rerun()
        with col2:
            if st.button("⚖️ Распределение очков (point-buy)", use_container_width=True):
                data["generation_method"] = "pointbuy"; wizard_go(1); st.rerun()
        st.info("💡 Опытные игроки предпочитают **броски кубиков**.")

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
                st.write(f"Бросок **2d10 + {dice_mod}** для каждой характеристики.")
                if st.button("🎲 Бросить кубики", use_container_width=True):
                    data["characteristics"] = cc.generate_by_dice(dice_mod)
                    data["dice_rolled_once"] = True
                    st.rerun()
            else:
                st.write("Твои характеристики:")
                for ch in cc.CHARACTERISTICS:
                    val = data["characteristics"][ch]
                    st.write(f"**{cc.CHARACTERISTIC_NAMES_RU[ch]}**: {val} (бонус +{cc.char_bonus(val)})")
                st.write("---")
                if not data.get("reroll_used"):
                    st.write("Можешь **перебросить одну** характеристику.")
                    rt = st.selectbox("Какую перебросить?",
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
            st.write("Все характеристики = **25**. **100 очков** для распределения. Максимум +20.")
            if "pointbuy_values" not in st.session_state:
                st.session_state.pointbuy_values = {ch: 25 for ch in cc.CHARACTERISTICS}
            pv = st.session_state.pointbuy_values
            for ch in cc.CHARACTERISTICS:
                pv[ch] = st.slider(cc.CHARACTERISTIC_NAMES_RU[ch],
                                   min_value=25, max_value=45, value=pv[ch], key=f"pb_{ch}")
            spent = sum(v - 25 for v in pv.values())
            left = 100 - spent
            st.write(f"**Осталось очков: {left}**")
            if left < 0: st.error("Превышен лимит!")
            cols = st.columns(2)
            with cols[0]:
                if st.button("← Назад"):
                    wizard_go(4 if sub.get("extra_choices") else 3); st.rerun()
            with cols[1]:
                if st.button("Далее →", use_container_width=True, disabled=(left < 0)):
                    data["characteristics"] = dict(pv); wizard_go(6); st.rerun()

    elif step == 6:
        st.header("Имя и детали")
        data["name"] = st.text_input("Имя персонажа *", value=data.get("name", ""))
        data["age"] = st.text_input("Возраст (необязательно)", value=data.get("age", ""))
        data["appearance"] = st.text_area("Внешность (необязательно)",
                                          value=data.get("appearance", ""), height=100)
        data["background"] = st.text_area("Предыстория (необязательно)",
                                          value=data.get("background", ""), height=150)
        cols = st.columns(2)
        with cols[0]:
            if st.button("← Назад"): wizard_go(5); st.rerun()
        with cols[1]:
            if st.button("Собрать лист →", use_container_width=True):
                if not data["name"].strip():
                    st.error("Введи имя персонажа.")
                else:
                    wizard_go(7); st.rerun()

    elif step == 7:
        st.header("Лист персонажа")
        if not data.get("sheet"):
            with st.spinner("Мастер составляет твой лист..."):
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
                    st.error(f"Ошибка генерации листа: {e}")
                    if st.button("← Назад"): wizard_go(6); st.rerun()
                    return

        sheet = data["sheet"]
        st.subheader(sheet["name"])
        st.caption(f"{sheet.get('faction','')} → {sheet.get('subfaction','')} → {sheet.get('archetype','')}")
        if sheet.get("extra_choices"):
            st.caption(" • ".join(f"{k}: {v}" for k, v in sheet["extra_choices"].items() if v))

        cols = st.columns(9)
        for i, ch in enumerate(cc.CHARACTERISTICS):
            cols[i].metric(ch, f"{sheet['characteristics'][ch]}", f"+{sheet['bonuses'][ch]}")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Раны", f"{sheet['wounds']['current']} / {sheet['wounds']['max']}")
        c2.metric("Судьба", f"{sheet['fate_points']['current']} / {sheet['fate_points']['max']}")
        c3.metric("Порча", sheet.get("corruption", 0))
        c4.metric("Пси-Рейтинг", sheet.get("psy_rating", 0))

        arm = sheet.get("armour", {})
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Голова", arm.get("head", 0)); c2.metric("Тело", arm.get("body", 0))
        c3.metric("Руки", arm.get("arms", 0)); c4.metric("Ноги", arm.get("legs", 0))
        if arm.get("notes"): st.caption(f"Броня: {arm['notes']}")

        with st.expander("Навыки", expanded=True):
            for s in sheet.get("skills", []):
                st.write(f"- **{s['name']}** ({s.get('characteristic','')}): {s.get('value','')}")
        with st.expander("Таланты", expanded=True):
            for t in sheet.get("talents", []): st.write(f"- {t}")
        with st.expander("Оружие", expanded=True):
            for w in sheet.get("weapons", []):
                st.write(f"- **{w.get('name','')}** — {w.get('stats','')}")
                if w.get("notes"): st.caption(f"  Особенности: {w['notes']}")
        with st.expander("Снаряжение", expanded=True):
            for e in sheet.get("equipment", []): st.write(f"- {e}")
        if sheet.get("psychic_powers"):
            with st.expander("Психосилы", expanded=True):
                for p in sheet["psychic_powers"]: st.write(f"- {p}")
        if sheet.get("background"):
            with st.expander("Предыстория", expanded=True): st.write(sheet["background"])

        st.write("---")
        cols = st.columns([1, 1, 2])
        with cols[0]:
            if st.button("← Назад"):
                data["sheet"] = None; wizard_go(6); st.rerun()
        with cols[1]:
            if st.button("🔄 Перегенерировать", use_container_width=True):
                data["sheet"] = None; st.rerun()
        with cols[2]:
            if st.button("✅ Подтвердить и начать игру", type="primary", use_container_width=True):
                path = cc.save_character(sheet)
                st.session_state.character = sheet
                st.session_state.character_path = path
                st.session_state.chat_history = []
                st.session_state.wizard_step = 0
                st.session_state.wizard_data = {}
                st.session_state.in_wizard = False
                st.rerun()


# ============================================================
# СТАРТОВЫЙ ЭКРАН
# ============================================================
def render_start_screen():
    st.title("⚔️ Warhammer 40,000 — RPG с ИИ-Мастером")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🆕 Новая игра")
        st.write("Создать нового персонажа через пошаговый мастер.")
        if st.button("Создать персонажа", type="primary", use_container_width=True):
            st.session_state.wizard_step = 0
            st.session_state.wizard_data = {}
            st.session_state.in_wizard = True
            st.rerun()
    with col2:
        st.subheader("📂 Продолжить")
        chars = cc.list_characters()
        if not chars:
            st.info("Нет сохранённых персонажей.")
        else:
            for c in chars:
                with st.container(border=True):
                    cols = st.columns([5, 1, 1])
                    with cols[0]:
                        st.markdown(f"**{c['name']}**")
                        st.caption(f"{c.get('faction','')} → {c.get('subfaction','')} → {c.get('archetype','')}")
                    with cols[1]:
                        if st.button("Играть", key=f"load_{c['name']}"):
                            sheet = cc.load_character(c["path"])
                            st.session_state.character = sheet
                            st.session_state.character_path = c["path"]
                            st.session_state.chat_history = []
                            st.session_state.in_wizard = False
                            st.rerun()
                    with cols[2]:
                        if st.button("🗑", key=f"del_{c['name']}"):
                            cc.delete_character(c["path"]); st.rerun()


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


def render_chat():
    kb = get_kb()
    giga = get_giga()
    master_prompt = get_master_prompt()

    with st.sidebar:
        st.header("👤 Персонаж")
        sheet = st.session_state.character
        st.write(f"**{sheet['name']}**")
        st.caption(f"{sheet.get('faction','')} → {sheet.get('subfaction','')} → {sheet.get('archetype','')}")
        with st.expander("Лист"):
            st.write(f"Раны: {sheet['wounds']['current']} / {sheet['wounds']['max']}")
            st.write(f"Судьба: {sheet['fate_points']['current']} / {sheet['fate_points']['max']}")
            st.write(f"Порча: {sheet.get('corruption', 0)}")
            if sheet.get("psy_rating", 0) > 0:
                st.write(f"Пси-Рейтинг: {sheet['psy_rating']}")
            st.write("---")
            for ch in cc.CHARACTERISTICS:
                st.write(f"{ch}: {sheet['characteristics'][ch]} (+{sheet['bonuses'][ch]})")
            st.write("---")
            for s in sheet.get("skills", []): st.write(f"• {s['name']}: {s.get('value','')}")
            st.write("---")
            for w in sheet.get("weapons", []): st.write(f"⚔ {w.get('name','')}")

        st.write("---")
        st.caption(f"📚 Чанков в базе: {kb.chunk_count}")

        with st.expander("🛠 Отладка"):
            st.caption(f"Сообщений: {len(st.session_state.get('chat_history', []))}")
            st.caption(f"Модель: {MODEL}")
            log_data = {
                "character": sheet,
                "chat_history": st.session_state.get("chat_history", []),
                "meta": {
                    "model": MODEL, "chunks_in_db": kb.chunk_count,
                    "vector_mode": kb.is_vector_mode,
                    "exported_at": datetime.now().isoformat(),
                },
            }
            st.download_button(
                label="📥 Скачать логи сессии",
                data=json.dumps(log_data, ensure_ascii=False, indent=2),
                file_name=f"session_{sheet.get('name','unnamed')}.json",
                mime="application/json", use_container_width=True,
            )
            if st.button("👁 Показать последний запрос", use_container_width=True):
                st.session_state.show_last_request = not st.session_state.get("show_last_request", False)
            if st.session_state.get("show_last_request"):
                st.code(st.session_state.get("last_request_to_giga", "—"), language="text")

        if st.button("Выйти в меню"):
            st.session_state.character = None
            st.session_state.chat_history = []
            st.session_state.show_last_request = False
            st.rerun()

    st.title("🎲 Игра")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    if not st.session_state.chat_history:
        intro_user = build_intro_message(st.session_state.character)
        with st.spinner("Мастер готовит вступление..."):
            try:
                resp = giga.chat(Chat(messages=[
                    Messages(role=MessagesRole.SYSTEM, content=master_prompt),
                    Messages(role=MessagesRole.USER, content=intro_user),
                ]))
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": resp.choices[0].message.content,
                    "rolls": [],
                })
            except Exception as e:
                st.error(f"Ошибка при генерации вступления: {e}")

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

    context = kb.format_context(user_input, top_k=TOP_K_KNOWLEDGE)
    enriched = f"{context}\n\n=== СООБЩЕНИЕ ИГРОКА ===\n{user_input}" if context else user_input

    giga_messages = [Messages(role=MessagesRole.SYSTEM, content=master_prompt)]
    last_idx = len(st.session_state.chat_history) - 1
    for i, m in enumerate(st.session_state.chat_history):
        role = MessagesRole.USER if m["role"] == "user" else MessagesRole.ASSISTANT
        content = m["content"]
        if i == last_idx and m["role"] == "user":
            content = enriched
        giga_messages.append(Messages(role=role, content=content))

    last_user_msg = next(
        (m.content for m in reversed(giga_messages) if m.role == MessagesRole.USER), ""
    )
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
                            function_call=msg.function_call,
                        ))
                        giga_messages.append(Messages(
                            role=MessagesRole.FUNCTION,
                            content=json.dumps(result, ensure_ascii=False),
                            name=fn_name,
                        ))
                        continue

                final_text = msg.content
                break

        text_rolls = []
        if final_text:
            final_text, text_rolls = parse_rolls_from_text(final_text)

        all_rolls = rolls_to_render + text_rolls

        for r in all_rolls:
            render_roll(r)

        if final_text:
            st.markdown(final_text)
            st.session_state.chat_history.append({
                "role": "assistant",
                "content": final_text,
                "rolls": all_rolls,
            })
        elif not all_rolls:
            st.markdown("_Не удалось получить ответ._")


# ============================================================
# ГЛАВНАЯ
# ============================================================
def main():
    # Один раз при старте проверяем / собираем векторную базу
    if "db_ready" not in st.session_state:
        ensure_db()
        st.session_state.db_ready = True

    if "character" not in st.session_state: st.session_state.character = None
    if "in_wizard" not in st.session_state: st.session_state.in_wizard = False
    if "show_last_request" not in st.session_state: st.session_state.show_last_request = False

    if st.session_state.character:
        render_chat()
    elif st.session_state.in_wizard:
        render_wizard()
    else:
        render_start_screen()


if __name__ == "__main__":
    main()