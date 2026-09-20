# PATCH_10_STYLE_V1
"""ui/theme.py — три темы с эффектами: свечения, градиенты, анимации."""
from __future__ import annotations

import streamlit as st


# ---------------------------------------------------------------------
# Определения тем: CSS-переменные + декоративный логотип
# ---------------------------------------------------------------------
THEMES = {
    "dark": {
        "label": "Нейтральная",
        "icon": "⚔",
        "vars": {
            "--accent": "#8b1a1a",
            "--accent-soft": "#b03030",
            "--accent-glow": "rgba(139, 26, 26, 0.35)",
            "--bg": "#0e0e10",
            "--bg-alt": "#131316",
            "--panel": "#16161a",
            "--panel-hi": "#1c1c20",
            "--border": "#2a2a2d",
            "--border-hi": "#3a3a3d",
            "--fg": "#e8e0d0",
            "--fg-dim": "#a0a0a0",
            "--shadow": "rgba(0,0,0,0.55)",
            "--radial-1": "rgba(139, 26, 26, 0.08)",
            "--radial-2": "rgba(80, 80, 100, 0.05)",
        },
    },
    "imperial": {
        "label": "Империум",
        "icon": "✠",
        "vars": {
            "--accent": "#b8860b",
            "--accent-soft": "#d4a017",
            "--accent-glow": "rgba(184, 134, 11, 0.4)",
            "--bg": "#0d0b08",
            "--bg-alt": "#131008",
            "--panel": "#1a1508",
            "--panel-hi": "#231c0e",
            "--border": "#3a2f10",
            "--border-hi": "#5a4518",
            "--fg": "#e8d8b0",
            "--fg-dim": "#b0a080",
            "--shadow": "rgba(0,0,0,0.65)",
            "--radial-1": "rgba(184, 134, 11, 0.10)",
            "--radial-2": "rgba(80, 50, 20, 0.06)",
        },
    },
    "mechanicum": {
        "label": "Механикум",
        "icon": "⚙",
        "vars": {
            "--accent": "#a02020",
            "--accent-soft": "#c83838",
            "--accent-glow": "rgba(160, 32, 32, 0.4)",
            "--bg": "#0a0505",
            "--bg-alt": "#100808",
            "--panel": "#180b0b",
            "--panel-hi": "#211010",
            "--border": "#3a1a1a",
            "--border-hi": "#5a2828",
            "--fg": "#e0c8c8",
            "--fg-dim": "#a09090",
            "--shadow": "rgba(0,0,0,0.7)",
            "--radial-1": "rgba(160, 32, 32, 0.12)",
            "--radial-2": "rgba(100, 30, 30, 0.08)",
        },
    },
}

_DEFAULT = "dark"


