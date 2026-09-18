"""Генератор CSS для выбранной темы.

Принципы:
  - Цвета — только через CSS-переменные на :root (--bg-deep и т.д.).
  - Никакого хардкода цветов в правилах: только var(...).
  - Текстуры/границы/свечения — через DECOR-пресет темы.
  - Два <style> блока: vars и layout. Vars перезаписывается при смене
    темы — новый блок с тем же id идёт позже, браузер берёт последнее.
"""

from __future__ import annotations

import streamlit as st

from ui_themes import DEFAULT_THEME, get_decor, get_theme

# ------------------------------------------------------------
# 1. Корневой блок переменных
# ------------------------------------------------------------

def _build_vars(theme: dict, decor: dict) -> str:
    p = theme["palette"]
    return f"""
<style id="wh40k-vars">
:root {{
    --bg-deep: {p["bg_deep"]};
    --bg-mid: {p["bg_mid"]};
    --bg-light: {p["bg_light"]};
    --bg-card: {p["bg_card"]};
    --bg-chat: {p["bg_chat"]};
    --bg-hover: {p["bg_hover"]};

    --ink: {p["text"]};
    --ink-dim: {p["text_dim"]};
    --ink-faint: {p["text_faint"]};
    --heading: {p["heading"]};
    --link: {p["link"]};

    --accent: {p["accent"]};
    --accent-dim: {p["accent_dim"]};
    --accent-bright: {p["accent_bright"]};
    --accent-glow: {p["accent_glow"]};

    --ok: {p["success"]};
    --warn: {p["warning"]};
    --bad: {p["danger"]};
    --border: {p["border"]};
    --border-strong: {p["border_strong"]};

    --font-head: Georgia, "Times New Roman", serif;
    --font-emoji: "Segoe UI Emoji", "Apple Color Emoji", "Noto Color Emoji", "Segoe UI Symbol", sans-serif;
    --font-body: Georgia, "Times New Roman", serif;

    --glow-strength: {decor["glow_strength"]};
    --texture: {decor["texture"]};
    --texture-size: {decor["texture_size"]};
}}
</style>
"""


# ------------------------------------------------------------
# 2. Уголки — форма через clip-path в зависимости от decor
# ------------------------------------------------------------

_CORNERS = {
    "none":    "none",
    "notch":   "polygon(14px 0, 100% 0, 100% calc(100% - 14px), calc(100% - 14px) 100%, 0 100%, 0 14px)",
    "relic":   "polygon(22px 0, 100% 0, 100% calc(100% - 22px), calc(100% - 22px) 100%, 0 100%, 0 22px)",
    "organic": "polygon(28px 0, 100% 0, 100% calc(100% - 28px), calc(100% - 28px) 100%, 0 100%, 0 28px)",
}

_BORDER = {
    "solid":  "1px solid var(--border)",
    "double": "3px double var(--border)",
    "ornate": "1px solid var(--border-strong)",
    "dashed": "1px dashed var(--border)",
}

_ANIM_HERO = {
    "none":   "none",
    "glow":   "hero-glow 5s ease-in-out infinite",
    "pulse":  "hero-pulse 4s ease-in-out infinite",
    "flicker":"hero-flicker 6s linear infinite",
}


