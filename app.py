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

LS_KEY = "wh40k_rpg_save"
LS_THEME_KEY = "wh40k_theme"
SAVE_FORMAT = "wh40k_rpg_save"
SAVE_VERSION = 1

st.set_page_config(page_title="Warhammer 40K — RPG с ИИ-Мастером", layout="wide")


# ============================================================
# ТЕМЫ — 12 палитр
# ============================================================
THEMES = {
    "default": {
        "label": "🎨 Стандартная",
        "bg_deep": "#0e1117", "bg_mid": "#161a21", "bg_light": "#1e2229",
        "bg_card": "#1c2028", "bg_chat": "#262a33",
        "accent": "#ff4b4b", "accent_dim": "#b83737", "accent_bright": "#ff7a7a",
        "text": "#fafafa", "text_dim": "#a0a4ab", "text_faint": "#6e7179",
        "heading": "#fafafa", "link": "#ff4b4b",
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
# АВАТАРЫ ФРАКЦИЙ — для чата
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


def get_faction_avatar(sheet) -> str:
    """Возвращает emoji-аватар по фракции персонажа."""
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
    height: 0 !important;
    visibility: hidden !important;
}
[data-testid="stToolbar"] { top: 0.5rem !important; right: 0.8rem !important; }
[data-testid="stDecoration"] { display: none !important; }

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
   9. Мобильный
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
}

/* =====================================================
   10. Ультравайд
   ===================================================== */
@media (min-width: 2000px) {
    html { font-size: 19px !important; }
    h1 { font-size: 2.4rem !important; }
    h2 { font-size: 1.8rem !important; }
    h3 { font-size: 1.4rem !important; }
    .block-container { max-width: 1800px !important; }
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
    background: rgba(128,128,128,0.15);
    color: var(--accent-bright) !important;
    padding: 1px 5px;
    border-radius: 3px;
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

/* === КНОПКИ === */
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
[data-testid="stExpander"] summary {
    color: var(--accent) !important;
    font-weight: 600 !important;
    font-size: clamp(0.95rem, 0.9rem + 0.15vw, 1.1rem) !important;
    text-transform: uppercase;
    letter-spacing: 0.08em;
}
[data-testid="stExpander"] summary p {
    color: var(--accent) !important;
    font-weight: 600 !important;
    font-size: clamp(0.95rem, 0.9rem + 0.15vw, 1.1rem) !important;
}
[data-testid="stExpander"] [data-testid="stExpanderDetails"] {
    background: var(--bg-mid) !important;
}
[data-testid="stExpander"] [data-testid="stExpanderDetails"] p,
[data-testid="stExpander"] [data-testid="stExpanderDetails"] li {
    color: var(--ink) !important;
}

/* === CHAT MESSAGE — роль-зависимый стиль (ПАКЕТ 1) === */
[data-testid="stChatMessage"] {
    background: var(--bg-chat) !important;
    border: 1px solid var(--accent-dim) !important;
    border-radius: 6px;
    padding: 16px 20px !important;
    margin-bottom: 14px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.35);
    transition: box-shadow 0.2s ease;
}

/* Мастер — левая акцентная полоса */
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

/* Игрок — правая акцентная полоса */
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

/* Метка роли над репликой */
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

/* === CHAT INPUT — усиленные селекторы === */
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

