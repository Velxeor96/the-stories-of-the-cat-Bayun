# app.py
# Streamlit: визард + чат с Мастером.
# Темы: 12 палитр. Терминальный UI в стиле Rogue Trader.

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

LS_KEY = "wh40k_rpg_save_v2"
LS_THEME_KEY = "wh40k_theme"
SAVE_FORMAT = "wh40k_rpg_save"
SAVE_VERSION = 1

st.set_page_config(
    page_title="Warhammer 40K · RPG",
    page_icon="⚔️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# ТЕМЫ — 12 палитр
# ============================================================
THEMES = {
    "default": {
        "label": "🎨 Стандартная",
        "bg_deep": "#0f1116", "bg_mid": "#161a21", "bg_light": "#1e2229",
        "bg_card": "#1c2028", "bg_chat": "#262a33",
        "accent": "#d98a3a", "accent_dim": "#7a4a1f", "accent_bright": "#f5c88a",
        "text": "#f0f0f0", "text_dim": "#a8a8b0", "text_faint": "#6e7179",
        "heading": "#f5c88a", "link": "#d98a3a",
    },
    "grimdark": {
        "label": "⚔️ Grimdark",
        "bg_deep": "#0e0e10", "bg_mid": "#16161a", "bg_light": "#1e1e24",
        "bg_card": "#1c1c22", "bg_chat": "#26262c",
        "accent": "#c9a961", "accent_dim": "#8a7444", "accent_bright": "#e8d9b8",
        "text": "#ede4d3", "text_dim": "#b8ac92", "text_faint": "#8a8068",
        "heading": "#e8d9b8", "link": "#c9a961",
    },
    "imperium": {
        "label": "🛡️ Империум",
        "bg_deep": "#080c1a", "bg_mid": "#0d1220", "bg_light": "#141a2a",
        "bg_card": "#10162a", "bg_chat": "#161e30",
        "accent": "#c9a961", "accent_dim": "#8a7444", "accent_bright": "#f5d99a",
        "text": "#e8e4d0", "text_dim": "#a8a090", "text_faint": "#706858",
        "heading": "#f5d99a", "link": "#c9a961",
    },
    "sororitas": {
        "label": "🩸 Сороритас",
        "bg_deep": "#140808", "bg_mid": "#1c0d0d", "bg_light": "#261212",
        "bg_card": "#1d0f0f", "bg_chat": "#281616",
        "accent": "#e0b04a", "accent_dim": "#8a6828", "accent_bright": "#f8dc9a",
        "text": "#f0e0d0", "text_dim": "#bc9e88", "text_faint": "#7a6250",
        "heading": "#f8dc9a", "link": "#e0b04a",
    },
    "mechanicus": {
        "label": "⚙️ Механикус",
        "bg_deep": "#141210", "bg_mid": "#1c1916", "bg_light": "#26221c",
        "bg_card": "#1e1a16", "bg_chat": "#282320",
        "accent": "#ff8c1a", "accent_dim": "#a05610", "accent_bright": "#ffc070",
        "text": "#e8e0d0", "text_dim": "#b0a590", "text_faint": "#786d5a",
        "heading": "#ffc070", "link": "#ff8c1a",
    },
    "chaos": {
        "label": "🔥 Хаос",
        "bg_deep": "#140406", "bg_mid": "#1c0608", "bg_light": "#260a0c",
        "bg_card": "#1d0709", "bg_chat": "#260a0c",
        "accent": "#d4a04a", "accent_dim": "#7a5520", "accent_bright": "#f5d08a",
        "text": "#e8d4c0", "text_dim": "#b09a80", "text_faint": "#7a6a54",
        "heading": "#f5d08a", "link": "#d4a04a",
    },
    "eldar": {
        "label": "✨ Эльдары",
        "bg_deep": "#0a1418", "bg_mid": "#0f1c22", "bg_light": "#162830",
        "bg_card": "#122228", "bg_chat": "#1a2e38",
        "accent": "#4dd0e1", "accent_dim": "#2a8a9a", "accent_bright": "#a0f0ff",
        "text": "#d8e8ec", "text_dim": "#8fa8b0", "text_faint": "#5a6c74",
        "heading": "#a0f0ff", "link": "#4dd0e1",
    },
    "drukhari": {
        "label": "💜 Друкхари",
        "bg_deep": "#0f0a14", "bg_mid": "#150d1c", "bg_light": "#1e1428",
        "bg_card": "#1a1022", "bg_chat": "#221a2e",
        "accent": "#a8ff60", "accent_dim": "#6a9a38", "accent_bright": "#d0ffa0",
        "text": "#e0d8e8", "text_dim": "#a090b0", "text_faint": "#68587a",
        "heading": "#d0ffa0", "link": "#a8ff60",
    },
    "orks": {
        "label": "💪 Орки",
        "bg_deep": "#161a20", "bg_mid": "#1d222c", "bg_light": "#262d3a",
        "bg_card": "#222834", "bg_chat": "#262d3a",
        "accent": "#b5d334", "accent_dim": "#6b7d3a", "accent_bright": "#d4ec5a",
        "text": "#e8eef0", "text_dim": "#a8b0b8", "text_faint": "#6d7580",
        "heading": "#d4ec5a", "link": "#b5d334",
    },
    "tau": {
        "label": "🔵 Тау",
        "bg_deep": "#0a1018", "bg_mid": "#0f1822", "bg_light": "#16202e",
        "bg_card": "#111a26", "bg_chat": "#18222e",
        "accent": "#4fc3f7", "accent_dim": "#2a80a8", "accent_bright": "#a0dcf5",
        "text": "#e0e8f0", "text_dim": "#98a8b8", "text_faint": "#5a6878",
        "heading": "#a0dcf5", "link": "#4fc3f7",
    },
    "necron": {
        "label": "💀 Некроны",
        "bg_deep": "#0a0d0c", "bg_mid": "#0f1413", "bg_light": "#161b1a",
        "bg_card": "#131918", "bg_chat": "#1a2321",
        "accent": "#3dd9a4", "accent_dim": "#2a9b76", "accent_bright": "#7effd0",
        "text": "#d8e8e2", "text_dim": "#8fa89f", "text_faint": "#5a6f68",
        "heading": "#7effd0", "link": "#3dd9a4",
    },
    "tyranids": {
        "label": "🦠 Тираниды",
        "bg_deep": "#100810", "bg_mid": "#180d18", "bg_light": "#221422",
        "bg_card": "#1a101a", "bg_chat": "#241624",
        "accent": "#9c5cff", "accent_dim": "#5a3888", "accent_bright": "#c8a0ff",
        "text": "#e8d8f0", "text_dim": "#a898b8", "text_faint": "#685878",
        "heading": "#c8a0ff", "link": "#9c5cff",
    },
}

DEFAULT_THEME = "grimdark"


# ============================================================
# АВАТАРЫ ФРАКЦИЙ
# ============================================================
FACTION_AVATARS = {
    "империум": "🛡️",
    "космодесант": "🛡️",
    "инквизиц": "🛡️",
    "эльдар": "✨",
    "аэльдар": "✨",
    "друкхар": "💜",
    "орк": "💪",
    "некро": "💀",
    "тау": "🔵",
    "тиран": "🦠",
    "хаос": "🔥",
    "сорорит": "🩸",
    "механик": "⚙️",
}

DEFAULT_AVATAR_MASTER = "🎲"

# ============================================================
# РУССКИЕ ИМЕНА ХАРАКТЕРИСТИК (короткие для кнопок)
# Поддержка алиасов: Wil/WP, Fel/FEL/fel и т.д.
# ============================================================
# ============================================================
# РУССКИЕ ИМЕНА ХАРАКТЕРИСТИК
#   Короткие — для кнопок.  Длинные — для подсказок.
# ============================================================
CHAR_RU_SHORT = {
    "WS":  "Рук",     # рукопашный бой
    "BS":  "Стр",     # стрельба
    "S":   "Сил",     # сила
    "T":   "Вын",     # выносливость
    "AG":  "Лов",     # ловкость
    "INT": "Инт",     # интеллект
    "PER": "Восп",    # восприятие
    "WIL": "Воля",    # сила воли
    "WP":  "Воля",
    "FEL": "Общ",     # общительность
    "STR": "Сил",
    "TOU": "Вын",
    "TGH": "Вын",
    "AGI": "Лов",
    "PERC": "Восп",
    "WILL": "Воля",
    "SOC": "Общ",
}

CHAR_RU_LONG = {
    "WS": "Рукопашный бой",
    "BS": "Стрельба",
    "S": "Сила",
    "T": "Выносливость",
    "Ag": "Ловкость",
    "Int": "Интеллект",
    "Per": "Восприятие",
    "Wil": "Сила воли",
    "WP": "Сила воли",
    "Fel": "Общительность",
}


def char_ru(key: str) -> str:
    """Короткое русское имя для кнопки."""
    if not key:
        return ""
    k = str(key).strip().upper().rstrip(".")
    return CHAR_RU_SHORT.get(k, str(key))


def char_ru_long(key: str) -> str:
    """Длинное русское имя для tooltip."""
    if not key:
        return ""
    return CHAR_RU_LONG.get(str(key).strip(), str(key))




def get_faction_avatar(sheet) -> str:
    if not sheet:
        return DEFAULT_AVATAR_MASTER
    faction = str(sheet.get("faction", "")).lower()
    for key, emoji in FACTION_AVATARS.items():
        if key in faction:
            return emoji
    return DEFAULT_AVATAR_MASTER


# ============================================================
# BASE CSS
# ============================================================
BASE_CSS = """
<style>
/* =====================================================
   1. КОРНЕВОЙ РАЗМЕР
   ===================================================== */
html {
    font-size: clamp(15px, 0.5vw + 12px, 18px) !important;
}

/* =====================================================
   2. ШИРИНА КОНТЕНТА
   ===================================================== */
.block-container {
    padding-top: 0.6rem !important;
    padding-left: 1rem !important;
    padding-right: 1rem !important;
    padding-bottom: 1rem !important;
    max-width: min(1700px, 94vw) !important;
    margin-left: auto !important;
    margin-right: auto !important;
}

/* =====================================================
   3. Убираем полосы сверху
   ===================================================== */
header[data-testid="stHeader"], [data-testid="stHeader"] {
    background: transparent !important;
    min-height: 44px !important;
    height: auto !important;
}
[data-testid="stToolbar"] { top: 0.5rem !important; right: 0.8rem !important; }
[data-testid="stDecoration"] { display: none !important; }
[data-testid="stStatusWidget"] { display: none !important; }
[data-testid="stHeader"] > div:first-child > div:first-child {
    background: transparent !important;
}

/* === Кнопка разворота сайдбара — ВСЕГДА видима и кликабельна === */
[data-testid="stSidebarCollapsedControl"],
[data-testid="stSidebarCollapsedControl"] > div,
[data-testid="stSidebarCollapsedControl"] button,
[data-testid="stSidebarCollapseButton"],
[data-testid="stSidebarCollapseButton"] button,
[data-testid="collapsedControl"],
button[kind="header"] {
    visibility: visible !important;
    display: block !important;
    opacity: 1 !important;
    z-index: 999999 !important;
    position: fixed !important;
    top: 0.5rem !important;
    left: 0.5rem !important;
}
[data-testid="stSidebarCollapsedControl"] button,
[data-testid="stSidebarCollapseButton"] button,
button[kind="header"] {
    background: var(--bg-light, #1e1e24) !important;
    color: var(--accent-bright, #e8d9b8) !important;
    border: 1px solid var(--accent-dim, #8a7444) !important;
    border-radius: 4px !important;
    padding: 6px 10px !important;
    box-shadow: 0 0 12px color-mix(in srgb, var(--accent, #c9a961) 35%, transparent) !important;
}
[data-testid="stSidebarCollapsedControl"] button:hover,
[data-testid="stSidebarCollapseButton"] button:hover,
button[kind="header"]:hover {
    border-color: var(--accent, #c9a961) !important;
    box-shadow: 0 0 20px color-mix(in srgb, var(--accent, #c9a961) 60%, transparent) !important;
}

/* =====================================================
   4. Прозрачные панели снизу
   ===================================================== */
[data-testid="stBottom"],
[data-testid="stBottom"] > div,
[data-testid="stBottom"] > div > div,
[data-testid="stBottomBlockContainer"],
[data-testid="stBottomBlockContainer"] > div,
[data-testid="stAppViewContainer"] > .main,
section.main > div,
.stApp > section {
    background: transparent !important;
    background-color: transparent !important;
}
[data-testid="stMainBlockContainer"] {
    padding-bottom: 1rem !important;
    background: transparent !important;
}

/* =====================================================
   5. Сайдбар-табы
   ===================================================== */
[data-testid="stSidebar"] .stTabs [data-baseweb="tab-list"] {
    display: flex !important;
    flex-wrap: wrap !important;
    gap: 2px !important;
    overflow: visible !important;
    height: auto !important;
    background: transparent !important;
}
[data-testid="stSidebar"] .stTabs [data-baseweb="tab"] {
    font-size: clamp(0.72rem, 0.68rem + 0.1vw, 0.85rem) !important;
    padding: 4px 7px !important;
    white-space: nowrap !important;
    min-width: unset !important;
    width: auto !important;
    height: auto !important;
    line-height: 1.2 !important;
}
[data-testid="stSidebar"] .stTabs [data-baseweb="tab"] p {
    font-size: clamp(0.72rem, 0.68rem + 0.1vw, 0.85rem) !important;
    margin: 0 !important; padding: 0 !important; line-height: 1.2 !important;
}

/* =====================================================
   6. Safety
   ===================================================== */
[data-testid="stChatMessage"] p,
[data-testid="stChatMessage"] li,
.stMarkdown p,
.stMarkdown li {
    overflow-wrap: anywhere !important;
    word-break: break-word !important;
}
.stMarkdown pre, .stMarkdown code {
    overflow-x: auto !important;
    max-width: 100% !important;
}

/* =====================================================
   7. TERMINAL UI — панели, скобки, свечение
   ===================================================== */
[data-testid="stVerticalBlockBorderWrapper"] {
    position: relative;
    background: linear-gradient(135deg,
        color-mix(in srgb, var(--bg-light, #1e1e24) 92%, var(--accent, #c9a961) 8%),
        var(--bg-card, #1c1c22)) !important;
    border: 1px solid var(--accent-dim, #8a7444) !important;
    border-radius: 0 !important;
    padding: 22px 26px !important;
    margin-bottom: 16px !important;
    clip-path: polygon(
        18px 0, 100% 0,
        100% calc(100% - 18px), calc(100% - 18px) 100%,
        0 100%, 0 18px
    );
    transition: all 0.22s ease;
    box-shadow: 0 0 0 1px color-mix(in srgb, var(--accent, #c9a961) 10%, transparent),
                0 4px 18px rgba(0,0,0,0.45);
}
[data-testid="stVerticalBlockBorderWrapper"]:hover {
    border-color: var(--accent, #c9a961) !important;
    box-shadow: 0 0 0 1px var(--accent, #c9a961),
                0 0 22px color-mix(in srgb, var(--accent, #c9a961) 35%, transparent),
                0 6px 24px rgba(0,0,0,0.55);
}
[data-testid="stVerticalBlockBorderWrapper"]::before {
    content: '';
    position: absolute;
    top: 8px; left: 8px;
    width: 22px; height: 22px;
    border-top: 2px solid var(--accent, #c9a961);
    border-left: 2px solid var(--accent, #c9a961);
    pointer-events: none;
    opacity: 0.85;
}
[data-testid="stVerticalBlockBorderWrapper"]::after {
    content: '';
    position: absolute;
    bottom: 8px; right: 8px;
    width: 22px; height: 22px;
    border-bottom: 2px solid var(--accent, #c9a961);
    border-right: 2px solid var(--accent, #c9a961);
    pointer-events: none;
    opacity: 0.85;
}

/* =====================================================
   8. ТЕРМИНАЛ — статус-бар, hero, заголовки секций
   ===================================================== */
.terminal-status {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 8px 16px;
    margin-bottom: 18px;
    font-family: 'Consolas', 'Menlo', 'Monaco', 'Courier New', monospace;
    font-size: clamp(0.68rem, 0.66rem + 0.1vw, 0.78rem);
    color: var(--accent-dim, #8a7444);
    letter-spacing: 0.22em;
    text-transform: uppercase;
    border-top: 1px solid var(--accent-dim, #8a7444);
    border-bottom: 1px solid var(--accent-dim, #8a7444);
    background: linear-gradient(90deg,
        transparent 0%,
        color-mix(in srgb, var(--accent, #c9a961) 5%, transparent) 50%,
        transparent 100%);
}
.terminal-status span { white-space: nowrap; }

.hero-panel {
    position: relative;
    padding: 28px 36px 26px 36px;
    margin-bottom: 16px;
    background: linear-gradient(135deg,
        color-mix(in srgb, var(--bg-light, #1e1e24) 88%, var(--accent, #c9a961) 12%),
        var(--bg-card, #1c1c22));
    border: 1px solid var(--accent-dim, #8a7444);
    clip-path: polygon(
        26px 0, 100% 0,
        100% calc(100% - 26px), calc(100% - 26px) 100%,
        0 100%, 0 26px
    );
    box-shadow: 0 0 30px color-mix(in srgb, var(--accent, #c9a961) 12%, transparent),
                0 4px 24px rgba(0,0,0,0.5),
                inset 0 0 60px color-mix(in srgb, var(--accent, #c9a961) 4%, transparent);
}
.hero-panel .hero-title {
    font-family: 'Consolas', 'Menlo', 'Monaco', 'Courier New', monospace;
    font-size: clamp(1.5rem, 1.15rem + 1.6vw, 2.6rem);
    font-weight: 700;
    letter-spacing: 0.06em;
    color: var(--accent-bright, #e8d9b8);
    margin: 0 0 8px 0;
    line-height: 1.15;
    text-shadow: 0 0 20px color-mix(in srgb, var(--accent, #c9a961) 35%, transparent);
}
.hero-panel .hero-sub {
    font-family: 'Consolas', 'Menlo', 'Monaco', 'Courier New', monospace;
    font-size: clamp(0.78rem, 0.74rem + 0.2vw, 0.95rem);
    color: var(--ink-dim, #b8ac92);
    letter-spacing: 0.35em;
    text-transform: uppercase;
    display: flex;
    align-items: center;
    gap: 14px;
}
.hero-panel .hero-sub .line {
    flex: 1;
    height: 1px;
    background: linear-gradient(90deg, transparent, var(--accent-dim, #8a7444), transparent);
    max-width: 200px;
}

.section-header {
    display: flex;
    align-items: center;
    gap: 14px;
    margin: 22px 0 12px 0;
    font-family: 'Consolas', 'Menlo', 'Monaco', 'Courier New', monospace;
}
.section-header .num {
    display: inline-block;
    padding: 3px 10px;
    border: 1px solid var(--accent, #c9a961);
    color: var(--accent, #c9a961);
    font-weight: 700;
    font-size: clamp(0.78rem, 0.74rem + 0.15vw, 0.92rem);
    letter-spacing: 0.15em;
    background: color-mix(in srgb, var(--accent, #c9a961) 8%, transparent);
    box-shadow: 0 0 10px color-mix(in srgb, var(--accent, #c9a961) 20%, transparent);
}
.section-header .title {
    color: var(--heading, #e8d9b8);
    font-weight: 700;
    font-size: clamp(0.95rem, 0.88rem + 0.3vw, 1.15rem);
    letter-spacing: 0.22em;
    text-transform: uppercase;
    white-space: nowrap;
}
.section-header .line {
    flex: 1;
    height: 1px;
    background: linear-gradient(90deg, var(--accent-dim, #8a7444), transparent 80%);
}
.section-header .meta {
    color: var(--accent-dim, #8a7444);
    font-size: clamp(0.72rem, 0.7rem + 0.1vw, 0.85rem);
    letter-spacing: 0.2em;
    text-transform: uppercase;
    white-space: nowrap;
}

/* =====================================================
   9. БРОСКИ КУБИКОВ — карточки
   ===================================================== */
.roll-card {
    position: relative;
    margin: 12px 0 16px 0;
    padding: 16px 24px 18px 24px;
    background: var(--bg-card, #1c1c22);
    border: 1px solid var(--accent-dim, #8a7444);
    clip-path: polygon(
        14px 0, 100% 0,
        100% calc(100% - 14px), calc(100% - 14px) 100%,
        0 100%, 0 14px
    );
    font-family: 'Consolas', 'Menlo', 'Monaco', 'Courier New', monospace;
    color: var(--accent, #c9a961);
    transition: box-shadow 0.25s ease;
}
.roll-card::before {
    content: '';
    position: absolute;
    top: 6px; left: 6px;
    width: 16px; height: 16px;
    border-top: 2px solid currentColor;
    border-left: 2px solid currentColor;
    opacity: 0.75;
    pointer-events: none;
}
.roll-card::after {
    content: '';
    position: absolute;
    bottom: 6px; right: 6px;
    width: 16px; height: 16px;
    border-bottom: 2px solid currentColor;
    border-right: 2px solid currentColor;
    opacity: 0.75;
    pointer-events: none;
}

.roll-card--success {
    color: #6ee787;
    border-color: rgba(110, 231, 135, 0.55);
    background:
        linear-gradient(135deg,
            rgba(110, 231, 135, 0.14),
            rgba(110, 231, 135, 0.04)),
        var(--bg-card, #1c1c22);
    box-shadow: 0 0 22px rgba(110, 231, 135, 0.20),
                inset 0 0 40px rgba(110, 231, 135, 0.05);
}
.roll-card--fail {
    color: #ff7a7a;
    border-color: rgba(255, 122, 122, 0.55);
    background:
        linear-gradient(135deg,
            rgba(255, 122, 122, 0.14),
            rgba(255, 122, 122, 0.04)),
        var(--bg-card, #1c1c22);
    box-shadow: 0 0 22px rgba(255, 122, 122, 0.20),
                inset 0 0 40px rgba(255, 122, 122, 0.05);
}
.roll-card--info {
    color: var(--accent, #c9a961);
    border-color: var(--accent-dim, #8a7444);
    background:
        linear-gradient(135deg,
            color-mix(in srgb, var(--accent, #c9a961) 10%, transparent),
            color-mix(in srgb, var(--accent, #c9a961) 2%, transparent)),
        var(--bg-card, #1c1c22);
    box-shadow: 0 0 18px color-mix(in srgb, var(--accent, #c9a961) 18%, transparent);
}

.roll-header {
    display: flex;
    align-items: center;
    gap: 12px;
    font-size: 0.72rem;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: currentColor;
    padding-bottom: 8px;
    border-bottom: 1px solid color-mix(in srgb, currentColor 30%, transparent);
    margin-bottom: 14px;
}
.roll-header .roll-label { opacity: 0.75; }
.roll-header .roll-expr {
    font-weight: 700;
    color: currentColor;
    text-shadow: 0 0 10px currentColor;
    opacity: 0.95;
}
.roll-header .roll-reason {
    font-style: italic;
    opacity: 0.7;
    margin-left: auto;
    text-transform: none;
    letter-spacing: 0.05em;
    font-size: 0.82rem;
}
.roll-body {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 30px;
    padding: 4px 0 12px 0;
}
.roll-value { text-align: center; }
.roll-value-num {
    font-size: clamp(2.6rem, 2rem + 2.2vw, 4.2rem);
    font-weight: 700;
    line-height: 1;
    color: currentColor;
    text-shadow: 0 0 26px currentColor;
    letter-spacing: -0.02em;
}
.roll-value-label {
    font-size: 0.68rem;
    letter-spacing: 0.3em;
    opacity: 0.7;
    margin-top: 6px;
    text-transform: uppercase;
}
.roll-mod {
    font-size: 1.6rem;
    font-weight: 700;
    color: currentColor;
    opacity: 0.9;
    padding: 4px 14px;
    border-left: 1px solid color-mix(in srgb, currentColor 50%, transparent);
    border-right: 1px solid color-mix(in srgb, currentColor 50%, transparent);
    text-shadow: 0 0 12px currentColor;
    letter-spacing: 0.04em;
}
.roll-meta {
    display: flex;
    justify-content: center;
    gap: 40px;
    padding: 10px 0 6px 0;
    border-top: 1px solid color-mix(in srgb, currentColor 22%, transparent);
    margin-top: 4px;
}
.roll-meta-item {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 3px;
}
.roll-meta-item .label {
    font-size: 0.66rem;
    letter-spacing: 0.25em;
    opacity: 0.65;
    text-transform: uppercase;
}
.roll-meta-item .value {
    font-size: 1.35rem;
    font-weight: 700;
    color: currentColor;
    text-shadow: 0 0 12px currentColor;
}
.roll-status {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 12px;
    margin-top: 10px;
    padding: 8px 0 2px 0;
    font-size: 0.88rem;
    font-weight: 700;
    letter-spacing: 0.35em;
    text-transform: uppercase;
    color: currentColor;
}
.roll-status-icon { font-size: 1.15rem; }
.roll-status-text { text-shadow: 0 0 16px currentColor; }

/* =====================================================
   9-B. САЙДБАР — ЛИСТ ПЕРСОНАЖА
   ===================================================== */
.char-sheet-header {
    display: flex;
    align-items: center;
    gap: 12px;
    padding-bottom: 12px;
    margin-bottom: 10px;
    border-bottom: 1px solid var(--accent-dim, #8a7444);
}
.char-avatar {
    width: 52px; height: 52px;
    border-radius: 50%;
    border: 2px solid var(--accent, #c9a961);
    background: color-mix(in srgb, var(--accent-dim, #8a7444) 30%, transparent);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 26px;
    box-shadow: 0 0 14px color-mix(in srgb, var(--accent, #c9a961) 35%, transparent),
                inset 0 0 10px color-mix(in srgb, var(--accent, #c9a961) 15%, transparent);
    flex-shrink: 0;
}
.char-sheet-name {
    font-family: 'Consolas', 'Menlo', monospace;
    font-size: 1rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    color: var(--accent-bright, #e8d9b8);
    margin: 0 0 3px 0;
    line-height: 1.1;
}
.char-sheet-sub {
    font-family: 'Consolas', 'Menlo', monospace;
    font-size: 0.66rem;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--ink-dim, #b8ac92);
    line-height: 1.3;
}

.stat-bar { margin: 8px 0; }
.stat-bar-head {
    display: flex;
    justify-content: space-between;
    font-family: 'Consolas', 'Menlo', monospace;
    font-size: 0.72rem;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    margin-bottom: 4px;
}
.stat-bar-label { color: var(--ink-dim, #b8ac92); }
.stat-bar-value { color: var(--accent-bright, #e8d9b8); font-weight: 700; }
.stat-bar-track {
    height: 8px;
    border-radius: 2px;
    background: color-mix(in srgb, var(--accent-dim, #8a7444) 18%, transparent);
    overflow: hidden;
    border: 1px solid var(--accent-dim, #8a7444);
}
.stat-bar-fill {
    height: 100%;
    transition: width 0.4s ease;
}
.stat-bar--wounds .stat-bar-fill {
    background: linear-gradient(90deg, #6b1a1a, #d33);
    box-shadow: 0 0 8px rgba(220, 50, 50, 0.6);
}
.stat-bar--fate .stat-bar-fill {
    background: linear-gradient(90deg, var(--accent-dim, #8a7444), var(--accent, #c9a961));
    box-shadow: 0 0 8px color-mix(in srgb, var(--accent, #c9a961) 55%, transparent);
}
.stat-bar--corruption .stat-bar-fill {
    background: linear-gradient(90deg, #4a1a6b, #9c5cff);
    box-shadow: 0 0 8px rgba(156, 92, 255, 0.5);
}
.stat-bar--insanity .stat-bar-fill {
    background: linear-gradient(90deg, #6b4a1a, #d4913a);
    box-shadow: 0 0 8px rgba(212, 145, 58, 0.5);
}

.meta-grid {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 6px;
    margin: 12px 0;
}
.meta-tile {
    background: var(--bg-card, #1c1c22);
    border: 1px solid var(--accent-dim, #8a7444);
    border-radius: 4px;
    padding: 10px 6px 9px 6px;
    text-align: center;
    font-family: 'Consolas', 'Menlo', monospace;
}
.meta-tile .icon { font-size: 1rem; opacity: 0.9; }
.meta-tile .label {
    font-size: 0.66rem;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--accent, #c9a961) !important;
    margin: 4px 0 5px;
}
.meta-tile .value {
    font-size: 1.15rem;
    font-weight: 700;
    color: var(--accent-bright, #e8d9b8);
}

.attr-grid {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 7px;
    margin: 10px 0 14px;
}
.attr-tile {
    background: color-mix(in srgb, var(--bg-card, #1c1c22) 88%, transparent);
    border: 1px solid color-mix(in srgb, var(--accent-dim, #8a7444) 80%, transparent);
    border-radius: 4px;
    padding: 10px 6px 9px 6px;
    text-align: center;
    font-family: 'Consolas', 'Menlo', monospace;
    transition: all 0.18s ease;
}
.attr-tile:hover {
    border-color: var(--accent, #c9a961);
    background: color-mix(in srgb, var(--bg-card, #1c1c22) 78%, var(--accent, #c9a961) 8%);
    box-shadow: 0 0 12px color-mix(in srgb, var(--accent, #c9a961) 25%, transparent);
}
.attr-tile .attr-key {
    font-size: 0.72rem;
    letter-spacing: 0.14em;
    color: var(--accent, #c9a961) !important;
    text-transform: uppercase;
    opacity: 1 !important;
    font-weight: 700;
}
.attr-tile .attr-val {
    font-size: 1.4rem;
    font-weight: 700;
    color: var(--ink, #ede4d3);
    margin: 5px 0 3px;
    line-height: 1;
    text-shadow: 0 0 10px color-mix(in srgb, var(--ink, #ede4d3) 20%, transparent);
}
.attr-tile .attr-bon {
    font-size: 0.85rem;
    color: var(--accent-bright, #e8d9b8);
    opacity: 0.95;
    font-weight: 600;
}


/* === Усиленная читаемость сайдбара (patch5) === */
[data-testid="stSidebar"] .stButton > button {
    color: var(--accent-bright, #e8d9b8) !important;
    font-weight: 600 !important;
    text-shadow: 0 0 6px color-mix(in srgb, var(--accent, #c9a961) 40%, transparent);
    letter-spacing: 0.04em !important;
}

[data-testid="stSidebar"] [data-testid="stExpander"] summary,
[data-testid="stSidebar"] [data-testid="stExpander"] summary *,
[data-testid="stSidebar"] [data-testid="stExpander"] summary p {
    color: var(--accent-bright, #e8d9b8) !important;
    font-weight: 700 !important;
    font-size: 0.82rem !important;
    letter-spacing: 0.1em !important;
    text-shadow: 0 0 8px color-mix(in srgb, var(--accent, #c9a961) 45%, transparent);
}

[data-testid="stSidebar"] [data-testid="stExpander"] summary svg {
    fill: var(--accent, #c9a961) !important;
}

/* === Полоса локации над чатом (patch6) === */
.location-bar {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 10px;
    padding: 10px 18px;
    margin: 0 0 18px 0;
    background: linear-gradient(90deg,
        color-mix(in srgb, var(--accent, #c9a961) 14%, transparent),
        transparent 65%);
    border-left: 3px solid var(--accent, #c9a961);
    border-top: 1px solid color-mix(in srgb, var(--accent, #c9a961) 22%, transparent);
    border-bottom: 1px solid color-mix(in srgb, var(--accent, #c9a961) 22%, transparent);
    font-family: 'Consolas', 'Menlo', monospace;
    font-size: clamp(0.78rem, 0.74rem + 0.2vw, 0.92rem);
    color: var(--accent-bright, #e8d9b8);
    letter-spacing: 0.14em;
    text-transform: uppercase;
    box-shadow: 0 0 18px color-mix(in srgb, var(--accent, #c9a961) 15%, transparent);
}
.location-bar .lbl {
    color: var(--accent, #c9a961);
    font-weight: 700;
    letter-spacing: 0.22em;
}
.location-bar .val {
    color: var(--accent-bright, #e8d9b8);
    font-weight: 600;
    letter-spacing: 0.06em;
    text-transform: none;
    text-shadow: 0 0 8px color-mix(in srgb, var(--accent, #c9a961) 35%, transparent);
}
.location-bar .dot {
    color: var(--accent-dim, #8a7444);
    opacity: 0.7;
    font-weight: 700;
}

/* === Пульс HP при низких ранах (patch6) === */
@keyframes pulse-wounds {
    0%, 100% {
        box-shadow: 0 0 8px rgba(220, 50, 50, 0.6);
        filter: brightness(1);
    }
    50% {
        box-shadow: 0 0 20px rgba(255, 60, 60, 1),
                    0 0 32px rgba(255, 60, 60, 0.5);
        filter: brightness(1.25);
    }
}
.stat-bar--wounds.stat-bar--low .stat-bar-fill {
    animation: pulse-wounds 1.5s ease-in-out infinite;
}
.stat-bar--wounds.stat-bar--low .stat-bar-value {
    color: #ff7a7a !important;
    text-shadow: 0 0 10px rgba(255, 122, 122, 0.8);
}

/* === Анимация карточки броска (patch9) === */
@keyframes roll-in {
    0% {
        opacity: 0;
        transform: translateY(14px) scale(0.94);
        filter: blur(4px);
    }
    60% { opacity: 1; filter: blur(0); }
    100% { opacity: 1; transform: translateY(0) scale(1); }
}
.roll-card {
    animation: roll-in 0.5s cubic-bezier(0.2, 0.8, 0.3, 1) both;
}

/* === XP-бар === */
.stat-bar--xp .stat-bar-fill {
    background: linear-gradient(90deg,
        color-mix(in srgb, var(--accent, #c9a961) 60%, #4fc3f7),
        var(--accent-bright, #e8d9b8));
    box-shadow: 0 0 10px color-mix(in srgb, var(--accent, #c9a961) 55%, transparent);
}

/* === Карточка полученного предмета (patch9) === */
@keyframes loot-in {
    0% {
        opacity: 0;
        transform: translateX(-30px) rotate(-2deg) scale(0.9);
    }
    60% { transform: translateX(4px) rotate(0.5deg) scale(1.02); }
    100% { opacity: 1; transform: translateX(0) rotate(0) scale(1); }
}
.loot-card {
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 14px 20px;
    margin: 10px 0 14px 0;
    background: linear-gradient(135deg,
        color-mix(in srgb, var(--accent, #c9a961) 22%, transparent),
        color-mix(in srgb, var(--accent, #c9a961) 6%, transparent));
    border: 1px solid var(--accent, #c9a961);
    border-left: 4px solid var(--accent-bright, #e8d9b8);
    clip-path: polygon(
        12px 0, 100% 0,
        100% calc(100% - 12px), calc(100% - 12px) 100%,
        0 100%, 0 12px
    );
    box-shadow: 0 0 22px color-mix(in srgb, var(--accent, #c9a961) 35%, transparent),
                inset 0 0 30px color-mix(in srgb, var(--accent, #c9a961) 8%, transparent);
    font-family: 'Consolas', 'Menlo', monospace;
    animation: loot-in 0.55s cubic-bezier(0.2, 0.9, 0.3, 1) both;
    position: relative;
}
.loot-card::after {
    content: '';
    position: absolute;
    top: 6px; right: 6px;
    width: 14px; height: 14px;
    border-top: 2px solid var(--accent-bright, #e8d9b8);
    border-right: 2px solid var(--accent-bright, #e8d9b8);
    opacity: 0.7;
}
.loot-icon {
    font-size: 2rem;
    line-height: 1;
    filter: drop-shadow(0 0 8px color-mix(in srgb, var(--accent, #c9a961) 60%, transparent));
    flex-shrink: 0;
}
.loot-info {
    display: flex;
    flex-direction: column;
    gap: 3px;
    min-width: 0;
}
.loot-label {
    font-size: 0.7rem;
    letter-spacing: 0.28em;
    color: var(--accent, #c9a961);
    text-transform: uppercase;
    font-weight: 700;
}
.loot-name {
    font-size: 1.05rem;
    letter-spacing: 0.05em;
    color: var(--accent-bright, #e8d9b8);
    font-weight: 700;
    text-shadow: 0 0 12px color-mix(in srgb, var(--accent, #c9a961) 45%, transparent);
    word-break: break-word;
}
.sidebar-divider {
    height: 1px;
    background: linear-gradient(90deg, transparent, var(--accent-dim, #8a7444), transparent);
    margin: 14px 0;
}
.sidebar-section-title {
    font-family: 'Consolas', 'Menlo', monospace;
    font-size: 0.74rem;
    letter-spacing: 0.16em;
    color: var(--accent, #c9a961) !important;
    text-transform: uppercase;
    margin: 12px 0 8px 0;
    padding-bottom: 5px;
    border-bottom: 1px solid color-mix(in srgb, var(--accent, #c9a961) 35%, transparent);
    font-weight: 700;
}
.pending-check-box {
    font-family: 'Consolas', 'Menlo', monospace;
    font-size: 0.78rem;
    letter-spacing: 0.06em;
    color: var(--accent-bright, #e8d9b8) !important;
    padding: 9px 12px;
    border: 1px solid var(--accent, #c9a961);
    border-radius: 4px;
    margin: 10px 0 8px 0;
    background: color-mix(in srgb, var(--accent, #c9a961) 12%, transparent);
    font-weight: 700;
    box-shadow: 0 0 12px color-mix(in srgb, var(--accent, #c9a961) 25%, transparent);
}


/* =====================================================
   10. Мобильный
   ===================================================== */
@media (max-width: 768px) {
    html { font-size: 15px !important; }
    .block-container {
        padding-left: 0.5rem !important;
        padding-right: 0.5rem !important;
    }
    h1 { font-size: 1.6rem !important; }
    h2 { font-size: 1.3rem !important; }
    [data-testid="stChatMessage"] { padding: 12px 14px !important; }
    [data-testid="stChatMessage"] p,
    [data-testid="stChatMessage"] li { font-size: 1rem !important; }
    [data-testid="stMetricValue"] > div,
    [data-testid="stMetricValue"] > div > div { font-size: 1.3rem !important; }
    [data-testid="stSidebar"] .stTabs [data-baseweb="tab"] {
        font-size: 0.7rem !important;
        padding: 3px 5px !important;
    }
    .hero-panel { padding: 18px 20px !important; }
    .hero-panel .hero-sub { letter-spacing: 0.2em; }
    .section-header .title { letter-spacing: 0.15em; font-size: 0.9rem; }
    .section-header .meta { display: none; }
    .chat-name { font-size: 0.65rem; letter-spacing: 0.15em; }
    .roll-card { padding: 12px 16px 14px 16px; }
    .roll-value-num { font-size: 2.4rem; }
    .roll-meta { gap: 20px; }
    .roll-meta-item .value { font-size: 1.1rem; }
    .roll-body { gap: 16px; }
    .roll-mod { font-size: 1.3rem; padding: 3px 10px; }
    .roll-status { font-size: 0.78rem; letter-spacing: 0.25em; }
    .attr-tile .attr-val { font-size: 0.9rem; }
    .meta-tile .value { font-size: 0.9rem; }
}

/* =====================================================
   11. Ультравайд
   ===================================================== */
@media (min-width: 2000px) {
    html { font-size: 19px !important; }
    h1 { font-size: 2.4rem !important; }
    h2 { font-size: 1.8rem !important; }
    h3 { font-size: 1.4rem !important; }
    .block-container { max-width: 1800px !important; }
}

/* === ПУЛЬС HP — ФИНАЛЬНЫЙ OVERRIDE (patch8) === */
@keyframes pulse-wounds {
    0%, 100% {
        background: linear-gradient(90deg, #6b1a1a, #d33);
        box-shadow: 0 0 8px rgba(220, 50, 50, 0.7);
        filter: brightness(1);
    }
    50% {
        background: linear-gradient(90deg, #ff1818, #ff6868);
        box-shadow: 0 0 24px rgba(255, 60, 60, 1),
                    0 0 44px rgba(255, 60, 60, 0.6);
        filter: brightness(1.3);
    }
}
.stat-bar--wounds.stat-bar--low .stat-bar-fill {
    animation: pulse-wounds 1.4s ease-in-out infinite !important;
    background: linear-gradient(90deg, #ff1818, #ff6868) !important;
    box-shadow: 0 0 18px rgba(255, 60, 60, 0.9) !important;
}
.stat-bar--wounds.stat-bar--low .stat-bar-value {
    color: #ff7a7a !important;
    text-shadow: 0 0 12px rgba(255, 122, 122, 0.95) !important;
    font-weight: 700 !important;
}
.stat-bar--wounds.stat-bar--low .stat-bar-label {
    color: #ff9a9a !important;
}
</style>
"""


# ============================================================
# THEME CSS
# ============================================================
THEME_CSS_TEMPLATE = """
<style>
:root {
    --bg-deep:   __BG_DEEP__;
    --bg-mid:    __BG_MID__;
    --bg-light:  __BG_LIGHT__;
    --bg-card:   __BG_CARD__;
    --bg-chat:   __BG_CHAT__;
    --accent:        __ACCENT__;
    --accent-dim:    __ACCENT_DIM__;
    --accent-bright: __ACCENT_BRIGHT__;
    --ink:       __TEXT__;
    --ink-dim:   __TEXT_DIM__;
    --ink-faint: __TEXT_FAINT__;
    --heading:   __HEADING__;
    --link:      __LINK__;
}

.stApp {
    background-color: var(--bg-deep) !important;
    color: var(--ink) !important;
    background-image:
        linear-gradient(color-mix(in srgb, var(--accent) 4%, transparent) 1px, transparent 1px),
        linear-gradient(90deg, color-mix(in srgb, var(--accent) 4%, transparent) 1px, transparent 1px) !important;
    background-size: 44px 44px !important;
    background-position: 0 0 !important;
}

[data-testid="stBottom"],
[data-testid="stBottomBlockContainer"] {
    background: var(--bg-deep) !important;
    border-top: 1px solid var(--accent-dim) !important;
}

h1, h2, h3, h4, h5, h6 {
    color: var(--heading) !important;
    font-weight: 700;
}
h1 {
    font-size: clamp(1.8rem, 1.5rem + 1vw, 2.6rem) !important;
    border-bottom: 1px solid var(--accent-dim);
    padding-bottom: .4rem;
}
h2 {
    font-size: clamp(1.35rem, 1.1rem + 0.6vw, 1.9rem) !important;
    color: var(--accent) !important;
}
h3 {
    font-size: clamp(1.15rem, 1rem + 0.4vw, 1.5rem) !important;
    color: var(--accent) !important;
}
h4, h5, h6 {
    font-size: clamp(1rem, 0.9rem + 0.2vw, 1.25rem) !important;
    color: var(--accent-dim) !important;
}

.stMarkdown p, .stMarkdown li {
    font-size: 1.05rem;
    line-height: 1.65;
    color: var(--ink) !important;
}
.stMarkdown strong, .stMarkdown b { color: var(--accent-bright) !important; font-weight: 700; }
.stMarkdown em, .stMarkdown i { color: var(--ink-dim) !important; font-style: italic; }
.stMarkdown a { color: var(--link) !important; text-decoration: underline; }
.stMarkdown a:hover { color: var(--accent-bright) !important; }
.stMarkdown code {
    background: color-mix(in srgb, var(--bg-deep) 82%, var(--accent) 18%);
    color: var(--accent-bright) !important;
    padding: 2px 7px;
    border-radius: 3px;
    border: 1px solid color-mix(in srgb, var(--accent) 35%, transparent);
    font-family: 'Consolas', 'Menlo', monospace;
    font-size: 0.92em;
}

[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] *,
.stCaption, .stCaption * {
    color: var(--ink-dim) !important;
    font-size: clamp(0.85rem, 0.8rem + 0.1vw, 1rem) !important;
}

[data-testid="stMetric"] {
    background: var(--bg-card) !important;
    border: 1px solid var(--accent-dim) !important;
    border-radius: 6px;
    padding: 10px 14px !important;
    min-width: 0 !important;
    overflow: visible !important;
}
[data-testid="stMetricLabel"] { overflow: visible !important; }
[data-testid="stMetricLabel"] > div,
[data-testid="stMetricLabel"] > div > div {
    color: var(--accent) !important;
    font-size: clamp(0.72rem, 0.7rem + 0.1vw, 0.85rem) !important;
    text-transform: uppercase;
    font-weight: 600 !important;
    letter-spacing: 0.04em;
    white-space: nowrap !important;
    overflow: visible !important;
    text-overflow: clip !important;
    line-height: 1.3 !important;
    display: inline-block !important;
}
[data-testid="stMetricValue"] > div,
[data-testid="stMetricValue"] > div > div {
    color: var(--accent-bright) !important;
    font-weight: 700 !important;
    font-size: clamp(1.3rem, 1.1rem + 0.6vw, 1.9rem) !important;
    line-height: 1.2 !important;
}
[data-testid="stMetricDelta"] { color: var(--ink-dim) !important; }

[data-testid="stSidebar"] {
    background: var(--bg-mid) !important;
    border-right: 1px solid var(--accent-dim);
}
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 { color: var(--accent) !important; }
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] small,
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] > * { color: var(--ink) !important; }
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] * { color: var(--ink-dim) !important; }

.stButton > button, [data-testid="stBaseButton-secondary"], [data-testid="stBaseButton-primary"] {
    letter-spacing: 0.05em;
    font-weight: 600 !important;
    background: var(--bg-light) !important;
    color: var(--accent-bright) !important;
    border: 1px solid var(--accent-dim) !important;
    border-radius: 3px;
    transition: all 0.2s ease;
    font-size: clamp(0.9rem, 0.85rem + 0.1vw, 1.05rem) !important;
    white-space: nowrap !important;
    text-transform: uppercase;
}
.stButton > button:hover, [data-testid="stBaseButton-secondary"]:hover {
    border-color: var(--accent) !important;
    color: var(--accent-bright) !important;
    box-shadow: 0 0 12px color-mix(in srgb, var(--accent) 45%, transparent),
                0 0 26px color-mix(in srgb, var(--accent) 18%, transparent),
                inset 0 0 8px color-mix(in srgb, var(--accent) 8%, transparent);
}
[data-testid="stBaseButton-primary"] {
    background: linear-gradient(180deg,
        color-mix(in srgb, var(--accent-dim) 100%, transparent),
        var(--accent-dim)) !important;
    border-color: var(--accent) !important;
    color: #ffffff !important;
}
[data-testid="stBaseButton-primary"]:hover {
    background: var(--accent) !important;
    color: #ffffff !important;
    box-shadow: 0 0 16px color-mix(in srgb, var(--accent) 60%, transparent),
                0 0 32px color-mix(in srgb, var(--accent) 25%, transparent);
}
[data-testid="stDownloadButton"] > button {
    background: var(--bg-light) !important;
    color: var(--accent-bright) !important;
    border: 1px solid var(--accent-dim) !important;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    font-size: clamp(0.9rem, 0.85rem + 0.1vw, 1.05rem) !important;
}

.stTabs [data-baseweb="tab-list"] { border-bottom: 1px solid var(--accent-dim); gap: 4px; }
.stTabs [data-baseweb="tab"] {
    color: var(--ink-dim) !important;
    background: transparent !important;
    padding: 8px 12px;
    font-weight: 600;
    font-size: clamp(0.88rem, 0.85rem + 0.1vw, 1rem) !important;
}
.stTabs [data-baseweb="tab"]:hover { color: var(--accent-bright) !important; }
.stTabs [aria-selected="true"] {
    color: var(--accent-bright) !important;
    border-bottom: 2px solid var(--accent) !important;
}
.stTabs [data-baseweb="tab-highlight"] { background-color: var(--accent) !important; }

[data-testid="stExpander"] {
    border: 1px solid var(--accent-dim) !important;
    border-radius: 4px;
    background: var(--bg-card) !important;
}
[data-testid="stExpander"] details > summary,
[data-testid="stExpander"] details > summary *,
[data-testid="stExpander"] details > summary p,
[data-testid="stExpander"] details > summary span,
[data-testid="stExpander"] details > summary div,
[data-testid="stExpander"] summary,
[data-testid="stExpander"] summary *,
[data-testid="stExpander"] summary p,
[data-testid="stExpander"] summary span,
[data-testid="stExpander"] summary div,
[data-testid="stExpander"] [data-testid="stExpanderHeader"],
[data-testid="stExpander"] [data-testid="stExpanderHeader"] *,
[data-testid="stExpander"] [data-testid="stExpanderHeader"] p,
[data-testid="stExpander"] [data-testid="stMarkdownContainer"] p,
[data-testid="stExpander"] summary svg,
[data-testid="stExpander"] details > summary svg {
    color: var(--accent) !important;
    fill: var(--accent) !important;
}

/* Названия внутри expander-details (Броня, Оружие...) — тоже accent */
[data-testid="stExpander"] details[open] > summary,
[data-testid="stExpander"] details[open] > summary * {
    color: var(--accent) !important;
}
[data-testid="stExpander"] summary {
    font-weight: 600 !important;
    font-size: clamp(0.95rem, 0.9rem + 0.15vw, 1.1rem) !important;
    text-transform: uppercase;
    letter-spacing: 0.08em;
}
[data-testid="stExpander"] [data-testid="stExpanderDetails"] {
    background: var(--bg-mid) !important;
}
[data-testid="stExpander"] [data-testid="stExpanderDetails"] p,
[data-testid="stExpander"] [data-testid="stExpanderDetails"] li {
    color: var(--ink) !important;
}

[data-testid="stChatMessage"] {
    background: var(--bg-chat) !important;
    border: 1px solid var(--accent-dim) !important;
    border-radius: 6px;
    padding: 16px 20px !important;
    margin-bottom: 14px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.35);
    transition: box-shadow 0.2s ease;
}
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) {
    border-left: 3px solid var(--accent) !important;
    background: linear-gradient(90deg,
        color-mix(in srgb, var(--bg-chat) 92%, var(--accent) 8%),
        var(--bg-chat)) !important;
}
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]):hover {
    box-shadow: 0 4px 16px rgba(0,0,0,0.45),
                0 0 20px color-mix(in srgb, var(--accent) 18%, transparent);
}
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
    border-right: 3px solid var(--accent-bright) !important;
    background: linear-gradient(270deg,
        color-mix(in srgb, var(--bg-chat) 92%, var(--accent-bright) 8%),
        var(--bg-chat)) !important;
}
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]):hover {
    box-shadow: 0 4px 16px rgba(0,0,0,0.45),
                0 0 20px color-mix(in srgb, var(--accent-bright) 18%, transparent);
}

[data-testid="stChatMessage"] p,
[data-testid="stChatMessage"] li {
    color: var(--ink) !important;
    font-size: clamp(1.05rem, 1rem + 0.3vw, 1.25rem) !important;
    line-height: 1.7 !important;
}
[data-testid="stChatMessage"] strong, [data-testid="stChatMessage"] b {
    color: var(--accent-bright) !important;
    font-weight: 700;
}
[data-testid="stChatMessage"] em, [data-testid="stChatMessage"] i {
    color: var(--ink-dim) !important;
}

.chat-name {
    display: flex;
    align-items: center;
    gap: 10px;
    font-family: 'Consolas', 'Menlo', 'Monaco', 'Courier New', monospace;
    font-size: 0.72rem;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    margin-bottom: 8px;
    padding-bottom: 6px;
    border-bottom: 1px solid color-mix(in srgb, var(--accent) 25%, transparent);
}
.chat-name--master { color: var(--accent); }
.chat-name--user { color: var(--accent-bright); }
.chat-name .chat-name-dot {
    display: inline-block;
    width: 6px; height: 6px;
    border-radius: 50%;
    background: currentColor;
    box-shadow: 0 0 8px currentColor;
}

[data-testid="stChatInput"],
[data-testid="stChatInput"] > div,
[data-testid="stChatInput"] > div > div,
[data-testid="stChatInput"] > div > div > div,
.stChatInput,
.stChatInputContainer,
.stChatInputContainer > div {
    background: var(--bg-light) !important;
    background-color: var(--bg-light) !important;
    border-color: var(--accent-dim) !important;
    box-shadow: none !important;
}
[data-testid="stChatInput"],
[data-testid="stChatInput"] > div,
.stChatInput {
    border: 1px solid var(--accent-dim) !important;
    border-radius: 6px !important;
}
[data-testid="stChatInput"] [data-baseweb="textarea"],
[data-testid="stChatInput"] [data-baseweb="base-input"],
[data-testid="stChatInput"] [data-baseweb="textarea"] > div,
[data-testid="stChatInput"] [data-baseweb="base-input"] > div {
    background: transparent !important;
    background-color: transparent !important;
    border-color: transparent !important;
}
[data-testid="stChatInput"] textarea,
[data-testid="stChatInputTextArea"],
.stChatInput textarea,
textarea[data-testid="stChatInputTextArea"] {
    background: transparent !important;
    background-color: transparent !important;
    color: var(--ink) !important;
    -webkit-text-fill-color: var(--ink) !important;
    caret-color: var(--accent) !important;
    font-size: clamp(1rem, 0.95rem + 0.25vw, 1.15rem) !important;
}
[data-testid="stChatInput"] textarea::placeholder,
[data-testid="stChatInputTextArea"]::placeholder,
.stChatInput textarea::placeholder,
textarea[data-testid="stChatInputTextArea"]::placeholder {
    color: var(--ink-faint) !important;
    -webkit-text-fill-color: var(--ink-faint) !important;
    opacity: 1 !important;
    font-style: italic;
}
[data-testid="stChatInput"] button,
[data-testid="stChatInputSubmitButton"] {
    color: var(--accent) !important;
    background: transparent !important;
}

[data-testid="stAlert"] { border-radius: 6px; border-left-width: 5px !important; }
[data-testid="stAlert"] * { font-size: clamp(0.9rem, 0.85rem + 0.1vw, 1.05rem) !important; }

.stTextInput input, .stTextArea textarea,
[data-testid="stTextInput"] input, [data-testid="stTextArea"] textarea {
    background: var(--bg-light) !important;
    background-color: var(--bg-light) !important;
    color: var(--ink) !important;
    -webkit-text-fill-color: var(--ink) !important;
    border: 1px solid var(--accent-dim) !important;
    border-radius: 4px !important;
    font-size: clamp(0.95rem, 0.9rem + 0.15vw, 1.1rem) !important;
    caret-color: var(--accent) !important;
}
.stTextInput input:focus, .stTextArea textarea:focus,
[data-testid="stTextInput"] input:focus, [data-testid="stTextArea"] textarea:focus {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 1px var(--accent) !important;
    outline: none !important;
}
.stTextInput input::placeholder, .stTextArea textarea::placeholder,
[data-testid="stTextInput"] input::placeholder,
[data-testid="stTextArea"] textarea::placeholder {
    color: var(--ink-faint) !important;
    -webkit-text-fill-color: var(--ink-faint) !important;
    opacity: 1 !important;
    font-style: italic;
}
[data-testid="stWidgetLabel"] > div,
[data-testid="stWidgetLabel"] > div > div,
[data-testid="stWidgetLabel"] p,
[data-testid="stWidgetLabel"] label {
    color: var(--accent) !important;
    font-size: clamp(0.88rem, 0.85rem + 0.1vw, 1rem) !important;
    text-transform: uppercase;
    letter-spacing: 0.1em;
}

[data-testid="stSelectbox"] > div,
[data-testid="stSelectbox"] > div > div,
[data-testid="stSelectbox"] [data-baseweb="select"],
[data-testid="stSelectbox"] [data-baseweb="select"] > div,
[data-testid="stSelectbox"] [data-baseweb="select"] > div > div,
[data-baseweb="select"] > div,
[data-baseweb="select"] > div > div,
[data-baseweb="select"] [role="button"],
[data-baseweb="select"] [role="combobox"] {
    background: var(--bg-light) !important;
    background-color: var(--bg-light) !important;
    color: var(--ink) !important;
    border-color: var(--accent-dim) !important;
}
[data-testid="stSelectbox"] [data-baseweb="select"],
[data-testid="stSelectbox"] [data-baseweb="select"] > div,
[data-baseweb="select"] > div {
    border: 1px solid var(--accent-dim) !important;
    border-radius: 4px !important;
}
[data-testid="stSelectbox"] input,
[data-baseweb="select"] input {
    background: transparent !important;
    background-color: transparent !important;
    color: var(--ink) !important;
    -webkit-text-fill-color: var(--ink) !important;
    caret-color: var(--accent) !important;
}
[data-testid="stSelectbox"] input::placeholder,
[data-baseweb="select"] input::placeholder {
    color: var(--ink-faint) !important;
    -webkit-text-fill-color: var(--ink-faint) !important;
    opacity: 1 !important;
}
[data-testid="stSelectbox"] svg,
[data-baseweb="select"] svg {
    fill: var(--accent) !important;
    color: var(--accent) !important;
}

[data-baseweb="popover"],
[data-baseweb="popover"] > div,
[data-baseweb="popover"] > div > div,
[data-baseweb="popover"] [role="listbox"],
[data-baseweb="popover"] ul,
[data-baseweb="popover"] li,
[data-baseweb="popover"] [role="option"],
[data-baseweb="menu"],
[data-baseweb="menu"] > div,
[data-baseweb="menu"] ul,
[data-baseweb="menu"] li,
[data-baseweb="menu"] [role="option"] {
    background: var(--bg-light) !important;
    background-color: var(--bg-light) !important;
    color: var(--ink) !important;
    border-color: var(--accent-dim) !important;
}
[data-baseweb="popover"] [role="option"]:hover,
[data-baseweb="popover"] [role="option"][aria-selected="true"],
[data-baseweb="popover"] [role="option"][aria-selected="true"] *,
[data-baseweb="menu"] [role="option"]:hover,
[data-baseweb="menu"] [role="option"][aria-selected="true"],
[data-baseweb="menu"] [role="option"][aria-selected="true"] * {
    background: var(--accent-dim) !important;
    background-color: var(--accent-dim) !important;
    color: var(--accent-bright) !important;
}

[data-testid="stSlider"] [data-testid="stWidgetLabel"],
[data-testid="stSlider"] [data-testid="stWidgetLabel"] *,
[data-testid="stSlider"] label,
[data-testid="stSlider"] label * {
    color: var(--accent-bright) !important;
    font-weight: 600 !important;
    font-size: clamp(0.95rem, 0.9rem + 0.15vw, 1.05rem) !important;
    opacity: 1 !important;
}
[data-testid="stSlider"] [data-testid="stThumbValue"],
[data-testid="stSlider"] [data-testid="stThumbValue"] *,
[data-testid="stSlider"] div[aria-live="polite"] {
    color: var(--accent-bright) !important;
    font-weight: 700 !important;
    font-size: 1.05rem !important;
    text-shadow: 0 0 8px color-mix(in srgb, var(--accent) 55%, transparent);
}
[data-testid="stSlider"] [data-testid="stTickBarMin"],
[data-testid="stSlider"] [data-testid="stTickBarMax"],
[data-testid="stSlider"] [data-testid="stTickBarMin"] *,
[data-testid="stSlider"] [data-testid="stTickBarMax"] * {
    color: var(--ink-dim) !important;
    font-size: 0.85rem !important;
    opacity: 1 !important;
}
[data-testid="stSlider"] [role="slider"] {
    background: var(--accent) !important;
    border: 2px solid var(--accent-bright) !important;
    box-shadow: 0 0 12px color-mix(in srgb, var(--accent) 60%, transparent) !important;
    outline: none !important;
}
[data-testid="stSlider"] [data-baseweb="slider"] > div > div > div:first-child {
    background: linear-gradient(90deg, var(--accent-dim), var(--accent)) !important;
    box-shadow: 0 0 8px color-mix(in srgb, var(--accent) 40%, transparent) !important;
}

[data-testid="stRadio"] label p,
[data-testid="stRadio"] label * { color: var(--ink) !important; }
[data-testid="stCheckbox"] label p,
[data-testid="stCheckbox"] label * { color: var(--ink) !important; }

[data-testid="stFileUploader"] section,
[data-testid="stFileUploaderDropzone"] {
    background: color-mix(in srgb, var(--bg-mid) 80%, transparent) !important;
    border: 1px dashed var(--accent-dim) !important;
    border-radius: 4px !important;
}
[data-testid="stFileUploader"] section *,
[data-testid="stFileUploaderDropzone"] * { color: var(--ink) !important; }

[data-testid="stProgress"] > div > div > div {
    background: linear-gradient(90deg, var(--accent-dim), var(--accent)) !important;
}

::-webkit-scrollbar { width: 10px; height: 10px; }
::-webkit-scrollbar-track { background: var(--bg-deep); }
::-webkit-scrollbar-thumb { background: var(--accent-dim); border-radius: 5px; }
::-webkit-scrollbar-thumb:hover { background: var(--accent); }
a { color: var(--link) !important; }
a:hover { color: var(--accent-bright) !important; }
hr { border-color: var(--accent-dim) !important; margin: 14px 0 !important; }
</style>
"""


def inject_custom_css(theme_key: str = DEFAULT_THEME):
    st.markdown(BASE_CSS, unsafe_allow_html=True)
    theme = THEMES.get(theme_key, THEMES[DEFAULT_THEME])
    css = THEME_CSS_TEMPLATE
    for k, v in {
        "__BG_DEEP__": theme["bg_deep"], "__BG_MID__": theme["bg_mid"],
        "__BG_LIGHT__": theme["bg_light"], "__BG_CARD__": theme["bg_card"],
        "__BG_CHAT__": theme["bg_chat"], "__ACCENT__": theme["accent"],
        "__ACCENT_DIM__": theme["accent_dim"], "__ACCENT_BRIGHT__": theme["accent_bright"],
        "__TEXT__": theme["text"], "__TEXT_DIM__": theme["text_dim"],
        "__TEXT_FAINT__": theme["text_faint"], "__HEADING__": theme["heading"],
        "__LINK__": theme["link"],
    }.items():
        css = css.replace(k, v)
    st.markdown(css, unsafe_allow_html=True)


# ============================================================
# КЭШ
# ============================================================
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


def get_master_prompt():
    with open(MASTER_PROMPT_PATH, encoding="utf-8") as f:
        return f.read()


# ============================================================
# LOCALSTORAGE
# ============================================================
def _ls_save(localS, sheet, chat_history):
    if not HAS_LS or sheet is None:
        return
    try:
        payload = json.dumps({
            "format": SAVE_FORMAT, "version": SAVE_VERSION,
            "character": sheet, "chat_history": chat_history,
            "saved_at": datetime.now().isoformat(),
        }, ensure_ascii=False)
        localS.setItem(LS_KEY, payload)
    except Exception as e:
        print(f"[LS] ошибка сохранения: {e}")


def _ls_load(localS):
    if not HAS_LS:
        return None
    try:
        raw = localS.getItem(LS_KEY)
        if not raw:
            return None
        data = json.loads(raw)
        if data.get("format") != SAVE_FORMAT:
            return None
        return {"character": data.get("character"),
                "chat_history": data.get("chat_history", [])}
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


def _ls_save_theme(localS, theme_key):
    if not HAS_LS:
        return
    try:
        localS.setItem(LS_THEME_KEY, theme_key)
    except Exception:
        pass


def _ls_load_theme(localS):
    if not HAS_LS:
        return None
    try:
        raw = localS.getItem(LS_THEME_KEY)
        if raw and raw in THEMES:
            return raw
    except Exception:
        pass
    return None


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
_STATE_RE = re.compile(
    r"\[STATE\]\s*(.*?)(?=\n\s*\n|\[STATE\]|\[/STATE\]|$)",
    re.DOTALL | re.IGNORECASE,
)


# Автоподстановка брони по фразам игрока
_ARMOUR_WORDS = {
    "head": ["шлем", "хелм", "маск", "капюшон", "helmet", "head"],
    "body": ["броня", "торс", "кирас", "планшет", "armour", "armor", "body", "chest"],
    "arms": ["перчатк", "наруч", "рукав", "glove", "bracer", "arms"],
    "legs": ["сапог", "ботинк", "понож", "штаны", "штани", "boot", "legs"],
}


def _detect_armour_zone(text: str):
    """По тексту определяет зону брони. Возвращает (zone, 'equip'|'unequip') или None."""
    if not text:
        return None
    low = text.lower()
    # Какое действие?
    action = None
    if re.search(r"\b(снима|снял|убира|сбро|снят|remove|off)\b", low):
        action = "unequip"
    elif re.search(r"\b(надел|надева|натягива|надевают|equip|wear|on)\b", low):
        action = "equip"
    if not action:
        return None
    # Какая зона?
    for zone, words in _ARMOUR_WORDS.items():
        for w in words:
            if w in low:
                return (zone, action)
    return None


def _normalize_state_tags(text: str) -> str:
    """Приводит все одиночные теги к парным, чтобы regex работал."""
    if not text:
        return text
    # Сначала убиваем пустые пары: [STATE][/STATE], [STATE] [/STATE]
    text = re.sub(r"\[STATE\]\s*\[/STATE\]", "", text, flags=re.IGNORECASE)
    # Все [/STATE] → маркер конца
    text = re.sub(r"\[/STATE\]", "\n[__END_STATE__]\n", text, flags=re.IGNORECASE)
    # Все [STATE] → маркер начала
    text = re.sub(r"\[STATE\]", "\n[__BEGIN_STATE__]\n", text, flags=re.IGNORECASE)
    return text


# ============================================================
# STATE: ключи, алиасы, автодетект (patch20)
# ============================================================
_KEY_ALIASES = {
    "inventory_add": "equipment_add",
    "inventory_remove": "equipment_remove",
    "items_add": "equipment_add",
    "items_remove": "equipment_remove",
    "armor_equip": "armour_equip",
    "armor_unequip": "armour_unequip",
    "armor_change": "armour_change",
    "loot": "loot_seen",
}

_KNOWN_EXACT = {
    "wounds", "fate", "insanity", "corruption", "xp", "money",
    "location", "date", "journal", "loot_seen",
    "quest_add", "quest_remove", "npc_add", "npc_remove",
    "effect_add", "effect_remove", "companion_add", "companion_remove",
    "goal_add", "goal_remove",
    "equipment_add", "equipment_remove", "equipment_equip", "equipment_unequip",
    "weapon_add", "weapon_remove", "weapon_lost", "weapon_equip", "weapon_unequip",
    "armour_equip", "armour_unequip", "armour_change",
}

_KNOWN_PREFIXES = (
    "armour_", "special_", "extra_money_", "reputation_", "characteristic_", "ship_",
)

_KEY_RE = re.compile(r"^[a-z][a-z0-9_]*$")
_ARMOUR_ZONES = ("head", "body", "arms", "legs")


def _is_state_key(key):
    if not key or not _KEY_RE.match(key):
        return False
    if key in _KNOWN_EXACT:
        return True
    return any(key.startswith(p) for p in _KNOWN_PREFIXES)


def _normalize_key_val(key, value):
    """Мастер пишет armour_equip=head — превращаем в armour_equip_head=1."""
    key = _KEY_ALIASES.get(key, key)
    vlow = str(value).strip().lower()
    if key == "armour_equip" and vlow in _ARMOUR_ZONES:
        return f"armour_equip_{vlow}", "1"
    if key == "armour_unequip" and vlow in _ARMOUR_ZONES:
        return f"armour_unequip_{vlow}", "1"
    return key, value


_LOOT_TAKE_RE = re.compile(
    r"\b(беру|забира|подбира|хватаю|присваива|в сумку|в инвентарь|в карман)",
    re.IGNORECASE,
)
_LOOT_DROP_RE = re.compile(
    r"\b(выбрасыва|выкидыва|броса|теря|отдаю|сбрасыва|избавля)",
    re.IGNORECASE,
)


def _keywords(text):
    return [w.lower() for w in re.findall(r"[А-Яа-яA-Za-z]{4,}", str(text))]


def _autodetect_loot(user_text, last_loot_seen):
    if not user_text or not last_loot_seen or not _LOOT_TAKE_RE.search(user_text):
        return []
    items = [x.strip() for x in last_loot_seen.split(";") if x.strip()]
    if not items:
        return []
    low = user_text.lower()
    matched = []
    for it in items:
        kws = _keywords(it)
        if kws and any(kw in low for kw in kws):
            matched.append(it)
    if not matched and re.search(r"\b(всё|все|предметы|вещи)\b", low):
        return items
    return matched


def _autodetect_drop(user_text, sheet):
    if not user_text or not _LOOT_DROP_RE.search(user_text):
        return [], []
    low = user_text.lower()
    eq, wp = [], []
    for it in (sheet.get("equipment") or []):
        kws = _keywords(it)
        if kws and any(kw in low for kw in kws):
            eq.append(it)
    for w in (sheet.get("weapons") or []):
        nm = w.get("name") if isinstance(w, dict) else None
        if not nm:
            continue
        kws = _keywords(nm)
        if kws and any(kw in low for kw in kws):
            wp.append(nm)
    return eq, wp


def parse_state_block(text: str):
    """Парсит [STATE] блоки + голые строки с известными ключами."""
    if not text:
        return text, {}
    normalized = _normalize_state_tags(text)
    updates = {}
    out_lines = []
    in_block = False
    for raw_line in normalized.split("\n"):
        line = raw_line.rstrip("\r")
        stripped = line.strip()
        if stripped == "[__BEGIN_STATE__]":
            in_block = True
            continue
        if stripped == "[__END_STATE__]":
            in_block = False
            continue
        if in_block:
            if "=" in stripped:
                key, _, value = stripped.partition("=")
                key = key.strip()
                value = value.strip()
                if key and value:
                    k2, v2 = _normalize_key_val(key, value)
                    updates[k2] = v2
            continue
        out_lines.append(line)

    final_out = []
    for line in out_lines:
        stripped = line.strip()
        if "=" in stripped:
            kp = stripped.split("=", 1)[0].strip()
            if " " not in kp and _is_state_key(kp):
                key, _, value = stripped.partition("=")
                value = value.strip()
                if value:
                    k2, v2 = _normalize_key_val(key.strip(), value)
                    updates[k2] = v2
                    continue
        final_out.append(line)

    cleaned = "\n".join(final_out)
    cleaned = re.sub(r"^\s*\[/?STATE\]\s*$", "", cleaned, flags=re.MULTILINE).strip()
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    if not cleaned and updates:
        cleaned = "_…_"
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

    # === ЭКИПИРОВКА (patch11) ===
    sheet["armour"] = _norm_armour(sheet.get("armour", {}))
    sheet["weapons"] = _norm_weapons(sheet.get("weapons", []))

    # Броня: armour_equip=head / armour_unequip=body
    for k, val in updates.items():
        if k.startswith("armour_equip_"):
            z = k[len("armour_equip_"):].strip().lower()
            if z in ("head", "body", "arms", "legs"):
                sheet["armour"].setdefault(z, {"value": 0, "equipped": True})["equipped"] = True
        if k.startswith("armour_unequip_"):
            z = k[len("armour_unequip_"):].strip().lower()
            if z in ("head", "body", "arms", "legs"):
                sheet["armour"].setdefault(z, {"value": 0, "equipped": True})["equipped"] = False
        if k.startswith("armour_change_"):
            z = k[len("armour_change_"):].strip().lower()
            if z in ("head", "body", "arms", "legs"):
                v = _parse_signed_int(val)
                if v is not None:
                    sheet["armour"].setdefault(z, {"value": 0, "equipped": True})["value"] = v

    # Оружие: weapon_equip=N / weapon_unequip=N / weapon_lost=N
    if "weapon_equip" in updates:
        names = [n.strip() for n in str(updates["weapon_equip"]).split(";") if n.strip()]
        for w in sheet["weapons"]:
            if w.get("name") in names:
                w["equipped"] = True
    if "weapon_unequip" in updates:
        names = [n.strip() for n in str(updates["weapon_unequip"]).split(";") if n.strip()]
        for w in sheet["weapons"]:
            if w.get("name") in names:
                w["equipped"] = False
    if "weapon_lost" in updates:
        names = []
        for n in str(updates["weapon_lost"]).split(";"):
            n = n.strip()
            if "|" in n:
                n = n.split("|")[0].strip()
            if n:
                names.append(n)
        sheet["weapons"] = [w for w in sheet["weapons"] if w.get("name") not in names]
    if "equipment_remove" in updates:
        names = []
        for n in str(updates["equipment_remove"]).split(";"):
            n = n.strip()
            if "|" in n:
                n = n.split("|")[0].strip()
            if n:
                names.append(n)
        sheet["equipment"] = [x for x in sheet.get("equipment", []) if x not in names]

    # Инвентарь экипирован / не экипирован (equipment_equip / equipment_unequip)
    # Хранится в отдельном сете «unequipped_items» (мягкий флаг)
    unequipped = set(sheet.get("unequipped_items") or [])
    if "equipment_unequip" in updates:
        for n in str(updates["equipment_unequip"]).split(";"):
            n = n.strip()
            if n:
                unequipped.add(n)
    if "equipment_equip" in updates:
        for n in str(updates["equipment_equip"]).split(";"):
            n = n.strip()
            if n:
                unequipped.discard(n)
    sheet["unequipped_items"] = sorted(unequipped) if unequipped else []

    if "location" in updates: sheet["location"] = updates["location"]
    if "date" in updates: sheet["game_date"] = updates["date"]

    for short in ["quest", "npc", "effect", "companion", "goal"]:
        plural = {"quest": "quests", "npc": "npcs", "effect": "effects",
                  "companion": "companions", "goal": "goals"}[short]
        add_key = f"{short}_add"; rem_key = f"{short}_remove"
        if add_key in updates:
            items = [i.strip() for i in updates[add_key].split(";") if i.strip()]
            lst = sheet.setdefault(plural, [])
            for it in items:
                if it not in lst: lst.append(it)
        if rem_key in updates:
            items = [i.strip() for i in updates[rem_key].split(";") if i.strip()]
            sheet[plural] = [x for x in sheet.get(plural, []) if x not in items]

    # === ИНВЕНТАРЬ: equipment_add / equipment_remove (patch10) ===
    if "equipment_add" in updates:
        items = [i.strip() for i in str(updates["equipment_add"]).split(";") if i.strip()]
        eq = sheet.setdefault("equipment", [])
        for it in items:
            if it not in eq:
                eq.append(it)
    if "equipment_remove" in updates:
        items = [i.strip() for i in str(updates["equipment_remove"]).split(";") if i.strip()]
        sheet["equipment"] = [x for x in sheet.get("equipment", []) if x not in items]

    # === ОРУЖИЕ: weapon_add=Название | статы  (patch10) ===
    if "weapon_add" in updates:
        items = [i.strip() for i in str(updates["weapon_add"]).split(";") if i.strip()]
        wl = sheet.setdefault("weapons", [])
        existing = {w.get("name", "") for w in wl if isinstance(w, dict)}
        for it in items:
            if "|" in it:
                name, stats = [p.strip() for p in it.split("|", 1)]
            else:
                name, stats = it, ""
            if name and name not in existing:
                wl.append({"name": name, "stats": stats, "notes": ""})
                existing.add(name)
    if "weapon_remove" in updates:
        items = [i.strip() for i in str(updates["weapon_remove"]).split(";") if i.strip()]
        sheet["weapons"] = [
            w for w in sheet.get("weapons", [])
            if not (isinstance(w, dict) and w.get("name") in items)
        ]

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
# ХЕЛПЕРЫ HTML
# ============================================================
def _esc(text) -> str:
    return (str(text)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;"))

def _apply_pending_check(pending, diff_label, diff_mod, sheet, chat_history, localS):
    """Формирует сообщение-проверку и отправляет Мастеру."""
    kind = pending.get("kind", "?")
    name = pending.get("name", "?")
    base = int(pending.get("value", 0) or 0)
    eff = base + diff_mod
    ru = char_ru(name) if kind == "Характеристика" else ""
    name_disp = f"{name} ({ru})" if ru and ru != name else name
    msg = (f"[ПРОВЕРКА] {kind}: {name_disp} · "
           f"База: {base} · Сложность: {diff_label} ({diff_mod:+d}) · "
           f"Эффективное значение: {eff}")
    _send_quick_action(msg, sheet, chat_history, localS)
    st.session_state.pending_check = None

def _dedupe_rolls(rolls):
    """Убирает дубли бросков, оставляя самую подробную версию.

    Ключ дедупа — (expression, rolls, total).
    Приоритет: с reason > без reason, с difficulty > без, с _from_text > без.
    """
    if not rolls:
        return []
    best = {}
    order = []
    for r in rolls:
        if not isinstance(r, dict):
            continue
        if "error" in r:
            k = ("__err__", id(r))
            if k not in best:
                best[k] = (0, r)
                order.append(k)
            continue
        key = (
            str(r.get("expression", "")),
            tuple(r.get("rolls", []) or []),
            int(r.get("total", 0) or 0),
        )
        priority = 0
        if r.get("reason"):
            priority += 1
        if int(r.get("difficulty", 0) or 0) > 0:
            priority += 2
        if r.get("_from_text"):
            priority += 1
        if key not in best:
            best[key] = (priority, r)
            order.append(key)
        elif best[key][0] < priority:
            best[key] = (priority, r)
    return [best[k][1] for k in order]



def _render_pending_check_picker(sheet, chat_history, localS, source="default"):
    """Меню выбора сложности. source — уникальный суффикс для ключей."""
    pending = st.session_state.get("pending_check")
    if not pending or pending.get("source") != source:
        return
    pname = pending["name"]
    ru = char_ru(pname) if pending.get("kind") == "Характеристика" else ""
    pname_disp = f"{pname} ({ru})" if ru and ru != pname else pname
    val = int(pending.get("value", 0) or 0)
    st.markdown(
        f'<div class="pending-check-box">'
        f'▶ ПРОВЕРКА: {_esc(pname_disp)} · {val}'
        f'</div>',
        unsafe_allow_html=True,
    )
    c1, c2 = st.columns(2)
    with c1:
        if st.button("ЛГК +20", key=f"pd_{source}_easy",
                     use_container_width=True, help="Лёгкая (+20)"):
            _apply_pending_check(pending, "Легко", 20, sheet, chat_history, localS)
            st.rerun()
    with c2:
        if st.button("ОБЧ 0", key=f"pd_{source}_norm",
                     use_container_width=True, help="Обычная (0)"):
            _apply_pending_check(pending, "Обычно", 0, sheet, chat_history, localS)
            st.rerun()
    c3, c4 = st.columns(2)
    with c3:
        if st.button("СЛЖ -20", key=f"pd_{source}_hard",
                     use_container_width=True, help="Сложная (-20)"):
            _apply_pending_check(pending, "Сложно", -20, sheet, chat_history, localS)
            st.rerun()
    with c4:
        if st.button("ОСЛ -40", key=f"pd_{source}_vhard",
                     use_container_width=True, help="Очень сложная (-40)"):
            _apply_pending_check(pending, "Очень сложно", -40, sheet, chat_history, localS)
            st.rerun()
    if st.button("✖ ОТМЕНА", key=f"pd_{source}_cancel", use_container_width=True):
        st.session_state.pending_check = None
        st.rerun()


def render_roll(r: dict):
    if not isinstance(r, dict):
        st.warning(f"Некорректный результат броска: {r}")
        return
    if "error" in r:
        st.error(f"Ошибка броска: {r['error']}")
        return

    expr = r.get("expression", "?")
    reason = r.get("reason", "")
    rolls = r.get("rolls", [])
    mod = r.get("modifier", 0)
    total = r.get("total", 0)
    difficulty = r.get("difficulty", 0)
    success = r.get("success")
    margin = r.get("margin", 0)

    roll1 = rolls[0] if rolls else total
    is_check = "1d100" in expr.lower() and difficulty > 0 and success is not None

    if is_check:
        if success:
            card_class = "roll-card--success"
            status_icon = "✅"
            status_text = "УСПЕХ"
            margin_label = "СТЕПЕНИ УСПЕХА"
        else:
            card_class = "roll-card--fail"
            status_icon = "❌"
            status_text = "ПРОВАЛ"
            margin_label = "СТЕПЕНИ ПРОВАЛА"
    else:
        card_class = "roll-card--info"
        status_icon = "🎲"
        status_text = "РЕЗУЛЬТАТ"
        margin_label = ""

    mod_html = ""
    if mod:
        sign = "+" if mod > 0 else ""
        mod_html = f'<div class="roll-mod">{sign}{mod}</div>'

    reason_html = f'<div class="roll-reason">{_esc(reason)}</div>' if reason else ""

    meta_parts = []
    if difficulty > 0:
        meta_parts.append(
            f'<div class="roll-meta-item">'
            f'<span class="label">СЛОЖНОСТЬ</span>'
            f'<span class="value">{difficulty}</span>'
            f'</div>'
        )
    if is_check:
        meta_parts.append(
            f'<div class="roll-meta-item">'
            f'<span class="label">{margin_label}</span>'
            f'<span class="value">{margin}</span>'
            f'</div>'
        )
    meta_html = f'<div class="roll-meta">{"".join(meta_parts)}</div>' if meta_parts else ""

    html = (
        f'<div class="roll-card {card_class}">'
        f'  <div class="roll-header">'
        f'    <span class="roll-label">🎲 БРОСОК</span>'
        f'    <span class="roll-expr">{_esc(expr)}</span>'
        f'    {reason_html}'
        f'  </div>'
        f'  <div class="roll-body">'
        f'    <div class="roll-value">'
        f'      <div class="roll-value-num">{roll1}</div>'
        f'      <div class="roll-value-label">ВЫПАЛО</div>'
        f'    </div>'
        f'    {mod_html}'
        f'  </div>'
        f'  {meta_html}'
        f'  <div class="roll-status">'
        f'    <span class="roll-status-icon">{status_icon}</span>'
        f'    <span class="roll-status-text">{status_text}</span>'
        f'  </div>'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


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
    if idx is None: return None, "Нет гранат"
    sheet["equipment"].pop(idx)
    return f"Игрок использовал гранату: {item}. Опиши взрыв.", None


def quick_medkit(sheet):
    idx, item = _find_in_equipment(sheet, ["аптеч", "медипак", "медпак"])
    if idx is None: return None, "Нет аптечки"
    sheet["equipment"].pop(idx)
    w = sheet.get("wounds", {})
    before = w.get("current", 0); max_w = w.get("max", before)
    after = min(max_w, before + 2); w["current"] = after
    return f"Игрок использовал аптечку ({item}). Раны: {before} → {after}.", None


def quick_stimulant(sheet):
    idx, item = _find_in_equipment(sheet, ["стимул", "боевой наркотик"])
    if idx is None: return None, "Нет стимуляторов"
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
    """Отправляет сообщение от кнопки в чат — Мастер ответит автоматически."""
    if not msg.startswith("["):
        msg = f"[ДЕЙСТВИЕ] {msg}"
    try:
        st.session_state.auto_user_message = msg
        cc.save_character(sheet)
        _ls_save(localS, sheet, chat_history)
    except Exception as e:
        print(f"[quick_action] ошибка сохранения: {e}")
        st.session_state.auto_user_message = msg


def render_theme_selector(localS, location="sidebar"):
    current = st.session_state.get("theme", DEFAULT_THEME)
    theme_keys = list(THEMES.keys())
    key_name = "theme_selector_sidebar" if location == "sidebar" else "theme_selector_main"

    chosen = st.selectbox(
        "🎨 Тема",
        options=theme_keys,
        index=theme_keys.index(current) if current in theme_keys else 0,
        format_func=lambda k: THEMES[k]["label"],
        key=key_name,
    )

    if chosen != current:
        st.session_state.theme = chosen
        _ls_save_theme(localS, chosen)
        st.rerun()


# ============================================================
# ХЕЛПЕРЫ UI
# ============================================================
def render_status_bar():
    date_str = datetime.now().strftime("%d.%m.%Y")
    st.markdown(
        f'<div class="terminal-status">'
        f'<span>◆ ROGUE TRADER</span>'
        f'<span>ТЕРМИНАЛ ДОСТУПА</span>'
        f'<span>{date_str}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )


def render_hero_panel():
    st.markdown(
        '<div class="hero-panel">'
        '<div class="hero-title">⚔️ W A R H A M M E R   4 0 K</div>'
        '<div class="hero-sub">'
        '<span class="line"></span>'
        '<span>RPG С ИИ-МАСТЕРОМ</span>'
        '<span class="line"></span>'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )


def render_section_header(num: str, title: str, meta: str = ""):
    meta_html = f'<span class="meta">{meta}</span>' if meta else ""
    st.markdown(
        f'<div class="section-header">'
        f'<span class="num">{num}</span>'
        f'<span class="title">{title}</span>'
        f'<span class="line"></span>'
        f'{meta_html}'
        f'</div>',
        unsafe_allow_html=True,
    )


def render_chat_name(role: str, player_name: str = "Игрок"):
    label = "МАСТЕР" if role == "assistant" else player_name.upper()
    cls = "chat-name--master" if role == "assistant" else "chat-name--user"
    st.markdown(
        f'<div class="chat-name {cls}">'
        f'<span class="chat-name-dot"></span>'
        f'<span>{label}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ============================================================
# АВАТАРКИ
# ============================================================
AVATAR_USER = "🧑"


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

    render_status_bar()
    st.title("⚔️ Создание персонажа")
    st.progress((step + 1) / 8)
    st.caption(f"Шаг {step + 1} из 8")

    if step == 0:
        render_section_header("01", "СПОСОБ ГЕНЕРАЦИИ")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🎲 Броски кубиков (2d10 + мод)", use_container_width=True):
                data["generation_method"] = "dice"; wizard_go(1); st.rerun()
        with col2:
            if st.button("⚖️ Распределение очков (point-buy)", use_container_width=True):
                data["generation_method"] = "pointbuy"; wizard_go(1); st.rerun()

    elif step == 1:
        render_section_header("02", "ФРАКЦИЯ")
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
        render_section_header("03", f"{f['name']} — ПУТЬ")
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
        render_section_header("04", f"{sub['name']} — АРХЕТИП")
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
        render_section_header("05", "ДОПОЛНИТЕЛЬНЫЕ ПАРАМЕТРЫ")
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
        render_section_header("06", "ХАРАКТЕРИСТИКИ")
        if data["generation_method"] == "dice":
            if not data.get("dice_rolled_once"):
                st.write(f"Бросок **2d10 + {dice_mod}**.")
                if st.button("🎲 Бросить кубики", use_container_width=True):
                    data["characteristics"] = cc.generate_by_dice(dice_mod)
                    data["dice_rolled_once"] = True; st.rerun()
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
                        data["reroll_used"] = True; st.rerun()
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
            spent = sum(v - 25 for v in pv.values()); left = 100 - spent
            st.write(f"**Осталось: {left}**")
            cols = st.columns(2)
            with cols[0]:
                if st.button("← Назад"):
                    wizard_go(4 if sub.get("extra_choices") else 3); st.rerun()
            with cols[1]:
                if st.button("Далее →", disabled=(left < 0), use_container_width=True):
                    data["characteristics"] = dict(pv); wizard_go(6); st.rerun()

    elif step == 6:
        render_section_header("07", "ИМЯ И ДЕТАЛИ")
        data["name"] = st.text_input("Имя *", value=data.get("name", ""))
        data["age"] = st.text_input("Возраст", value=data.get("age", ""))
        data["appearance"] = st.text_area("Внешность", value=data.get("appearance", ""), height=100)
        data["background"] = st.text_area("Предыстория", value=data.get("background", ""), height=150)
        cols = st.columns(2)
        with cols[0]:
            if st.button("← Назад"): wizard_go(5); st.rerun()
        with cols[1]:
            if st.button("Собрать лист →", use_container_width=True):
                if not data["name"].strip(): st.error("Введи имя")
                else: wizard_go(7); st.rerun()

    elif step == 7:
        render_section_header("08", "ЛИСТ ПЕРСОНАЖА")
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
            with st.expander("Предыстория"): st.write(sheet["background"])
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
                _ls_save(localS, sheet, [])
                st.session_state.wizard_step = 0
                st.session_state.wizard_data = {}
                st.session_state.in_wizard = False
                st.rerun()


# ============================================================
# СТАРТОВЫЙ ЭКРАН
# ============================================================
def _download_save_payload(sheet, chat_history):
    return json.dumps({
        "format": SAVE_FORMAT, "version": SAVE_VERSION,
        "character": sheet, "chat_history": chat_history,
        "saved_at": datetime.now().isoformat(),
    }, ensure_ascii=False, indent=2)


def render_start_screen(localS):
    render_status_bar()
    render_hero_panel()

    col_l, col_theme = st.columns([3, 1])
    with col_theme:
        render_theme_selector(localS, location="main")

    render_section_header("01", "НОВАЯ ИГРА")

    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            st.markdown(
                '<div style="font-family:Consolas,monospace;color:var(--accent,'
                '#c9a961);font-size:1.8rem;letter-spacing:0.3em;'
                'margin-bottom:6px;">⚔</div>'
                '<div style="font-family:Consolas,monospace;color:var(--accent-bright,'
                '#e8d9b8);font-size:1.05rem;letter-spacing:0.18em;'
                'text-transform:uppercase;font-weight:700;margin-bottom:6px;">'
                'Создать персонажа</div>'
                '<div style="color:var(--ink-dim,#b8ac92);font-size:0.9rem;'
                'line-height:1.5;margin-bottom:14px;">'
                '8 шагов · броски кубиков или распределение очков</div>',
                unsafe_allow_html=True,
            )
            if st.button("▶ НАЧАТЬ СОЗДАНИЕ", type="primary", use_container_width=True):
                st.session_state.wizard_step = 0
                st.session_state.wizard_data = {}
                st.session_state.in_wizard = True
                st.rerun()
    with col2:
        with st.container(border=True):
            st.markdown(
                '<div style="font-family:Consolas,monospace;color:var(--accent,'
                '#c9a961);font-size:1.8rem;letter-spacing:0.3em;'
                'margin-bottom:6px;">📥</div>'
                '<div style="font-family:Consolas,monospace;color:var(--accent-bright,'
                '#e8d9b8);font-size:1.05rem;letter-spacing:0.18em;'
                'text-transform:uppercase;font-weight:700;margin-bottom:6px;">'
                'Загрузить сохранение</div>'
                '<div style="color:var(--ink-dim,#b8ac92);font-size:0.9rem;'
                'line-height:1.5;margin-bottom:6px;">'
                'JSON-файл персонажа (лист + история)</div>',
                unsafe_allow_html=True,
            )
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

    chars = cc.list_characters()
    meta = f"{len(chars)} ЗАПИСЬ" if chars else "ПУСТО"
    render_section_header("02", "ПЕРСОНАЖИ", meta)

    if not chars:
        st.info("Нет сохранённых персонажей.")
    else:
        for i, c in enumerate(chars, start=1):
            with st.container(border=True):
                st.markdown(
                    f'<div style="display:flex;justify-content:space-between;'
                    f'align-items:center;margin-bottom:14px;">'
                    f'<span style="font-family:Consolas,monospace;color:var(--accent,'
                    f'#c9a961);font-size:1.2rem;letter-spacing:0.2em;">☠</span>'
                    f'<span style="font-family:Consolas,monospace;color:var(--accent-dim,'
                    f'#8a7444);font-size:0.78rem;letter-spacing:0.22em;">'
                    f'ЗАПИСЬ {i:02d}</span>'
                    f'</div>'
                    f'<div style="font-family:Consolas,monospace;color:var(--heading,'
                    f'#e8d9b8);font-size:1.5rem;letter-spacing:0.14em;font-weight:700;'
                    f'margin-bottom:6px;">{c["name"]}</div>'
                    f'<div style="height:1px;background:linear-gradient(90deg,'
                    f'var(--accent-dim,#8a7444),transparent 70%);margin-bottom:12px;"></div>'
                    f'<div style="color:var(--ink-dim,#b8ac92);font-family:Consolas,'
                    f'monospace;font-size:0.88rem;letter-spacing:0.1em;'
                    f'margin-bottom:16px;">'
                    f'{c.get("faction","")} · {c.get("subfaction","")} · '
                    f'{c.get("archetype","")}</div>',
                    unsafe_allow_html=True,
                )
                b1, b2, b3 = st.columns(3)
                with b1:
                    if st.button("▶ ИГРАТЬ", key=f"load_{c['name']}",
                                 use_container_width=True, type="primary"):
                        sheet = cc.load_character(c["path"])
                        chat = cc.load_chat_history(c["name"])
                        st.session_state.character = sheet
                        st.session_state.character_path = c["path"]
                        st.session_state.chat_history = chat
                        st.session_state.in_wizard = False
                        _ls_save(localS, sheet, chat)
                        st.rerun()
                with b2:
                    try:
                        sheet_data = cc.load_character(c["path"])
                        chat_data = cc.load_chat_history(c["name"])
                        payload = _download_save_payload(sheet_data, chat_data)
                        st.download_button(
                            "💾 СКАЧАТЬ",
                            data=payload,
                            file_name=f"{c['name']}_save.json",
                            mime="application/json",
                            key=f"dl_{c['name']}",
                            use_container_width=True,
                        )
                    except Exception:
                        st.caption("—")
                with b3:
                    if st.button("🗑 УДАЛИТЬ", key=f"del_{c['name']}",
                                 use_container_width=True):
                        cc.delete_character(c["path"])
                        cc.delete_chat_history(c["name"])
                        st.rerun()

    st.write("")
    st.write("")
    col_a, col_b, col_c = st.columns([3, 2, 3])
    with col_b:
        if st.button("⌫ СБРОСИТЬ АВТОСОХРАНЕНИЕ", use_container_width=True):
            _ls_clear(localS)
            st.toast("Автосохранение очищено", icon="✅")


# ============================================================
# ВСТРОЕННЫЙ ЛИСТ ПЕРСОНАЖА (для мобильных)
# ============================================================
def render_character_inline(sheet, kb, localS, chat_history):
    wounds = sheet.get("wounds", {"current": 0, "max": 0})
    fate = sheet.get("fate_points", {"current": 0, "max": 0})

    c1, c2 = st.columns(2)
    c1.metric("❤️ Раны", f"{wounds.get('current', 0)}/{wounds.get('max', 0)}")
    c2.metric("🍀 Судьба", f"{fate.get('current', 0)}/{fate.get('max', 0)}")
    c1, c2 = st.columns(2)
    c1.metric("🌀 Порча", sheet.get("corruption", 0))
    c2.metric("🧠 Безумие", sheet.get("insanity", 0))

    loc = sheet.get("location", "")
    date = sheet.get("game_date", "")
    if loc: st.markdown(f"📍 **Локация:** {loc}")
    if date: st.markdown(f"⏱️ **Время:** {date}")

    money = sheet.get("money", 0)
    currency = sheet.get("currency", "Троны")
    st.markdown(f"💰 **{currency}:** {money}")

    with st.expander("🎒 Снаряжение", expanded=False):
        eq = sheet.get("equipment", [])
        if eq:
            for e in eq: st.write(f"• {e}")
        else:
            st.caption("— пусто —")

    with st.expander("⚔️ Оружие", expanded=False):
        for w in sheet.get("weapons", []):
            st.markdown(f"**{w.get('name','')}**")
            st.caption(w.get("stats", ""))
            if w.get("notes"): st.caption(f"_{w['notes']}_")

    with st.expander("✨ Таланты", expanded=False):
        for t in sheet.get("talents", []): st.write(f"• {t}")

    with st.expander("📖 Навыки", expanded=False):
        for s in sheet.get("skills", []):
            st.write(f"• **{s['name']}** ({s.get('characteristic','')}): {s.get('value','')}")

    powers = sheet.get("psychic_powers", [])
    if powers:
        with st.expander("🔮 Психосилы", expanded=False):
            for p in powers: st.write(f"• {p}")

    with st.expander("📋 Задачи", expanded=False):
        q = sheet.get("quests", [])
        if q:
            for item in q: st.write(f"• {item}")
        else:
            st.caption("— нет —")

    with st.expander("👥 NPC", expanded=False):
        n = sheet.get("npcs", [])
        if n:
            for item in n: st.write(f"• {item}")
        else:
            st.caption("— нет —")

    effects = sheet.get("effects", [])
    if effects:
        with st.expander("⚡ Эффекты", expanded=False):
            for e in effects: st.write(f"• {e}")

    with st.expander("🚀 Корабль", expanded=False):
        ship = sheet.get("ship")
        if not ship:
            st.caption("— нет —")
        else:
            st.markdown(f"**{ship['name']}**")
            st.caption(f"{ship.get('class','')} • {ship.get('type','')}")
            st.write(ship.get("description", ""))

    journal = sheet.get("journal", [])
    if journal:
        with st.expander("📖 Дневник", expanded=False):
            for entry in journal: st.write(f"• {entry}")


# ============================================================
# САЙДБАР — ЛИСТ ПЕРСОНАЖА
# ============================================================
def _norm_armour(arm):
    """Нормализует броню в {zone: {value, equipped}, notes}."""
    if not arm:
        return {}
    result = {"notes": arm.get("notes", "")}
    for z in ["head", "body", "arms", "legs"]:
        v = arm.get(z, 0)
        if isinstance(v, dict):
            result[z] = {
                "value": int(v.get("value", 0) or 0),
                "equipped": bool(v.get("equipped", True)),
            }
        else:
            result[z] = {"value": int(v or 0), "equipped": True}
    return result


def _norm_weapons(ws):
    """Нормализует оружие в dict с флагом equipped."""
    result = []
    for w in (ws or []):
        if not isinstance(w, dict):
            continue
        nw = dict(w)
        nw.setdefault("equipped", True)
        result.append(nw)
    return result


def _ap_total(sheet):
    """AP — только по экипированным зонам."""
    arm = _norm_armour(sheet.get("armour", {}))
    vals = []
    for z in ["head", "body", "arms", "legs"]:
        zz = arm.get(z, {})
        if zz.get("equipped", True):
            vals.append(int(zz.get("value", 0) or 0))
    return max(vals) if vals else 0


def _render_stat_bar(label: str, current: int, maximum: int, variant: str, icon: str = ""):
    maximum = max(1, int(maximum or 1))
    current = int(current or 0)
    pct = max(0, min(100, round(100 * current / maximum)))
    is_low = (variant == "wounds" and pct < 30)
    low_class = " stat-bar--low" if is_low else ""
    pulse_attr = ' data-pulse="on"' if is_low else ''
    st.markdown(
        f'<div class="stat-bar stat-bar--{variant}{low_class}"{pulse_attr}>'
        f'  <div class="stat-bar-head">'
        f'    <span class="stat-bar-label">{icon} {label}</span>'
        f'    <span class="stat-bar-value">{current} / {maximum}</span>'
        f'  </div>'
        f'  <div class="stat-bar-track">'
        f'    <div class="stat-bar-fill" style="width:{pct}%"></div>'
        f'  </div>'
        f'</div>',
        unsafe_allow_html=True,
    )




def render_location_bar(sheet):
    """Полоса локации над чатом: 📍 ЛОКАЦИЯ · значение · ⏱ ВРЕМЯ · значение."""
    sheet = sheet or {}
    loc = str(sheet.get("location", "") or "").strip() or "Неизвестное место"
    date = str(sheet.get("game_date", "") or "").strip() or "—"
    st.markdown(
        f'<div class="location-bar">'
        f'  <span class="lbl">📍 ЛОКАЦИЯ</span>'
        f'  <span class="val">{_esc(loc)}</span>'
        f'  <span class="dot">◆</span>'
        f'  <span class="lbl">⏱ ВРЕМЯ</span>'
        f'  <span class="val">{_esc(date)}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )
def _render_character_summary(sheet: dict, chat_history: list, localS):
    name = sheet.get("name", "Безымянный")
    faction = sheet.get("faction", "")
    subfaction = sheet.get("subfaction", "")
    archetype = sheet.get("archetype", "")
    faction_avatar = get_faction_avatar(sheet)
    sub_line = " · ".join([x for x in [faction, subfaction, archetype] if x]) or "—"

    st.markdown(
        f'<div class="char-sheet-header">'
        f'  <div class="char-avatar">{faction_avatar}</div>'
        f'  <div style="min-width:0;">'
        f'    <div class="char-sheet-name">{_esc(name)}</div>'
        f'    <div class="char-sheet-sub">{_esc(sub_line)}</div>'
        f'  </div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    w = sheet.get("wounds", {}) or {}
    _render_stat_bar("РАНЫ", int(w.get("current", 0) or 0),
                     int(w.get("max", 1) or 1), "wounds", "❤️")
    f = sheet.get("fate_points", {}) or {}
    _render_stat_bar("СУДЬБА", int(f.get("current", 0) or 0),
                     int(f.get("max", 1) or 1), "fate", "🍀")

    xp = int(sheet.get("xp", 0) or 0)
    rank = int(sheet.get("rank", 1) or 1)
    xp_next = rank * 500
    _render_stat_bar(f"ОПЫТ · РАНГ {rank}", xp, xp_next, "xp", "★")

    corr = int(sheet.get("corruption", 0) or 0)
    ins = int(sheet.get("insanity", 0) or 0)
    if corr > 0 or ins > 0:
        c1, c2 = st.columns(2)
        with c1:
            if corr > 0:
                _render_stat_bar("ПОРЧА", corr, max(corr, 10), "corruption", "🌀")
        with c2:
            if ins > 0:
                _render_stat_bar("БЕЗУМИЕ", ins, max(ins, 10), "insanity", "🧠")

    ap = _ap_total(sheet)
    bonuses = sheet.get("bonuses", {}) or {}
    ini = int(bonuses.get("Ag", 0) or 0)
    per = int(bonuses.get("Per", 0) or 0)

    st.markdown(
        f'<div class="meta-grid">'
        f'  <div class="meta-tile">'
        f'    <div class="icon">🛡️</div>'
        f'    <div class="label">БРОНЯ</div>'
        f'    <div class="value">{ap}</div>'
        f'  </div>'
        f'  <div class="meta-tile">'
        f'    <div class="icon">⚡</div>'
        f'    <div class="label">ИНИЦ</div>'
        f'    <div class="value">{ini:+d}</div>'
        f'  </div>'
        f'  <div class="meta-tile">'
        f'    <div class="icon">👁</div>'
        f'    <div class="label">ВНИМ</div>'
        f'    <div class="value">{per:+d}</div>'
        f'  </div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    chars = sheet.get("characteristics", {}) or {}
    with st.expander("⚔ ПРОВЕРКИ", expanded=True, key="exp_chars"):
        char_cols = st.columns(3)
        for i, ch in enumerate(cc.CHARACTERISTICS):
            val = int(chars.get(ch, 0) or 0)
            bon = int(bonuses.get(ch, val // 10) or 0)
            ru = char_ru(ch)
            label = f"{ru} · {val}" if ru else f"{ch} · {val}"
            with char_cols[i % 3]:
                if st.button(label, key=f"chk_char_{ch}",
                             use_container_width=True,
                             help=f"{ch} — {char_ru_long(ch)}: база {val}, бонус {bon:+d}"):
                    st.session_state.pending_check = {
                        "source": "chars",
                        "kind": "Характеристика", "name": ch, "value": val,
                    }
                    st.rerun()
        _render_pending_check_picker(sheet, chat_history, localS, source="chars")
    st.markdown('<div class="sidebar-divider"></div>', unsafe_allow_html=True)


def _render_quick_actions(sheet, chat_history, localS):
    with st.expander("⚡ ДЕЙСТВИЯ", expanded=False, key="exp_actions"):
        cols = st.columns(2)
        with cols[0]:
            if st.button("🔥 Судьба", use_container_width=True, help="Потратить Очко Судьбы"):
                msg, err = quick_fate_point(sheet)
                if err: st.toast(err, icon="⚠️")
                else: _send_quick_action(msg, sheet, chat_history, localS); st.rerun()
        with cols[1]:
            if st.button("💣 Граната", use_container_width=True):
                msg, err = quick_grenade(sheet)
                if err: st.toast(err, icon="⚠️")
                else: _send_quick_action(msg, sheet, chat_history, localS); st.rerun()
        cols = st.columns(2)
        with cols[0]:
            if st.button("🏥 Аптечка", use_container_width=True):
                msg, err = quick_medkit(sheet)
                if err: st.toast(err, icon="⚠️")
                else: _send_quick_action(msg, sheet, chat_history, localS); st.rerun()
        with cols[1]:
            if st.button("⚡ Стим", use_container_width=True):
                msg, err = quick_stimulant(sheet)
                if err: st.toast(err, icon="⚠️")
                else: _send_quick_action(msg, sheet, chat_history, localS); st.rerun()

        effects = sheet.get("effects", [])
        if effects:
            eff_to_remove = st.selectbox("Снять эффект", options=["—"] + effects,
                                         key="effect_remove_select",
                                         label_visibility="collapsed")
            if eff_to_remove != "—" and st.button("✖️ Снять", use_container_width=True):
                msg, err = quick_remove_effect(sheet, eff_to_remove)
                if err: st.toast(err, icon="⚠️")
                else: _send_quick_action(msg, sheet, chat_history, localS); st.rerun()


def render_character_sidebar(sheet, kb, model, localS, chat_history):
    _render_character_summary(sheet, chat_history, localS)

    _render_quick_actions(sheet, chat_history, localS)
    st.markdown('<div class="sidebar-divider"></div>', unsafe_allow_html=True)

    tabs = st.tabs(["Перс", "Инвент", "Мир", "Корабль", "Заметки"])

    with tabs[0]:
        skills = sheet.get("skills", [])
        if skills:
            with st.expander(f"📖 НАВЫКИ ({len(skills)})", expanded=False, key="exp_skills"):
                for i, s in enumerate(skills):
                    nm = s.get("name", "?")
                    val = int(s.get("value", 0) or 0)
                    ch = s.get("characteristic", "")
                    ru_ch = char_ru(ch)
                    ch_disp = ru_ch if ru_ch else ch
                    if st.button(f"{nm} · {ch_disp} {val}", key=f"skl_{i}",
                                 use_container_width=True,
                                 help=f"Проверка навыка «{nm}» ({ch} — {char_ru_long(ch)})"):
                        st.session_state.pending_check = {
                            "source": "skills",
                            "kind": "Навык", "name": nm, "value": val,
                        }
                        st.rerun()
                _render_pending_check_picker(sheet, chat_history, localS, source="skills")

        talents = sheet.get("talents", [])
        if talents:
            with st.expander(f"✨ ТАЛАНТЫ ({len(talents)})", expanded=False, key="exp_talents"):
                for i, t in enumerate(talents):
                    if st.button(f"📖 {t}", key=f"tal_{i}",
                                 use_container_width=True,
                                 help=f"Справка: {t}"):
                        _send_quick_action(
                            f'[СПРАВКА] Расскажи кратко по канону про талант: "{t}"',
                            sheet, chat_history, localS)
                        st.rerun()

        weapons = sheet.get("weapons", [])
        if weapons:
            with st.expander(f"⚔ ОРУЖИЕ ({len(weapons)})", expanded=False, key="exp_weapons"):
                for i, w in enumerate(weapons):
                    wname = w.get("name", "?")
                    stats = w.get("stats", "")
                    equipped = bool(w.get("equipped", True))
                    is_ranged = bool(re.search(r"\d+\s*м", stats))
                    badge = "✅" if equipped else "⚪"
                    badge_color = "var(--accent-bright, #e8d9b8)" if equipped else "var(--ink-dim, #8a8068)"
                    st.markdown(
                        f'<div style="font-family:Consolas,monospace;font-size:0.85rem;'
                        f'color:{badge_color};margin:12px 0 3px 0;'
                        f'font-weight:700;letter-spacing:0.03em;">{badge} {_esc(wname)}</div>'
                        f'<div style="font-family:Consolas,monospace;font-size:0.7rem;'
                        f'color:var(--ink-dim, #b8ac92);margin-bottom:6px;'
                        f'word-break:break-word;">{_esc(stats)}</div>',
                        unsafe_allow_html=True,
                    )
                    if equipped:
                        c1, c2, c3 = st.columns(3)
                        if is_ranged:
                            labels = [("ОДИН", "одиночный выстрел", "single"),
                                      ("ОЧЕР", "стрельба очередью", "burst"),
                                      ("ПРИЦ", "прицельный выстрел", "aimed")]
                        else:
                            labels = [("АТАК", "обычная атака", "atk"),
                                      ("ПАР", "парирование", "par"),
                                      ("МОЩН", "мощная атака", "pow")]
                        for col, (lbl, mode, sfx) in zip([c1, c2, c3], labels):
                            with col:
                                if st.button(lbl, key=f"w_{sfx}_{i}",
                                             use_container_width=True,
                                             help=f"{wname}: {mode}"):
                                    _send_quick_action(
                                        f'[АТАКА] {wname} — {mode}',
                                        sheet, chat_history, localS)
                                    st.rerun()
                    else:
                        st.caption("_Оружие убрано. Достань командой «Достаю X»._")
                    if w.get("notes"):
                        st.caption(f"_{w['notes']}_")

        powers = sheet.get("psychic_powers", [])
        if powers:
            with st.expander(f"🔮 ПСИХОСИЛЫ ({len(powers)})", expanded=False, key="exp_psy"):
                for i, p in enumerate(powers):
                    pname = p if isinstance(p, str) else p.get("name", "?")
                    st.markdown(
                        f'<div style="font-family:Consolas,monospace;font-size:0.85rem;'
                        f'color:var(--accent-bright, #e8d9b8);margin:12px 0 6px 0;'
                        f'font-weight:700;letter-spacing:0.03em;">{_esc(pname)}</div>',
                        unsafe_allow_html=True,
                    )
                    c1, c2, c3 = st.columns(3)
                    modes = [("ТОЧН", "точечное применение", "pt"),
                             ("ОБЛ", "по площади", "ar"),
                             ("КОНЦ", "с концентрацией", "cc")]
                    for col, (lbl, mode, sfx) in zip([c1, c2, c3], modes):
                        with col:
                            if st.button(lbl, key=f"p_{sfx}_{i}",
                                         use_container_width=True,
                                         help=f"{pname}: {mode}"):
                                _send_quick_action(
                                    f'[ПСИ] {pname} — {mode}',
                                    sheet, chat_history, localS)
                                st.rerun()

        arm = _norm_armour(sheet.get("armour", {}))
        if arm:
            with st.expander("🛡️ БРОНЯ", expanded=False, key="exp_armour"):
                zones = [("head", "Голова"), ("body", "Тело"),
                         ("arms", "Руки"), ("legs", "Ноги")]
                for z, zname in zones:
                    zz = arm.get(z, {}) or {}
                    v = int(zz.get("value", 0) or 0)
                    eq = bool(zz.get("equipped", True))
                    badge = "✅" if eq else "⚪"
                    col = "var(--accent-bright, #e8d9b8)" if eq else "var(--ink-dim, #8a8068)"
                    extra = " · снято" if not eq else ""
                    st.markdown(
                        f'<div style="font-family:Consolas,monospace;font-size:0.84rem;'
                        f'color:{col};padding:5px 0;border-bottom:1px dashed '
                        f'color-mix(in srgb, var(--accent) 15%, transparent);">'
                        f'{badge} {zname}: <b>{v}</b>{extra}</div>',
                        unsafe_allow_html=True,
                    )
                if arm.get("notes"): st.caption(arm["notes"])

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
        loc = sheet.get("location", ""); date = sheet.get("game_date", "")
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
            hull = ship.get("hull", {}); crew = ship.get("crew", {})
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
                st.markdown("**Заметки:**"); st.write(ship["notes"])

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

        st.markdown("**📝 Заметки**")
        st.text_area("Заметки", key=notes_key, height=200,
                     label_visibility="collapsed",
                     placeholder="Имена NPC, планы, зацепки...",
                     on_change=_save_notes)
        journal = sheet.get("journal", [])
        if journal:
            st.markdown("**📖 Дневник**")
            for entry in journal: st.write(f"• {entry}")

    st.write("---")
    st.caption(f"📚 Чанков: {kb.chunk_count} | 💬 Ходов: {len(chat_history)}")

    with st.expander("⚙️ Экспорт / Импорт"):
        try:
            payload = _download_save_payload(sheet, chat_history)
            st.download_button("💾 Скачать сейв",
                               data=payload,
                               file_name=f"{sheet.get('name','unnamed')}_save.json",
                               mime="application/json",
                               use_container_width=True)
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
                    _raw_chat = data.get("chat_history", [])
                    cleaned_chat = []
                    for m in _raw_chat:
                        if isinstance(m, dict) and m.get("role") == "assistant":
                            cleaned_text, _ = parse_state_block(m.get("content", ""))
                            if cleaned_text and cleaned_text != "_…_":
                                mc = dict(m)
                                mc["content"] = cleaned_text
                                cleaned_chat.append(mc)
                        else:
                            cleaned_chat.append(m)
                    st.session_state.chat_history = cleaned_chat
                    _ls_save(localS, data["character"], st.session_state.chat_history)
                    st.rerun()
            except Exception as e:
                st.error(f"Ошибка: {e}")

    with st.expander("🎨 Тема"):
        render_theme_selector(localS, location="sidebar")

    with st.expander("🛠 Отладка"):
        log_data = {
            "character": sheet, "chat_history": chat_history,
            "meta": {"model": model, "chunks_in_db": kb.chunk_count,
                     "vector_mode": kb.is_vector_mode,
                     "exported_at": datetime.now().isoformat()},
        }
        st.download_button("📥 Скачать логи",
                           data=json.dumps(log_data, ensure_ascii=False, indent=2),
                           file_name=f"session_{sheet.get('name','unnamed')}.json",
                           mime="application/json", use_container_width=True)
        if st.button("👁 Последний запрос", use_container_width=True):
            st.session_state.show_last_request = not st.session_state.get("show_last_request", False)
        if st.session_state.get("show_last_request"):
            st.code(st.session_state.get("last_request_to_giga", "—"), language="text")

        if st.button("📜 Последний [STATE]", use_container_width=True):
            st.session_state.show_last_state = not st.session_state.get("show_last_state", False)
        if st.session_state.get("show_last_state"):
            last_state = st.session_state.get("last_state_updates") or {}
            if last_state:
                st.json(last_state)
            else:
                st.caption("— пусто —")

    st.write("---")
    if st.button("🔄 Заново", use_container_width=True, help="Начать историю заново"):
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
        f"4. Не вводи NPC, чуждых расе персонажа.\n"
        f"5. ОБЯЗАТЕЛЬНО укажи в [STATE] поля location= и date= для первой сцены."
    )


def render_chat(localS):
    kb = get_kb(); giga = get_giga(); master_prompt = get_master_prompt()
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    with st.sidebar:
        render_character_sidebar(st.session_state.character, kb, MODEL,
                                 localS, st.session_state.chat_history)

    render_status_bar()
    render_location_bar(st.session_state.character)
    st.title("🎲 Игра")

    with st.expander("👤 Лист персонажа", expanded=False):
        render_character_inline(st.session_state.character, kb, localS,
                                st.session_state.chat_history)

    faction_avatar = get_faction_avatar(st.session_state.character)
    player_name = (st.session_state.character or {}).get("name", "Игрок")

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
                    st.session_state.last_state_updates = dict(state_updates)
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
        role = msg["role"]
        content = msg.get("content", "")
        # Чистим STATE-мусор даже при показе (защита от старой грязи в LS)
        if role == "assistant":
            content, _ = parse_state_block(content)
            if not content or content == "_…_":
                continue
        avatar = AVATAR_USER if role == "user" else faction_avatar
        with st.chat_message(role, avatar=avatar):
            render_chat_name(role, player_name)
            for r in _dedupe_rolls(msg.get("rolls", []) or []):
                render_roll(r)
            st.markdown(content)

    user_input = st.chat_input("Что делаешь?")
    auto_msg = st.session_state.pop("auto_user_message", None)
    if auto_msg:
        user_input = auto_msg
    if not user_input:
        return

    st.session_state.chat_history.append({"role": "user", "content": user_input, "rolls": []})
    with st.chat_message("user", avatar=AVATAR_USER):
        render_chat_name("user", player_name)
        st.markdown(user_input)
    cc.save_chat_history(st.session_state.character.get("name", "unnamed"),
                         st.session_state.chat_history)
    _ls_save(localS, st.session_state.character, st.session_state.chat_history)

    context = kb.format_context(user_input, top_k=TOP_K_KNOWLEDGE)
    sheet_json = json.dumps(st.session_state.character, ensure_ascii=False, indent=2)
    parts = [f"=== АКТУАЛЬНЫЙ ЛИСТ ПЕРСОНАЖА ===\n{sheet_json}"]
    if context: parts.append(context)
    parts.append(f"=== СООБЩЕНИЕ ИГРОКА ===\n{user_input}")

    # Подсказка Мастеру в зависимости от метки
    hint = ""
    msg_upper = user_input.upper()
    if "[ПРОВЕРКА]" in msg_upper:
        hint = ("=== ИНСТРУКЦИЯ ===\n"
                "Игрок нажал кнопку проверки. Сделай бросок 1d100 против "
                "ЭФФЕКТИВНОГО ЗНАЧЕНИЯ из сообщения. Оформи результат ОДНОЙ "
                "строкой: 🎲 Бросок 1d100 (причина): выпало [N] — сложность D. "
                "Если N ≤ D — УСПЕХ, иначе ПРОВАЛ. Учти степени (разница // 10). "
                "Затем опиши последствия в сцене.\n"
                "ВАЖНО: выведи РОВНО ОДИН бросок 1d100, не дублируй его. "
                "Не вызывай функцию roll_dice — только пиши броском в тексте. "
                "Отвечай ТОЛЬКО на текущий запрос, не смешивай с прошлыми.")
    elif "[АТАКА]" in msg_upper:
        hint = ("=== ИНСТРУКЦИЯ ===\n"
                "Игрок атакует. Сделай бросок 1d100 против BS (дальний бой) "
                "или WS (ближний бой) персонажа со сложностью по "
                "обстоятельствам (обычно 40-60). Оформи броском "
                "🎲 Бросок 1d100. При успехе — опиши попадание и урон.")
    elif "[СПРАВКА]" in msg_upper:
        hint = ("=== ИНСТРУКЦИЯ ===\n"
                "Игрок просит справку по канону. Ответь кратко (3-6 "
                "предложений), по правилам WH40K Rogue Trader, без "
                "выдумок. Если не знаешь — так и скажи.")
    elif "[ПСИ]" in msg_upper:
        hint = ("=== ИНСТРУКЦИЯ ===\n"
                "Игрок применяет психосилу. Сделай психотест 1d100 против "
                "пси-рейтинга или Willpower. При 9 на d10 — Феномен, при "
                "100 — Периллы Варпа. Опиши эффект.")
    if hint:
        parts.append(hint)

    enriched = "\n\n".join(parts)

    giga_messages = [Messages(role=MessagesRole.SYSTEM, content=master_prompt)]
    last_idx = len(st.session_state.chat_history) - 1
    for i, m in enumerate(st.session_state.chat_history):
        role_enum = MessagesRole.USER if m["role"] == "user" else MessagesRole.ASSISTANT
        content = m["content"]
        if i == last_idx and m["role"] == "user":
            content = enriched
        giga_messages.append(Messages(role=role_enum, content=content))

    last_user_msg = next(
        (m.content for m in reversed(giga_messages) if m.role == MessagesRole.USER), "")
    st.session_state.last_request_to_giga = last_user_msg

    with st.chat_message("assistant", avatar=faction_avatar):
        render_chat_name("assistant", player_name)
        rolls_to_render = []; final_text = None
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
                        st.error(f"Ошибка GigaChat: {e2}"); break
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

        state_updates = {}; text_rolls = []
        if final_text:
            final_text, state_updates = parse_state_block(final_text)
            final_text, text_rolls = parse_rolls_from_text(final_text)

        # Автоподстановка брони и лута (patch20)
        last_user = ""
        for m_ in reversed(st.session_state.chat_history):
            if m_.get("role") == "user":
                last_user = m_.get("content", "")
                break

        if not any(k.startswith("armour_") for k in state_updates):
            detected = _detect_armour_zone(last_user)
            if detected:
                zone, action = detected
                state_updates[f"armour_{action}_{zone}"] = "1"

        if not any(k in state_updates for k in ("equipment_add", "weapon_add")):
            last_loot = st.session_state.get("last_loot_seen", "")
            items = _autodetect_loot(last_user, last_loot)
            if items:
                existing = state_updates.get("equipment_add", "")
                all_items = [x for x in existing.split(";") if x.strip()] + items
                seen = set()
                unique = []
                for x in all_items:
                    if x not in seen:
                        seen.add(x)
                        unique.append(x)
                state_updates["equipment_add"] = "; ".join(unique)

        eq_drop, wp_lost = _autodetect_drop(last_user, st.session_state.character)
        if eq_drop and "equipment_remove" not in state_updates:
            state_updates["equipment_remove"] = "; ".join(eq_drop)
        if wp_lost and "weapon_lost" not in state_updates:
            state_updates["weapon_lost"] = "; ".join(wp_lost)

        if "loot_seen" in state_updates:
            st.session_state.last_loot_seen = state_updates["loot_seen"]

        if state_updates:
            old_snap = {
                "w": int(((st.session_state.character.get("wounds") or {}).get("current", 0)) or 0),
                "f": int(((st.session_state.character.get("fate_points") or {}).get("current", 0)) or 0),
                "c": int(st.session_state.character.get("corruption", 0) or 0),
                "i": int(st.session_state.character.get("insanity", 0) or 0),
                "x": int(st.session_state.character.get("xp", 0) or 0),
            }
            st.session_state.character = apply_state_updates(
                st.session_state.character, state_updates)
            try:
                new_path = cc.save_character(st.session_state.character)
                st.session_state.character_path = new_path
            except Exception as e:
                print(f"[STATE] ошибка: {e}")

            new_snap = {
                "w": int(((st.session_state.character.get("wounds") or {}).get("current", 0)) or 0),
                "f": int(((st.session_state.character.get("fate_points") or {}).get("current", 0)) or 0),
                "c": int(st.session_state.character.get("corruption", 0) or 0),
                "i": int(st.session_state.character.get("insanity", 0) or 0),
                "x": int(st.session_state.character.get("xp", 0) or 0),
            }
            toasts = []
            dw = new_snap["w"] - old_snap["w"]
            df = new_snap["f"] - old_snap["f"]
            dc = new_snap["c"] - old_snap["c"]
            di = new_snap["i"] - old_snap["i"]
            dx = new_snap["x"] - old_snap["x"]
            if dw: toasts.append((f"{dw:+d} РАНЫ", "❤️" if dw > 0 else "💔"))
            if df: toasts.append((f"{df:+d} СУДЬБА", "🍀" if df > 0 else "⚠️"))
            if dc: toasts.append((f"{dc:+d} ПОРЧА", "🌀"))
            if di: toasts.append((f"{di:+d} БЕЗУМИЕ", "🧠"))
            if dx: toasts.append((f"{dx:+d} ОПЫТ", "★"))
            for txt, ic in toasts:
                try: st.toast(txt, icon=ic)
                except Exception: pass

            # Карточка лута
            loot_items = []
            for short, lbl, ic in [
                ("quest_add", "НОВАЯ ЗАДАЧА", "📋"),
                ("npc_add", "НОВЫЙ NPC", "👥"),
                ("companion_add", "НОВЫЙ СПУТНИК", "🐾"),
                ("goal_add", "НОВАЯ ЦЕЛЬ", "🎯"),
                ("effect_add", "НОВЫЙ ЭФФЕКТ", "⚡"),
            ]:
                if short in state_updates:
                    for it in str(state_updates[short]).split(";"):
                        it = it.strip()
                        if it:
                            loot_items.append((lbl, it, ic))

            # Инвентарь
            if "equipment_add" in state_updates:
                for it in str(state_updates["equipment_add"]).split(";"):
                    it = it.strip()
                    if it:
                        loot_items.append(("ПОЛУЧЕН ПРЕДМЕТ", it, "📦"))

            # ОБНАРУЖЕНО (не в инвентарь, только всплывает)
            if "loot_seen" in state_updates:
                for it in str(state_updates["loot_seen"]).split(";"):
                    it = it.strip()
                    if it:
                        loot_items.append(("ОБНАРУЖЕНО", it, "👁"))

            # Оружие
            if "weapon_add" in state_updates:
                for it in str(state_updates["weapon_add"]).split(";"):
                    it = it.strip()
                    if not it:
                        continue
                    nm = it.split("|")[0].strip() if "|" in it else it
                    loot_items.append(("ПОЛУЧЕНО ОРУЖИЕ", nm, "⚔"))

            # Особые ресурсы: special_XXX=+N
            for k, v in state_updates.items():
                if k.startswith("special_"):
                    res = k[len("special_"):].strip()
                    try:
                        iv = int(str(v).strip().lstrip("+"))
                    except Exception:
                        iv = 0
                    if iv > 0:
                        loot_items.append(("ОСОБЫЙ РЕСУРС", f"{res} +{iv}", "💎"))

            # Деньги: money=+N
            if "money" in state_updates:
                mv = str(state_updates["money"]).strip()
                if mv.startswith("+"):
                    loot_items.append(("ПОЛУЧЕНО ДЕНЕГ", mv, "💰"))

            for lbl, nm, ic in loot_items:
                st.markdown(
                    f'<div class="loot-card">'
                    f'  <div class="loot-icon">{ic}</div>'
                    f'  <div class="loot-info">'
                    f'    <div class="loot-label">{lbl}</div>'
                    f'    <div class="loot-name">{_esc(nm)}</div>'
                    f'  </div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

            st.session_state.last_state_updates = dict(state_updates)

        all_rolls = _dedupe_rolls(rolls_to_render + text_rolls)
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

    if "theme" not in st.session_state:
        saved = _ls_load_theme(localS) if localS else None
        st.session_state.theme = saved if saved else DEFAULT_THEME

    inject_custom_css(st.session_state.theme)

    if "character" not in st.session_state: st.session_state.character = None
    if "in_wizard" not in st.session_state: st.session_state.in_wizard = False
    if "chat_history" not in st.session_state: st.session_state.chat_history = []
    if "show_last_request" not in st.session_state: st.session_state.show_last_request = False

    if localS and not st.session_state.get("ls_restore_done") and not st.session_state.character:
        attempts = st.session_state.get("ls_attempts", 0)
        if attempts < 4:
            loaded = _ls_load(localS)
            if loaded and loaded.get("character"):
                char = loaded["character"]
                chat = loaded.get("chat_history", [])
                if not chat:
                    try:
                        file_chat = cc.load_chat_history(char.get("name", ""))
                        if file_chat:
                            chat = file_chat
                    except Exception:
                        pass
                st.session_state.character = char
                # Чистка старой истории: выкидываем STATE-мусор из сообщений
                cleaned_chat = []
                for m in chat:
                    if isinstance(m, dict) and m.get("role") == "assistant":
                        cleaned_text, _ = parse_state_block(m.get("content", ""))
                        if cleaned_text and cleaned_text != "_…_":
                            mc = dict(m)
                            mc["content"] = cleaned_text
                            cleaned_chat.append(mc)
                    else:
                        cleaned_chat.append(m)
                st.session_state.chat_history = cleaned_chat
                st.session_state.ls_restore_done = True
            else:
                st.session_state.ls_attempts = attempts + 1
                st.rerun()
        else:
            st.session_state.ls_restore_done = True

    if st.session_state.character:
        render_chat(localS)
    elif st.session_state.in_wizard:
        render_wizard(localS)
    else:
        render_start_screen(localS)


if __name__ == "__main__":
    main()