def _build_layout(theme: dict, decor: dict) -> str:
    corners = _CORNERS.get(decor["corners"], _CORNERS["notch"])
    border = _BORDER.get(decor["border_style"], _BORDER["solid"])
    hero_anim = _ANIM_HERO.get(decor["animation"], "none")

    return f"""
<style id="wh40k-layout">
@keyframes fade-in     {{ from {{opacity:0}} to {{opacity:1}} }}
@keyframes slide-up    {{ from {{opacity:0;transform:translateY(18px)}} to {{opacity:1;transform:translateY(0)}} }}
@keyframes slide-right {{ from {{opacity:0;transform:translateX(-20px)}} to {{opacity:1;transform:translateX(0)}} }}
@keyframes glow-pulse  {{ 0%,100%{{filter:brightness(1)}} 50%{{filter:brightness(1.14)}} }}
@keyframes hero-glow   {{
    0%,100% {{ box-shadow: 0 0 30px var(--accent-glow), 0 4px 24px rgba(0,0,0,.5); }}
    50%     {{ box-shadow: 0 0 55px var(--accent-glow), 0 6px 32px rgba(0,0,0,.6); }}
}}
@keyframes hero-pulse  {{
    0%,100% {{ transform: scale(1); }}
    50%     {{ transform: scale(1.005); }}
}}
@keyframes hero-flicker {{
    0%,19%,21%,23%,25%,54%,56%,100% {{ opacity:1; }}
    20%,24%,55% {{ opacity:.92; }}
}}
@keyframes roll-in     {{ from {{opacity:0;transform:translateY(12px) scale(.96)}} to {{opacity:1;transform:translateY(0) scale(1)}} }}
@keyframes roll-shake  {{ 0%,100%{{transform:rotate(0)}} 25%{{transform:rotate(-1.2deg)}} 75%{{transform:rotate(1.2deg)}} }}
@keyframes pulse-wounds {{
    0%,100% {{ box-shadow: 0 0 8px rgba(220,50,50,.7); }}
    50%     {{ box-shadow: 0 0 22px rgba(255,60,60,1), 0 0 36px rgba(255,60,60,.5); }}
}}

/* === ФОН === */
.stApp {{
    background-color: var(--bg-deep) !important;
    color: var(--ink) !important;
    background-image: var(--texture) !important;
    background-size: var(--texture-size) !important;
    background-attachment: fixed !important;
}}
[data-testid="stBottom"], [data-testid="stBottomBlockContainer"] {{
    background: var(--bg-deep) !important;
    border-top: 1px solid var(--border) !important;
}}

/* === ШРИФТЫ === */
h1, h2, h3, h4, h5, h6, .hero-panel .hero-title, .section-header .title {{
    font-family: var(--font-head) !important;
    color: var(--heading) !important;
    letter-spacing: .12em !important;
    font-weight: 700;
}}
h1 {{ font-size: clamp(1.8rem, 1.5rem + 1vw, 2.6rem) !important;
     border-bottom: 1px solid var(--border) !important;
     padding-bottom: .4rem;
     text-shadow: 0 0 30px var(--accent-glow); }}
h2 {{ font-size: clamp(1.35rem, 1.1rem + .6vw, 1.9rem) !important; color: var(--accent) !important; }}
h3 {{ font-size: clamp(1.15rem, 1rem + .4vw, 1.5rem) !important; color: var(--accent) !important; }}

.stMarkdown p, .stMarkdown li,
[data-testid="stChatMessage"] p,
[data-testid="stChatMessage"] li {{
    font-family: var(--font-body) !important;
    color: var(--ink) !important;
    font-size: clamp(1.05rem, 1rem + .3vw, 1.22rem) !important;
    line-height: 1.7 !important;
}}
.stMarkdown strong, .stMarkdown b,
[data-testid="stChatMessage"] strong,
[data-testid="stChatMessage"] b {{ color: var(--accent-bright) !important; font-weight: 700; }}
.stMarkdown em, .stMarkdown i,
[data-testid="stChatMessage"] em,
[data-testid="stChatMessage"] i {{ color: var(--ink-dim) !important; }}
.stMarkdown a {{ color: var(--link) !important; }}
.stMarkdown a:hover {{ color: var(--accent-bright) !important; }}
.stMarkdown code {{
    background: color-mix(in srgb, var(--bg-deep) 82%, var(--accent) 18%);
    color: var(--accent-bright) !important;
    padding: 2px 7px; border-radius: 3px;
    border: 1px solid color-mix(in srgb, var(--accent) 35%, transparent);
    font-family: 'Consolas', monospace; font-size: .92em;
}}

/* === SIDEBAR === */
[data-testid="stSidebar"] {{
    background: var(--bg-mid) !important;
    border-right: 1px solid var(--border) !important;
    background-image:
        linear-gradient(color-mix(in srgb, var(--accent) 3%, transparent) 1px, transparent 1px),
        linear-gradient(90deg, color-mix(in srgb, var(--accent) 3%, transparent) 1px, transparent 1px) !important;
    background-size: 30px 30px, 30px 30px !important;
}}
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {{ color: var(--accent) !important; }}
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] small,
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] > * {{ color: var(--ink) !important; }}
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] * {{ color: var(--ink-dim) !important; }}

/* === КНОПКИ === */
.stButton > button,
[data-testid="stBaseButton-secondary"],
[data-testid="stBaseButton-primary"] {{
    background: var(--bg-light) !important;
    color: var(--accent-bright) !important;
    border: {border} !important;
    border-radius: 0;
    clip-path: {corners};
    font-family: var(--font-head) !important;
    letter-spacing: 0;
    font-weight: 600 !important;
    text-transform: none;
    font-size: clamp(.88rem, .84rem + .1vw, 1rem) !important;
    transition: color .18s ease, border-color .18s ease, box-shadow .18s ease, background .18s ease;
    box-shadow: 0 0 0 3px color-mix(in srgb, var(--accent) 5%, transparent) !important;
}}
.stButton > button:hover,
[data-testid="stBaseButton-secondary"]:hover {{
    border-color: var(--accent) !important;
    box-shadow:
        0 0 0 3px color-mix(in srgb, var(--accent) 18%, transparent),
        0 0 22px var(--accent-glow),
        0 0 44px color-mix(in srgb, var(--accent) 22%, transparent) !important;
}}
[data-testid="stBaseButton-primary"] {{
    background: linear-gradient(180deg, var(--accent-dim), var(--accent-dim)) !important;
    border-color: var(--accent) !important;
    color: #ffffff !important;
}}
[data-testid="stBaseButton-primary"]:hover {{
    background: var(--accent) !important;
    box-shadow: 0 0 22px var(--accent-glow), 0 0 44px color-mix(in srgb, var(--accent) 35%, transparent) !important;
}}

/* === ВКЛАДКИ === */
.stTabs [data-baseweb="tab-list"] {{ border-bottom: 1px solid var(--border); gap: 4px; }}
.stTabs [data-baseweb="tab"] {{
    color: var(--ink-dim) !important;
    background: transparent !important;
    font-family: var(--font-head) !important;
    padding: 8px 12px;
    font-weight: 600;
    text-transform: none;
    letter-spacing: 0;
}}
.stTabs [data-baseweb="tab"]:hover {{ color: var(--accent-bright) !important; }}
.stTabs [aria-selected="true"] {{
    color: var(--accent-bright) !important;
    border-bottom: 2px solid var(--accent) !important;
    text-shadow: 0 0 14px var(--accent-glow);
}}
.stTabs [data-baseweb="tab-highlight"] {{ background-color: var(--accent) !important; }}

/* === EXPANDER === */
[data-testid="stExpander"] {{
    border: {border} !important;
    background: var(--bg-card) !important;
    clip-path: {corners};
    padding: 6px 10px;
    transition: box-shadow .22s ease;
}}
[data-testid="stExpander"]:hover {{
    box-shadow: 0 0 0 1px var(--accent), 0 0 18px var(--accent-glow);
}}
[data-testid="stExpander"] summary,
[data-testid="stExpander"] summary *,
[data-testid="stExpander"] [data-testid="stExpanderHeader"],
[data-testid="stExpander"] [data-testid="stExpanderHeader"] * {{
    color: var(--accent) !important;
    fill: var(--accent) !important;
    font-family: var(--font-head) !important;
    text-transform: none;
    letter-spacing: 0;
    font-weight: 700 !important;
}}

/* === ЧАТ === */
[data-testid="stChatMessage"] {{
    background: var(--bg-chat) !important;
    border: 1px solid var(--border) !important;
    padding: 16px 20px !important;
    margin-bottom: 14px;
    box-shadow: 0 2px 8px rgba(0,0,0,.35);
    animation: slide-up .45s cubic-bezier(.2,.8,.3,1) both;
    position: relative;
}}
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) {{
    border-left: 3px solid var(--accent) !important;
    background: linear-gradient(90deg,
        color-mix(in srgb, var(--bg-chat) 92%, var(--accent) 8%),
        var(--bg-chat)) !important;
}}
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"])::before {{
    content: ''; position: absolute;
    top: 8px; bottom: 8px; left: 0; width: 2px;
    background: linear-gradient(180deg, transparent, var(--accent) 20%,
        var(--accent-bright) 50%, var(--accent) 80%, transparent);
    box-shadow: 0 0 12px var(--accent);
}}
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {{
    border-right: 3px solid var(--accent-bright) !important;
}}

/* === METRIC === */
[data-testid="stMetric"] {{
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    padding: 10px 14px !important;
    background-image: linear-gradient(135deg,
        color-mix(in srgb, var(--accent) 6%, transparent), transparent 60%) !important;
    transition: box-shadow .22s ease;
}}
[data-testid="stMetric"]:hover {{
    box-shadow: 0 0 0 1px var(--accent), 0 0 16px var(--accent-glow);
}}
[data-testid="stMetricLabel"] > div,
[data-testid="stMetricLabel"] > div > div {{
    color: var(--accent) !important;
    font-family: var(--font-head) !important;
    text-transform: none;
    letter-spacing: 0;
    font-size: clamp(.72rem, .7rem + .1vw, .85rem) !important;
    font-weight: 600 !important;
}}
[data-testid="stMetricValue"] > div,
[data-testid="stMetricValue"] > div > div {{
    color: var(--accent-bright) !important;
    font-weight: 700 !important;
    font-size: clamp(1.3rem, 1.1rem + .6vw, 1.9rem) !important;
}}

/* === HERO PANEL === */
.hero-panel {{
    position: relative;
    padding: 28px 36px 26px;
    background: linear-gradient(135deg,
        color-mix(in srgb, var(--bg-light) 88%, var(--accent) 12%),
        var(--bg-card));
    border: {border};
    clip-path: {corners};
    box-shadow: 0 0 30px var(--accent-glow), 0 4px 24px rgba(0,0,0,.5);
    animation: {hero_anim}, slide-up .7s ease both;
    margin-bottom: 16px;
}}
.hero-panel::before, .hero-panel::after {{
    content: ''; position: absolute;
    width: 14px; height: 14px;
    background: radial-gradient(circle,
        var(--accent-bright) 15%,
        var(--accent-dim) 65%, transparent 100%);
    border-radius: 50%;
    box-shadow: 0 0 10px var(--accent);
}}
.hero-panel::before {{ top: 10px; left: 10px; }}
.hero-panel::after  {{ top: 10px; right: 10px; }}
.hero-panel .hero-title {{
    font-family: var(--font-head) !important;
    font-size: clamp(1.5rem, 1.15rem + 1.6vw, 2.6rem);
    font-weight: 700;
    color: var(--accent-bright);
    margin: 0 0 8px 0;
    text-shadow: 0 0 20px var(--accent-glow);
    letter-spacing: 0;
}}
.hero-panel .hero-sub {{
    font-family: var(--font-head);
    font-size: clamp(.78rem, .74rem + .2vw, .95rem);
    color: var(--ink-dim);
    letter-spacing: 0;
    text-transform: none;
    display: flex; align-items: center; gap: 14px;
}}
.hero-panel .hero-sub .line {{
    flex: 1; height: 1px; max-width: 200px;
    background: linear-gradient(90deg, transparent, var(--border), transparent);
}}

/* === SECTION HEADER === */
.section-header {{
    display: flex; align-items: center; gap: 14px;
    margin: 22px 0 12px;
    font-family: var(--font-head);
    animation: slide-right .55s ease both;
}}
.section-header .num {{
    display: inline-block; padding: 3px 10px;
    border: 1px solid var(--accent);
    color: var(--accent);
    font-weight: 700;
    background: color-mix(in srgb, var(--accent) 8%, transparent);
    box-shadow: 0 0 10px var(--accent-glow);
}}
.section-header .title {{
    color: var(--heading);
    font-weight: 700;
    font-size: clamp(.95rem, .88rem + .3vw, 1.15rem);
    letter-spacing: 0;
    text-transform: none;
}}
.section-header .line {{
    flex: 1; height: 1px;
    background: linear-gradient(90deg, var(--border), transparent 80%);
}}
.section-header .meta {{
    color: var(--accent-dim);
    font-size: clamp(.72rem, .7rem + .1vw, .85rem);
    letter-spacing: 0;
    text-transform: none;
}}

/* === ROLL CARD === */
.roll-card {{
    position: relative;
    margin: 12px 0 16px;
    padding: 16px 24px 18px;
    background: var(--bg-card);
    border: 1px solid var(--border-strong);
    clip-path: {corners};
    font-family: 'Consolas','Menlo',monospace;
    color: var(--accent);
    animation: roll-in .5s cubic-bezier(.2,.8,.3,1) both,
               roll-shake .6s ease-in-out .25s 2,
               glow-pulse 2.5s ease-in-out .6s infinite;
}}
.roll-card--success {{ color: var(--ok); border-color: color-mix(in srgb, var(--ok) 55%, transparent);
    background: linear-gradient(135deg,
        color-mix(in srgb, var(--ok) 14%, transparent),
        var(--bg-card));
    box-shadow: 0 0 22px color-mix(in srgb, var(--ok) 30%, transparent);
}}
.roll-card--fail {{ color: var(--bad); border-color: color-mix(in srgb, var(--bad) 55%, transparent);
    background: linear-gradient(135deg,
        color-mix(in srgb, var(--bad) 14%, transparent),
        var(--bg-card));
    box-shadow: 0 0 22px color-mix(in srgb, var(--bad) 30%, transparent);
}}
.roll-card--info {{ color: var(--accent); border-color: var(--border-strong); }}
.roll-header {{ display: flex; gap: 12px; align-items: center;
    font-size: .72rem; letter-spacing: 0; text-transform: none;
    padding-bottom: 8px; margin-bottom: 14px;
    border-bottom: 1px solid color-mix(in srgb, currentColor 30%, transparent);
}}
.roll-expr {{ font-weight: 700; text-shadow: 0 0 10px currentColor; }}
.roll-reason {{ font-style: italic; opacity: .7; margin-left: auto;
    text-transform: none; letter-spacing: 0; font-size: .82rem; }}
.roll-body {{ display: flex; justify-content: center; align-items: center; gap: 30px; padding: 4px 0 12px; }}
.roll-value-num {{ font-size: clamp(2.6rem, 2rem + 2.2vw, 4.2rem); font-weight: 700;
    line-height: 1; color: currentColor; text-shadow: 0 0 26px currentColor; }}
.roll-value-label {{ font-size: .68rem; letter-spacing: 0; opacity: .7;
    margin-top: 6px; text-transform: none; text-align: center; }}
.roll-mod {{ font-size: 1.6rem; font-weight: 700;
    padding: 4px 14px;
    border-left: 1px solid color-mix(in srgb, currentColor 50%, transparent);
    border-right: 1px solid color-mix(in srgb, currentColor 50%, transparent); }}
.roll-meta {{ display: flex; justify-content: center; gap: 40px; padding: 10px 0 6px;
    border-top: 1px solid color-mix(in srgb, currentColor 22%, transparent); }}
.roll-meta-item {{ display: flex; flex-direction: column; align-items: center; gap: 3px; }}
.roll-meta-item .label {{ font-size: .66rem; letter-spacing: 0;
    opacity: .65; text-transform: none; }}
.roll-meta-item .value {{ font-size: 1.35rem; font-weight: 700; text-shadow: 0 0 12px currentColor; }}
.roll-status {{ display: flex; justify-content: center; gap: 12px;
    margin-top: 10px; padding: 8px 0 2px;
    font-size: .88rem; font-weight: 700; letter-spacing: 0;
    text-transform: none; text-shadow: 0 0 16px currentColor; }}

/* === STAT BARS === */
.stat-bar {{ margin: 8px 0; }}
.stat-bar-head {{ display: flex; justify-content: space-between;
    font-family: 'Consolas', monospace; font-size: .72rem;
    letter-spacing: 0; text-transform: none; margin-bottom: 4px; }}
.stat-bar-label {{ color: var(--ink-dim); }}
.stat-bar-value {{ color: var(--accent-bright); font-weight: 700; }}
.stat-bar-track {{ height: 8px; background: color-mix(in srgb, var(--accent-dim) 18%, transparent);
    border: 1px solid var(--border); overflow: hidden; }}
.stat-bar-fill {{ height: 100%; transition: width .4s ease; }}
.stat-bar--wounds .stat-bar-fill {{ background: linear-gradient(90deg, #6b1a1a, #d33);
    box-shadow: 0 0 8px rgba(220,50,50,.6); }}
.stat-bar--fate .stat-bar-fill {{ background: linear-gradient(90deg, var(--accent-dim), var(--accent));
    box-shadow: 0 0 8px var(--accent-glow); }}
.stat-bar--corruption .stat-bar-fill {{ background: linear-gradient(90deg, #4a1a6b, #9c5cff); }}
.stat-bar--insanity .stat-bar-fill {{ background: linear-gradient(90deg, #6b4a1a, #d4913a); }}
.stat-bar--xp .stat-bar-fill {{ background: linear-gradient(90deg,
    color-mix(in srgb, var(--accent) 60%, #4fc3f7), var(--accent-bright)); }}
.stat-bar--wounds.stat-bar--low .stat-bar-fill {{
    animation: pulse-wounds 1.4s ease-in-out infinite;
    background: linear-gradient(90deg, #ff1818, #ff6868) !important;
}}

/* === SIDEBAR ELEMENTS === */
.char-sheet-header {{ display: flex; align-items: center; gap: 12px;
    padding-bottom: 12px; margin-bottom: 10px; border-bottom: 1px solid var(--border); }}
.char-avatar {{ width: 52px; height: 52px; border-radius: 50%;
    border: 2px solid var(--accent);
    background: color-mix(in srgb, var(--accent-dim) 30%, transparent);
    display: flex; align-items: center; justify-content: center;
    font-size: 26px; flex-shrink: 0;
    box-shadow: 0 0 14px var(--accent-glow), inset 0 0 10px color-mix(in srgb, var(--accent) 15%, transparent); }}
.char-sheet-name {{ font-family: var(--font-head); font-size: 1rem; font-weight: 700;
    color: var(--accent-bright); margin: 0 0 3px; line-height: 1.1; }}
.char-sheet-sub {{ font-family: 'Consolas', monospace; font-size: .66rem;
    letter-spacing: 0; text-transform: none; color: var(--ink-dim); }}
.sidebar-divider {{ height: 1px; margin: 14px 0;
    background: linear-gradient(90deg, transparent, var(--accent), transparent);
    box-shadow: 0 0 8px var(--accent-glow); }}
.sidebar-section-title {{ font-family: 'Consolas', monospace; font-size: .74rem;
    letter-spacing: 0; color: var(--accent) !important;
    text-transform: none; margin: 12px 0 8px; padding-bottom: 5px;
    border-bottom: 1px solid var(--border); font-weight: 700; }}

.meta-grid {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 6px; margin: 12px 0; }}
.meta-tile {{ background: var(--bg-card); border: 1px solid var(--border);
    padding: 10px 6px 9px; text-align: center; font-family: 'Consolas', monospace; }}
.meta-tile .icon {{ font-size: 1rem; }}
.meta-tile .label {{ font-size: .66rem; letter-spacing: 0;
    text-transform: none; color: var(--accent) !important; margin: 4px 0 5px; }}
.meta-tile .value {{ font-size: 1.15rem; font-weight: 700; color: var(--accent-bright); }}

.attr-grid {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 7px; margin: 10px 0 14px; }}
.attr-tile {{ background: color-mix(in srgb, var(--bg-card) 88%, transparent);
    border: 1px solid var(--border); padding: 10px 6px 9px; text-align: center;
    font-family: 'Consolas', monospace; transition: color .18s ease, border-color .18s ease, box-shadow .18s ease, background .18s ease; }}
.attr-tile:hover {{ border-color: var(--accent); background: color-mix(in srgb, var(--bg-card) 78%, var(--accent) 8%);
    box-shadow: 0 0 12px var(--accent-glow); }}
.attr-tile .attr-key {{ font-size: .72rem; letter-spacing: 0;
    color: var(--accent) !important; text-transform: none; font-weight: 700; }}
.attr-tile .attr-val {{ font-size: 1.4rem; font-weight: 700; color: var(--ink);
    margin: 5px 0 3px; line-height: 1; }}
.attr-tile .attr-bon {{ font-size: .85rem; color: var(--accent-bright); font-weight: 600; }}

/* === LOCATION BAR === */
.location-bar {{ display: flex; align-items: center; flex-wrap: wrap; gap: 10px;
    padding: 10px 40px; margin: 0 0 18px;
    background: linear-gradient(90deg,
        color-mix(in srgb, var(--accent) 14%, transparent), transparent 65%);
    border-left: 3px solid var(--accent);
    border-top: 1px solid color-mix(in srgb, var(--accent) 22%, transparent);
    border-bottom: 1px solid color-mix(in srgb, var(--accent) 22%, transparent);
    font-family: 'Consolas', monospace;
    font-size: clamp(.78rem, .74rem + .2vw, .92rem);
    color: var(--accent-bright); letter-spacing: 0; text-transform: none;
    position: relative; box-shadow: 0 0 18px var(--accent-glow);
}}
.location-bar::before, .location-bar::after {{
    content: '\\2022\\2022\\2022';
    position: absolute; top: 50%; transform: none;
    color: var(--accent); opacity: .5; letter-spacing: 0; font-size: .7rem;
}}
.location-bar::before {{ left: 12px; }}
.location-bar::after  {{ right: 12px; }}
.location-bar .lbl {{ color: var(--accent); font-weight: 700; }}
.location-bar .dot {{ color: var(--accent-dim); }}

/* === TERMINAL STATUS === */
.terminal-status {{ display: flex; justify-content: space-between; align-items: center;
    padding: 8px 16px; margin-bottom: 18px;
    font-family: 'Consolas', monospace; font-size: clamp(.68rem, .66rem + .1vw, .78rem);
    color: var(--accent-dim); letter-spacing: 0; text-transform: none;
    border-top: 1px solid var(--border); border-bottom: 1px solid var(--border);
    background: linear-gradient(90deg, transparent,
        color-mix(in srgb, var(--accent) 8%, transparent) 50%, transparent);
}}

/* === CHAT NAME === */
.chat-name {{ display: flex; align-items: center; gap: 10px;
    font-family: 'Consolas', monospace; font-size: .72rem;
    letter-spacing: 0; text-transform: none;
    margin-bottom: 8px; padding-bottom: 6px;
    border-bottom: 1px solid color-mix(in srgb, var(--accent) 25%, transparent); }}
.chat-name--master {{ color: var(--accent); }}
.chat-name--user {{ color: var(--accent-bright); }}
.chat-name-dot {{ display: inline-block; width: 6px; height: 6px; border-radius: 50%;
    background: currentColor; box-shadow: 0 0 8px currentColor; }}

/* === CHAT INPUT === */
[data-testid="stChatInput"],
[data-testid="stChatInput"] > div,
[data-testid="stChatInput"] > div > div,
.stChatInput, .stChatInputContainer,
.stChatInputContainer > div {{
    background: var(--bg-light) !important;
    border-color: var(--border) !important;
}}
[data-testid="stChatInput"] textarea,
textarea[data-testid="stChatInputTextArea"] {{
    background: transparent !important;
    color: var(--ink) !important;
    -webkit-text-fill-color: var(--ink) !important;
    caret-color: var(--accent) !important;
    font-family: var(--font-body) !important;
    font-size: 1.05rem !important;
}}
[data-testid="stChatInput"] textarea::placeholder {{
    color: var(--ink-faint) !important;
    -webkit-text-fill-color: var(--ink-faint) !important;
    opacity: 1 !important; font-style: italic;
}}
[data-testid="stChatInput"]:focus-within,
.stChatInput:focus-within {{
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 1px var(--accent), 0 0 20px var(--accent-glow) !important;
}}

/* === ПРОЧЕЕ === */
[data-testid="stAlert"] {{ border-left-width: 5px !important; }}
hr {{ border-color: var(--border) !important; margin: 14px 0 !important; }}

::-webkit-scrollbar {{ width: 12px; height: 12px; }}
::-webkit-scrollbar-track {{ background: color-mix(in srgb, var(--bg-deep) 80%, black 20%); }}
::-webkit-scrollbar-thumb {{
    background: linear-gradient(180deg, var(--accent), var(--accent-dim));
    border: 1px solid color-mix(in srgb, var(--accent-bright) 50%, transparent);
    box-shadow: 0 0 8px var(--accent-glow);
}}
::-webkit-scrollbar-thumb:hover {{
    background: linear-gradient(180deg, var(--accent-bright), var(--accent));
    box-shadow: 0 0 14px color-mix(in srgb, var(--accent) 80%, transparent);
}}

@media (max-width: 768px) {{
    .block-container {{ padding-left: .5rem !important; padding-right: .5rem !important; }}
    h1 {{ font-size: 1.6rem !important; }}
    .hero-panel {{ padding: 18px 20px !important; }}
    .roll-value-num {{ font-size: 2.4rem; }}
    .roll-body {{ gap: 16px; }}
}}
</style>
"""