BASE_CSS = """
@keyframes fadeInUp {
    from { opacity: 0; transform: translateY(14px); }
    to   { opacity: 1; transform: translateY(0); }
}
@keyframes glowPulse {
    0%, 100% { box-shadow: 0 0 20px var(--accent-glow); }
    50%      { box-shadow: 0 0 34px var(--accent-glow); }
}
@keyframes slideIn {
    from { opacity: 0; transform: translateX(-10px); }
    to   { opacity: 1; transform: translateX(0); }
}

:root {
    {vars}
}

/* Глобальный фон */
.stApp {
    background: var(--bg) !important;
    color: var(--fg) !important;
    position: relative;
    overflow-x: hidden;
}
.stApp::before {
    content: '';
    position: fixed;
    inset: 0;
    background:
        radial-gradient(ellipse at 15% 0%, var(--radial-1) 0%, transparent 45%),
        radial-gradient(ellipse at 85% 100%, var(--radial-2) 0%, transparent 45%);
    pointer-events: none;
    z-index: 0;
}
.stApp > * { position: relative; z-index: 1; }

/* Сайдбар */
section[data-testid="stSidebar"] {
    background: var(--panel) !important;
    border-right: 1px solid var(--border) !important;
}
section[data-testid="stSidebar"] > div {
    background: var(--panel) !important;
}

/* Кнопки */
.stButton > button {
    background: var(--panel) !important;
    color: var(--fg) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
    transition: all 0.25s ease !important;
    font-family: inherit;
}
.stButton > button:hover {
    border-color: var(--accent) !important;
    color: var(--fg) !important;
    box-shadow: 0 0 14px var(--accent-glow) !important;
    transform: translateY(-1px);
}
.stButton > button[kind="primary"] {
    background: linear-gradient(180deg, var(--accent) 0%, color-mix(in srgb, var(--accent) 75%, black) 100%) !important;
    border: 1px solid var(--accent-soft) !important;
    color: #ffffff !important;
    box-shadow: 0 0 20px var(--accent-glow), 0 4px 12px var(--shadow) !important;
    font-weight: 600;
    letter-spacing: 0.5px;
}
.stButton > button[kind="primary"]:hover {
    box-shadow: 0 0 32px var(--accent-glow), 0 6px 18px var(--shadow) !important;
    transform: translateY(-1px);
    animation: glowPulse 2s ease-in-out infinite;
}

/* Метрики */
[data-testid="stMetric"] {
    background: var(--panel) !important;
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
    padding: 10px 12px !important;
    box-shadow: 0 2px 8px var(--shadow);
}
[data-testid="stMetricValue"] {
    color: var(--fg) !important;
    font-family: Georgia, serif !important;
    font-weight: bold !important;
}
[data-testid="stMetricLabel"] {
    color: var(--fg-dim) !important;
    letter-spacing: 1px;
    text-transform: uppercase;
    font-size: 11px !important;
}

/* Чат-сообщения */
.stChatMessage[data-testid="stChatMessage"] {
    background: var(--panel) !important;
    border: 1px solid var(--border) !important;
    border-radius: 12px !important;
    padding: 14px 18px !important;
    margin: 8px 0 !important;
    animation: fadeInUp 0.35s ease-out;
    box-shadow: 0 4px 12px var(--shadow);
}

/* Прогресс-бар */
.stProgress > div > div > div > div {
    background: linear-gradient(90deg, var(--accent) 0%, var(--accent-soft) 100%) !important;
    box-shadow: 0 0 10px var(--accent-glow);
}

/* Разделители */
hr {
    border-color: var(--border) !important;
    opacity: 0.6;
}

/* Selectbox и input */
.stSelectbox > div > div,
.stTextInput > div > div > input,
.stNumberInput > div > div > input {
    background: var(--panel) !important;
    color: var(--fg) !important;
    border-color: var(--border) !important;
}

/* Заголовки */
h1, h2, h3, h4 {
    color: var(--fg) !important;
    letter-spacing: 0.5px;
}

/* Ссылки */
a { color: var(--accent-soft) !important; }

/* Декоративные секции — небольшая тень при hover */
.tut-card, .kot-scroll, .th-body {
    transition: box-shadow 0.35s ease, transform 0.35s ease;
}
.tut-card:hover, .th-body:hover {
    box-shadow: 0 10px 40px var(--shadow), 0 0 30px var(--accent-glow) !important;
}
"""


def _current() -> str:
    return st.session_state.get("ui_theme", _DEFAULT)


def _build_css() -> str:
    t = THEMES.get(_current(), THEMES[_DEFAULT])
    vars_css = "\n    ".join(f"{k}: {v};" for k, v in t["vars"].items())
    return BASE_CSS.replace("{vars}", vars_css)


def apply_theme() -> None:
    st.markdown(f"<style>{_build_css()}</style>", unsafe_allow_html=True)


def render_theme_selector(key_prefix: str = "theme") -> None:
    options = list(THEMES.keys())
    current = _current()
    idx = options.index(current) if current in options else 0

    st.markdown(
        "<div style='font-size:11px; letter-spacing:3px; color:var(--accent); "
        "text-transform:uppercase; margin:12px 0 6px 0;'>Оформление</div>",
        unsafe_allow_html=True,
    )
    choice = st.selectbox(
        "🎨 Тема",
        options=options,
        index=idx,
        format_func=lambda k: f"{THEMES[k]['icon']}  {THEMES[k]['label']}",
        key=f"{key_prefix}_selector",
        label_visibility="collapsed",
    )
    if choice != current:
        st.session_state.ui_theme = choice
        st.rerun()


def current_theme_icon() -> str:
    return THEMES.get(_current(), THEMES[_DEFAULT])["icon"]