/* === ALERTS (используются для бросков) === */
[data-testid="stAlert"] { border-radius: 6px; border-left-width: 5px !important; }
[data-testid="stAlert"] * { font-size: clamp(0.9rem, 0.85rem + 0.1vw, 1.05rem) !important; }
[data-testid="stAlert"][kind="success"] * { color: #0a2e0a !important; }
[data-testid="stAlert"][kind="error"] * { color: #2e0a0a !important; }
[data-testid="stAlert"][kind="info"] * { color: #0a1a2e !important; }
[data-testid="stAlert"][kind="warning"] * { color: #2e220a !important; }

/* === TEXT INPUT / TEXTAREA === */
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

/* === SELECTBOX === */
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

/* === СЛАЙДЕРЫ === */
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

/* === RADIO / CHECKBOX === */
[data-testid="stRadio"] label p,
[data-testid="stRadio"] label * { color: var(--ink) !important; }
[data-testid="stCheckbox"] label p,
[data-testid="stCheckbox"] label * { color: var(--ink) !important; }

/* === FILE UPLOADER === */
[data-testid="stFileUploader"] section,
[data-testid="stFileUploaderDropzone"] {
    background: color-mix(in srgb, var(--bg-mid) 80%, transparent) !important;
    border: 1px dashed var(--accent-dim) !important;
    border-radius: 4px !important;
}
[data-testid="stFileUploader"] section *,
[data-testid="stFileUploaderDropzone"] * { color: var(--ink) !important; }

/* === PROGRESS === */
[data-testid="stProgress"] > div > div > div {
    background: linear-gradient(90deg, var(--accent-dim), var(--accent)) !important;
}

/* === SCROLLBAR === */
::-webkit-scrollbar { width: 10px; height: 10px; }
::-webkit-scrollbar-track { background: var(--bg-deep); }
::-webkit-scrollbar-thumb { background: var(--accent-dim); border-radius: 5px; }
::-webkit-scrollbar-thumb:hover { background: var(--accent); }

/* === LINKS / HR === */
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


@st.cache_data
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
        key = key.strip(); value = value.strip()
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
    if reason: header += f" ({reason})"
    header += ": "
    roll1 = rolls[0] if rolls else total
    detail = f"выпало [{roll1}] + {mod} = {total}" if mod else f"выпало [{roll1}]"
    if "1d100" in expr.lower() and difficulty > 0 and success is not None:
        if success:
            detail += f" — ✅ УСПЕХ (сложность {difficulty}, степеней успеха: {margin})"
        else:
            detail += f" — ❌ ПРОВАЛ (сложность {difficulty}, степеней провала: {margin})"
    return header + detail


def render_roll(r: dict):
    if not isinstance(r, dict):
        st.warning(f"Некорректный результат броска: {r}"); return
    if "error" in r:
        st.error(f"Ошибка броска: {r['error']}"); return
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
    chat_history.append({"role": "user", "content": f"[ДЕЙСТВИЕ] {msg}", "rolls": []})
    cc.save_chat_history(sheet.get("name", "unnamed"), chat_history)
    cc.save_character(sheet)
    _ls_save(localS, sheet, chat_history)


# ============================================================
# ПЕРЕКЛЮЧАТЕЛЬ ТЕМЫ
# ============================================================
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
    """Метка роли над репликой: точка + имя."""
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
# ВСТРОЕННЫЙ ЛИСТ ПЕРСОНАЖА
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
# САЙДБАР
# ============================================================
def _render_quick_actions(sheet, chat_history, localS):
    st.markdown("**⚡ Действия**")
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

    tabs = st.tabs(["Перс", "Инвент", "Мир", "Корабль", "Заметки"])

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
                    st.session_state.chat_history = data.get("chat_history", [])
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
    st.title("🎲 Игра")

    with st.expander("👤 Лист персонажа", expanded=False):
        render_character_inline(st.session_state.character, kb, localS,
                                st.session_state.chat_history)

    # Аватар фракции + имя игрока
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

    # Отрисовка истории с метками роли
    for msg in st.session_state.chat_history:
        role = msg["role"]
        avatar = AVATAR_USER if role == "user" else faction_avatar
        with st.chat_message(role, avatar=avatar):
            render_chat_name(role, player_name)
            for r in msg.get("rolls", []):
                render_roll(r)
            st.markdown(msg["content"])

    user_input = st.chat_input("Что делаешь?")
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
                st.session_state.chat_history = chat
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