# ------------------------------------------------------------
# 3. Публичная функция
# ------------------------------------------------------------

def render_theme(theme_key: str) -> None:
    """Вставляет CSS выбранной темы. Сначала vars, потом layout.

    При смене темы vars перезаписываются (тот же id в DOM — берётся последний),
    layout идентичен по структуре и просто использует новые значения.
    """
    theme = get_theme(theme_key)
    decor = get_decor(theme)

    # Шрифты одним @import

    st.markdown(_build_vars(theme, decor), unsafe_allow_html=True)
    st.markdown(_build_layout(theme, decor), unsafe_allow_html=True)
    st.markdown(SIDEBAR_FIX_CSS, unsafe_allow_html=True)
    _inject_ghost_kill()
    _inject_sidebar_fix_v2()
    _inject_sidebar_line_fix()
    _inject_visual_pro()


def render_theme_selector_css() -> str:
    """Возвращает inline-стиль для selectbox с темами (на будущее)."""
    return ""

# ============================================================
# SIDEBAR_FIX_CSS — исправление наезда кнопок и контрастности
# ============================================================
SIDEBAR_FIX_CSS = """
<style>
[data-testid="stSidebar"] .stButton > button {
    min-height: 38px !important;
    height: auto !important;
    padding: 8px 12px !important;
    line-height: 1.25 !important;
    white-space: normal !important;
    overflow: visible !important;
    text-overflow: clip !important;
    display: block !important;
    width: 100% !important;
    text-align: left !important;
    font-family: var(--font-head) !important;
    font-size: .85rem !important;
    letter-spacing: .05em !important;
}
[data-testid="stSidebar"] .stButton {
    margin-bottom: 6px !important;
}
[data-testid="stSidebar"] .stButton > button p,
[data-testid="stSidebar"] .stButton > button span {
    white-space: normal !important;
    overflow: visible !important;
    word-break: normal !important;
    line-height: 1.25 !important;
    font-size: inherit !important;
}
[data-testid="stSidebar"] .stTabs [data-baseweb="tab-list"] {
    flex-wrap: wrap !important;
    gap: 4px !important;
    overflow: visible !important;
}
[data-testid="stSidebar"] .stTabs [data-baseweb="tab"] {
    padding: 6px 10px !important;
    font-size: .78rem !important;
    min-width: auto !important;
}
[data-testid="stSidebar"] [data-testid="stExpander"] summary {
    padding: 10px 12px !important;
    font-size: .88rem !important;
    line-height: 1.3 !important;
    white-space: normal !important;
}
[data-testid="stSidebar"] [data-testid="stExpander"] summary * {
    white-space: normal !important;
    overflow: visible !important;
    word-break: normal !important;
}
[data-testid="stSidebar"] .stMarkdown p,
[data-testid="stSidebar"] .stMarkdown li {
    font-size: .92rem !important;
    line-height: 1.5 !important;
}
</style>
"""

# patch25: visual boost
_VISUAL_PRO_CSS = """
<style>
/* Тени и подсветка карточек */
[data-testid="stChatMessage"] {
    box-shadow:
        0 4px 16px rgba(0,0,0,.5),
        0 0 0 1px color-mix(in srgb, var(--accent) 12%, transparent),
        inset 0 1px 0 color-mix(in srgb, var(--accent) 15%, transparent) !important;
}
[data-testid="stChatMessage"]:hover {
    box-shadow:
        0 6px 24px rgba(0,0,0,.55),
        0 0 22px color-mix(in srgb, var(--accent) 30%, transparent),
        inset 0 1px 0 color-mix(in srgb, var(--accent) 20%, transparent) !important;
}

/* Мягкая анимация появления */
@keyframes fade-in-up {
    from { opacity: 0; transform: none; }
    to   { opacity: 1; transform: none; }
}
.stMarkdown { animation: fade-in-up 0.35s ease both; }

/* Пульс на primary-кнопках */
@keyframes btn-pulse {
    0%, 100% { box-shadow: 0 0 12px color-mix(in srgb, var(--accent) 30%, transparent); }
    50%      { box-shadow: 0 0 26px color-mix(in srgb, var(--accent) 60%, transparent); }
}
[data-testid="stBaseButton-primary"] {
    animation: btn-pulse 2.6s ease-in-out infinite;
}

/* Плашки под метрики */
[data-testid="stMetric"] {
    box-shadow:
        0 2px 10px rgba(0,0,0,.4),
        0 0 0 1px color-mix(in srgb, var(--accent) 20%, transparent) !important;
}
[data-testid="stMetric"]:hover {
    box-shadow:
        0 4px 18px rgba(0,0,0,.5),
        0 0 18px color-mix(in srgb, var(--accent) 40%, transparent) !important;
}

/* Скроллбар с подсветкой */
::-webkit-scrollbar-thumb:hover {
    box-shadow: 0 0 16px color-mix(in srgb, var(--accent) 80%, transparent);
}

/* Плашка под narrative */
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) {
    background:
        linear-gradient(135deg,
            color-mix(in srgb, var(--accent) 8%, var(--bg-chat)) 0%,
            var(--bg-chat) 100%) !important;
}

/* Hover-подсветка кнопок сайдбара */
[data-testid="stSidebar"] .stButton > button:hover {
    background: linear-gradient(180deg,
        color-mix(in srgb, var(--accent) 18%, var(--bg-light)),
        color-mix(in srgb, var(--accent) 8%, var(--bg-light))) !important;
}
</style>
"""


def _inject_visual_pro():
    st.markdown(_VISUAL_PRO_CSS, unsafe_allow_html=True)

# patch29: sidebar line-height fix
_SIDEBAR_LINE_FIX = """
<style>
[data-testid="stSidebar"] .stButton > button,
[data-testid="stSidebar"] .stButton > button *,
[data-testid="stSidebar"] .stButton > button p,
[data-testid="stSidebar"] .stButton > button span,
[data-testid="stSidebar"] .stButton > button div {
    line-height: 1.4 !important;
    letter-spacing: .08em !important;
    white-space: normal !important;
    word-break: keep-all !important;
    overflow-wrap: normal !important;
    font-family: var(--font-head) !important;
    font-size: .85rem !important;
}
[data-testid="stSidebar"] .stButton > button {
    min-height: 40px !important;
    padding: 9px 12px !important;
    text-transform: uppercase !important;
    font-weight: 600 !important;
}
[data-testid="stSidebar"] [data-testid="stExpander"] summary,
[data-testid="stSidebar"] [data-testid="stExpander"] summary * {
    line-height: 1.4 !important;
    font-size: .88rem !important;
    white-space: normal !important;
}
[data-testid="stSidebar"] [data-testid="stExpander"] summary {
    padding: 12px 14px !important;
    text-transform: uppercase !important;
}
[data-testid="stSidebar"] [data-testid="stExpander"] {
    margin-bottom: 8px !important;
}
/* Убрать псевдоэлементы декора (были источником «ЛRГИ») */
[data-testid="stSidebar"] .stButton > button::before,
[data-testid="stSidebar"] .stButton > button::after {
    content: none !important;
}
/* Разделитель между блоками сайдбара */
[data-testid="stSidebar"] .sidebar-divider {
    height: 1px;
    background: linear-gradient(90deg, transparent, var(--accent, #c9a961), transparent);
    box-shadow: 0 0 8px color-mix(in srgb, var(--accent, #c9a961) 40%, transparent);
    margin: 14px 0;
}
</style>
"""


def _inject_sidebar_line_fix():
    st.markdown(_SIDEBAR_LINE_FIX, unsafe_allow_html=True)

# patch30: sidebar fix
_SIDEBAR_FIX_V2 = """
<style>
[data-testid="stSidebar"] .stButton > button,
[data-testid="stSidebar"] .stButton > button *,
[data-testid="stSidebar"] .stButton > button p,
[data-testid="stSidebar"] .stButton > button span,
[data-testid="stSidebar"] .stButton > button div {
    line-height: 1.4 !important;
    letter-spacing: .08em !important;
    white-space: normal !important;
    word-break: keep-all !important;
    font-family: var(--font-head) !important;
    font-size: .85rem !important;
}
[data-testid="stSidebar"] .stButton > button {
    min-height: 40px !important;
    padding: 9px 12px !important;
    text-transform: uppercase !important;
}
[data-testid="stSidebar"] .stButton > button::before,
[data-testid="stSidebar"] .stButton > button::after {
    content: none !important;
}
[data-testid="stSidebar"] [data-testid="stExpander"] summary,
[data-testid="stSidebar"] [data-testid="stExpander"] summary * {
    line-height: 1.4 !important;
    font-size: .88rem !important;
    white-space: normal !important;
}
[data-testid="stSidebar"] [data-testid="stExpander"] summary {
    padding: 12px 14px !important;
    text-transform: uppercase !important;
}
[data-testid="stSidebar"] [data-testid="stExpander"] {
    margin-bottom: 8px !important;
}
</style>
"""


def _inject_sidebar_fix_v2():
    st.markdown(_SIDEBAR_FIX_V2, unsafe_allow_html=True)


_GHOST_KILL_CSS = """
<style>
/* Убийца ghost-рендера: убираем всё, что заставляет браузер
   рисовать текст дважды. */

/* Кнопки Streamlit — ядерный override */
.stButton > button,
.stButton > button *,
.stButton > button p,
.stButton > button span,
[data-testid="stBaseButton-secondary"],
[data-testid="stBaseButton-secondary"] *,
[data-testid="stBaseButton-primary"],
[data-testid="stBaseButton-primary"] * {
    transition: none !important;
    animation: none !important;
    transform: none !important;
    clip-path: none !important;
    -webkit-clip-path: none !important;
    text-transform: none !important;
    letter-spacing: 0 !important;
    white-space: normal !important;
    font-size: 1rem !important;
    line-height: 1.4 !important;
    font-variant: normal !important;
    font-feature-settings: normal !important;
    text-shadow: none !important;
    filter: none !important;
    will-change: auto !important;
    contain: none !important;
    position: static !important;
}

/* Expander — заголовок */
[data-testid="stExpander"] summary,
[data-testid="stExpander"] summary *,
[data-testid="stExpander"] [data-testid="stExpanderHeader"],
[data-testid="stExpander"] [data-testid="stExpanderHeader"] *,
[data-testid="stExpander"] details > summary,
[data-testid="stExpander"] details > summary * {
    transition: none !important;
    animation: none !important;
    transform: none !important;
    clip-path: none !important;
    -webkit-clip-path: none !important;
    text-transform: none !important;
    letter-spacing: 0 !important;
    white-space: normal !important;
    font-size: 1rem !important;
    line-height: 1.4 !important;
    font-variant: normal !important;
    font-feature-settings: normal !important;
    text-shadow: none !important;
    filter: none !important;
    position: static !important;
}

/* Скрыть a11y-дубли внутри summary (Streamlit иногда рендерит sr-only span) */
[data-testid="stExpander"] summary [aria-hidden="true"],
[data-testid="stExpander"] summary .sr-only,
[data-testid="stExpander"] summary .visually-hidden,
[data-testid="stExpander"] summary [style*="clip: rect(0"],
[data-testid="stExpander"] details > summary [aria-hidden="true"] {
    display: none !important;
    visibility: hidden !important;
    width: 0 !important;
    height: 0 !important;
    overflow: hidden !important;
    position: absolute !important;
    left: -9999px !important;
}

/* Иконка ▶ / ▼ у expander — скрыть совсем (она тоже может ghost-ить) */
[data-testid="stExpander"] summary svg,
[data-testid="stExpander"] details > summary svg,
[data-testid="stExpander"] [data-testid="stExpanderHeader"] svg {
    display: none !important;
    visibility: hidden !important;
    width: 0 !important;
    height: 0 !important;
}
</style>
"""


def _inject_ghost_kill():
    st.markdown(_GHOST_KILL_CSS, unsafe_allow_html=True)

# patch41: kill ghost (targeted, без *)
_GHOST_KILL_CSS = """
<style>
/* ==========================================================
   MATERIAL SYMBOLS — ВОЗВРАЩАЕМ ИХ РОДНОЙ ШРИФТ.
   Streamlit рисует иконки expander лигатурами типа
   'keyboard_arrow_right'. Без родного шрифта они видны как
   обычный текст — отсюда «arrИво exactly».
   ========================================================== */
.material-symbols-rounded,
.material-symbols-outlined,
.material-symbols-sharp,
.material-icons,
.material-icons-outlined,
.material-icons-round,
[data-testid="stIconMaterial"],
[data-testid="stIconMaterial"] *,
span[class*="material-symbols"],
span[class*="material-icons"],
[class*="material-symbol"] {
    font-family: 'Material Symbols Rounded', 'Material Symbols Outlined',
                 'Material Icons', 'Material Icons Outlined' !important;
    font-feature-settings: 'liga' !important;
    -webkit-font-feature-settings: 'liga' !important;
    font-variant: normal !important;
    text-transform: none !important;
    letter-spacing: normal !important;
    line-height: 1 !important;
    transform: none !important;
    transition: none !important;
    font-size: inherit !important;
}

/* ==========================================================
   КНОПКИ — точечно
   ========================================================== */
.stButton > button,
.stButton > button *,
.stButton > button p,
.stButton > button span,
[data-testid="stBaseButton-primary"],
[data-testid="stBaseButton-primary"] *,
[data-testid="stBaseButton-secondary"],
[data-testid="stBaseButton-secondary"] * {
    text-transform: none !important;
    letter-spacing: 0 !important;
    transform: none !important;
    transition: none !important;
    animation: none !important;
    clip-path: none !important;
    -webkit-clip-path: none !important;
    white-space: normal !important;
    font-size: 1rem !important;
    line-height: 1.4 !important;
    font-variant: normal !important;
    font-feature-settings: normal !important;
}

/* ==========================================================
   EXPANDER — только summary-текст, БЕЗ svg
   ========================================================== */
[data-testid="stExpander"] summary,
[data-testid="stExpander"] summary p,
[data-testid="stExpander"] summary > div,
[data-testid="stExpander"] [data-testid="stExpanderHeader"],
[data-testid="stExpander"] [data-testid="stExpanderHeader"] p {
    text-transform: none !important;
    letter-spacing: 0 !important;
    transform: none !important;
    transition: none !important;
    animation: none !important;
    font-size: 1rem !important;
    line-height: 1.4 !important;
    font-variant: normal !important;
    font-feature-settings: normal !important;
    white-space: normal !important;
}

/* Скрыть возможные a11y-дубли в summary — но НЕ material icons */
[data-testid="stExpander"] summary .sr-only,
[data-testid="stExpander"] summary .visually-hidden {
    display: none !important;
    position: absolute !important;
    left: -9999px !important;
    width: 0 !important;
    height: 0 !important;
    overflow: hidden !important;
}
</style>
"""


def _inject_ghost_kill():
    st.markdown(_GHOST_KILL_CSS, unsafe_allow_html=True)
