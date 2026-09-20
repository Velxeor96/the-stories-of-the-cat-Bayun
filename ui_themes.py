"""Темы визуального оформления Warhammer 40K RPG.

Два независимых слоя:
  - DECOR: пресеты декораций (текстура фона, форма углов, свечения).
  - THEMES: конкретные палитры + шрифты + указание на DECOR.

Меняя тему — мы полностью переключаем визуальный характер, не только цвет.
"""

# ============================================================
# Пресеты декораций
# ============================================================
# Каждый пресет определяет:
#   texture      — SVG-паттерн или CSS-градиенты для фона
#   texture_size — размер плитки
#   corners      — форма обрезки углов: none | notch | relic | organic
#   border_style — solid | double | ornate | dashed
#   glow_strength— 0..3, общая интенсивность свечений
#   animation    — none | glow | pulse | flicker

DECOR = {
    "industrial": {
        "texture": (
            "linear-gradient(color-mix(in srgb, var(--accent) 4%, transparent) 1px, transparent 1px),"
            " linear-gradient(90deg, color-mix(in srgb, var(--accent) 4%, transparent) 1px, transparent 1px)"
        ),
        "texture_size": "44px 44px, 44px 44px",
        "corners": "notch",
        "border_style": "solid",
        "glow_strength": 1,
        "animation": "none",
    },
    "gothic": {
        "texture": (
            "radial-gradient(ellipse at top,"
            " color-mix(in srgb, var(--accent) 8%, transparent), transparent 70%)"
        ),
        "texture_size": "100% 100%",
        "corners": "relic",
        "border_style": "ornate",
        "glow_strength": 2,
        "animation": "glow",
    },
    "tech": {
        "texture": (
            "repeating-linear-gradient(60deg,"
            " color-mix(in srgb, var(--accent) 5%, transparent) 0 1px, transparent 1px 30px),"
            " repeating-linear-gradient(-60deg,"
            " color-mix(in srgb, var(--accent) 5%, transparent) 0 1px, transparent 1px 30px),"
            " repeating-linear-gradient(0deg,"
            " color-mix(in srgb, var(--accent) 5%, transparent) 0 1px, transparent 1px 52px)"
        ),
        "texture_size": "auto, auto, auto",
        "corners": "notch",
        "border_style": "solid",
        "glow_strength": 2,
        "animation": "none",
    },
    "organic": {
        "texture": (
            "radial-gradient(ellipse 70% 40% at 20% 10%,"
            " color-mix(in srgb, var(--accent) 10%, transparent), transparent 60%),"
            " radial-gradient(ellipse 60% 50% at 80% 90%,"
            " color-mix(in srgb, var(--accent-dim) 12%, transparent), transparent 65%)"
        ),
        "texture_size": "100% 100%, 100% 100%",
        "corners": "organic",
        "border_style": "solid",
        "glow_strength": 2,
        "animation": "pulse",
    },
    "chaos": {
        "texture": (
            "repeating-linear-gradient(45deg,"
            " color-mix(in srgb, var(--accent) 5%, transparent) 0 2px, transparent 2px 14px)"
        ),
        "texture_size": "auto",
        "corners": "notch",
        "border_style": "dashed",
        "glow_strength": 3,
        "animation": "flicker",
    },
    "clean": {
        "texture": (
            "radial-gradient(ellipse at top,"
            " color-mix(in srgb, var(--accent) 6%, transparent), transparent 75%)"
        ),
        "texture_size": "100% 100%",
        "corners": "none",
        "border_style": "solid",
        "glow_strength": 0,
        "animation": "none",
    },
    "military": {
        "texture": (
            "repeating-linear-gradient(0deg,"
            " color-mix(in srgb, var(--accent) 3%, transparent) 0 1px, transparent 1px 32px),"
            " repeating-linear-gradient(90deg,"
            " color-mix(in srgb, var(--accent) 3%, transparent) 0 1px, transparent 1px 32px)"
        ),
        "texture_size": "auto, auto",
        "corners": "none",
        "border_style": "solid",
        "glow_strength": 1,
        "animation": "none",
    },
    "relic": {
        "texture": (
            "radial-gradient(ellipse at 30% 20%,"
            " color-mix(in srgb, var(--accent) 12%, transparent), transparent 65%),"
            " radial-gradient(ellipse at 70% 80%,"
            " color-mix(in srgb, var(--accent-dim) 10%, transparent), transparent 65%)"
        ),
        "texture_size": "100% 100%, 100% 100%",
        "corners": "relic",
        "border_style": "ornate",
        "glow_strength": 3,
        "animation": "glow",
    },
}


# ============================================================
# Темы. Label и icon — только кириллица / emoji.
# ============================================================

THEMES = {
    # --- Империум ---
    "grimdark": {
        "label": "Гримдарк", "icon": "☠",
        "decor": "industrial",
        "font_heading": "Georgia", "font_body": "Georgia",
        "font_urls": [],
        "palette": {
            "bg_deep": "#0e0e10", "bg_mid": "#16161a", "bg_light": "#1e1e24",
            "bg_card": "#1c1c22", "bg_chat": "#26262c", "bg_hover": "#22222a",
            "text": "#ede4d3", "text_dim": "#b8ac92", "text_faint": "#8a8068",
            "heading": "#e8d9b8", "link": "#c9a961",
            "accent": "#c9a961", "accent_dim": "#8a7444", "accent_bright": "#e8d9b8",
            "accent_glow": "rgba(201,169,97,0.35)",
            "success": "#6ee787", "warning": "#f5c878", "danger": "#ff7a7a",
            "border": "#8a7444", "border_strong": "#c9a961",
        },
    },
    "imperium": {
        "label": "Империум", "icon": "⚜",
        "decor": "gothic",
        "font_heading": "Georgia", "font_body": "Georgia",
        "font_urls": [],
        "palette": {
            "bg_deep": "#080c1a", "bg_mid": "#0d1220", "bg_light": "#141a2a",
            "bg_card": "#10162a", "bg_chat": "#161e30", "bg_hover": "#1a2338",
            "text": "#e8e4d0", "text_dim": "#a8a090", "text_faint": "#706858",
            "heading": "#f5d99a", "link": "#c9a961",
            "accent": "#c9a961", "accent_dim": "#8a7444", "accent_bright": "#f5d99a",
            "accent_glow": "rgba(245,217,154,0.4)",
            "success": "#7ad3a0", "warning": "#f5c878", "danger": "#e87070",
            "border": "#8a7444", "border_strong": "#c9a961",
        },
    },
    "inquisition": {
        "label": "Инквизиция", "icon": "⊙",
        "decor": "gothic",
        "font_heading": "Georgia", "font_body": "Georgia",
        "font_urls": [],
        "palette": {
            "bg_deep": "#0a0608", "bg_mid": "#140c10", "bg_light": "#1e1218",
            "bg_card": "#181014", "bg_chat": "#221418", "bg_hover": "#261820",
            "text": "#e8d8d8", "text_dim": "#a88888", "text_faint": "#6a4848",
            "heading": "#ff5050", "link": "#c83030",
            "accent": "#c83030", "accent_dim": "#7a1a1a", "accent_bright": "#ff5050",
            "accent_glow": "rgba(200,48,48,0.45)",
            "success": "#8cc880", "warning": "#e8a040", "danger": "#ff3030",
            "border": "#7a1a1a", "border_strong": "#c83030",
        },
    },
    "custodes": {
        "label": "Кустодес", "icon": "⚔",
        "decor": "relic",
        "font_heading": "Georgia", "font_body": "Georgia",
        "font_urls": [],
        "palette": {
            "bg_deep": "#0a0806", "bg_mid": "#141008", "bg_light": "#1e180c",
            "bg_card": "#191308", "bg_chat": "#221a0e", "bg_hover": "#281e10",
            "text": "#f0e0b8", "text_dim": "#b8a878", "text_faint": "#7a6a48",
            "heading": "#ffd97a", "link": "#e8b84a",
            "accent": "#e8b84a", "accent_dim": "#8a6a2a", "accent_bright": "#ffd97a",
            "accent_glow": "rgba(255,217,122,0.55)",
            "success": "#a8e08a", "warning": "#ffb84a", "danger": "#e87070",
            "border": "#8a6a2a", "border_strong": "#e8b84a",
        },
    },
    "deathwatch": {
        "label": "Караул Смерти", "icon": "⚔",
        "decor": "military",
        "font_heading": "Georgia", "font_body": "Georgia",
        "font_urls": [],
        "palette": {
            "bg_deep": "#06080a", "bg_mid": "#0c1014", "bg_light": "#12181e",
            "bg_card": "#10161c", "bg_chat": "#161c22", "bg_hover": "#1a222a",
            "text": "#e0e0e8", "text_dim": "#a0a0a8", "text_faint": "#606070",
            "heading": "#f0f0f8", "link": "#c8c8d0",
            "accent": "#c8c8d0", "accent_dim": "#5a5a68", "accent_bright": "#f0f0f8",
            "accent_glow": "rgba(200,200,208,0.35)",
            "success": "#88d0a0", "warning": "#d0b060", "danger": "#d07070",
            "border": "#5a5a68", "border_strong": "#c8c8d0",
        },
    },
    "guard": {
        "label": "Имперская Гвардия", "icon": "⚑",
        "decor": "military",
        "font_heading": "Georgia", "font_body": "Georgia",
        "font_urls": [],
        "palette": {
            "bg_deep": "#0e100c", "bg_mid": "#181c14", "bg_light": "#22281c",
            "bg_card": "#1c2216", "bg_chat": "#242c1c", "bg_hover": "#283018",
            "text": "#e0e8d0", "text_dim": "#a0a890", "text_faint": "#687058",
            "heading": "#d8e8a0", "link": "#a8b878",
            "accent": "#a8b878", "accent_dim": "#5a6638", "accent_bright": "#d8e8a0",
            "accent_glow": "rgba(168,184,120,0.35)",
            "success": "#a0d080", "warning": "#e0b858", "danger": "#d07858",
            "border": "#5a6638", "border_strong": "#a8b878",
        },
    },
    "ecclesiarchy": {
        "label": "Экклезиархия", "icon": "✝",
        "decor": "gothic",
        "font_heading": "Georgia", "font_body": "Georgia",
        "font_urls": [],
        "palette": {
            "bg_deep": "#100614", "bg_mid": "#1c0c24", "bg_light": "#281432",
            "bg_card": "#1e1028", "bg_chat": "#28182e", "bg_hover": "#301a34",
            "text": "#e8d8e8", "text_dim": "#a898a8", "text_faint": "#6a5868",
            "heading": "#f5d878", "link": "#c8a840",
            "accent": "#c8a840", "accent_dim": "#7a6428", "accent_bright": "#f5d878",
            "accent_glow": "rgba(245,216,120,0.5)",
            "success": "#88d090", "warning": "#e8b040", "danger": "#d04848",
            "border": "#7a6428", "border_strong": "#c8a840",
        },
    },
    "arbites": {
        "label": "Адептус Арбитес", "icon": "⚖",
        "decor": "clean",
        "font_heading": "Georgia", "font_body": "Georgia",
        "font_urls": [],
        "palette": {
            "bg_deep": "#06080a", "bg_mid": "#0e1218", "bg_light": "#161e24",
            "bg_card": "#121a20", "bg_chat": "#1a2228", "bg_hover": "#1e282e",
            "text": "#d8e0e8", "text_dim": "#889098", "text_faint": "#505860",
            "heading": "#e0e8f0", "link": "#a0a8b0",
            "accent": "#a0a8b0", "accent_dim": "#4a5258", "accent_bright": "#e0e8f0",
            "accent_glow": "rgba(160,168,176,0.3)",
            "success": "#78c890", "warning": "#d0a858", "danger": "#c85858",
            "border": "#4a5258", "border_strong": "#a0a8b0",
        },
    },
    "rogue_trader": {
        "label": "Вольный Торговец", "icon": "⚓",
        "decor": "relic",
        "font_heading": "Georgia", "font_body": "Georgia",
        "font_urls": [],
        "palette": {
            "bg_deep": "#0e0806", "bg_mid": "#1c1008", "bg_light": "#28180c",
            "bg_card": "#1e140a", "bg_chat": "#2c1c10", "bg_hover": "#301e12",
            "text": "#f0dcc0", "text_dim": "#b89c78", "text_faint": "#786448",
            "heading": "#f5c878", "link": "#d4a050",
            "accent": "#d4a050", "accent_dim": "#7a5828", "accent_bright": "#f5c878",
            "accent_glow": "rgba(212,160,80,0.45)",
            "success": "#98c880", "warning": "#e8b048", "danger": "#c87050",
            "border": "#7a5828", "border_strong": "#d4a050",
        },
    },
    "mechanicus": {
        "label": "Механикус", "icon": "⚙",
        "decor": "tech",
        "font_heading": "Georgia", "font_body": "Georgia",
        "font_urls": [],
        "palette": {
            "bg_deep": "#141210", "bg_mid": "#1c1916", "bg_light": "#26221c",
            "bg_card": "#1e1a16", "bg_chat": "#282320", "bg_hover": "#2e2824",
            "text": "#e8e0d0", "text_dim": "#b0a590", "text_faint": "#786d5a",
            "heading": "#ffc070", "link": "#ff8c1a",
            "accent": "#ff8c1a", "accent_dim": "#a05610", "accent_bright": "#ffc070",
            "accent_glow": "rgba(255,140,26,0.5)",
            "success": "#88d060", "warning": "#ffb040", "danger": "#ff5040",
            "border": "#a05610", "border_strong": "#ff8c1a",
        },
    },
    "sororitas": {
        "label": "Сороритас", "icon": "✚",
        "decor": "gothic",
        "font_heading": "Georgia", "font_body": "Georgia",
        "font_urls": [],
        "palette": {
            "bg_deep": "#140808", "bg_mid": "#1c0d0d", "bg_light": "#261212",
            "bg_card": "#1d0f0f", "bg_chat": "#281616", "bg_hover": "#301a1a",
            "text": "#f0e0d0", "text_dim": "#bc9e88", "text_faint": "#7a6250",
            "heading": "#f8dc9a", "link": "#e0b04a",
            "accent": "#e0b04a", "accent_dim": "#8a6828", "accent_bright": "#f8dc9a",
            "accent_glow": "rgba(248,220,154,0.55)",
            "success": "#a0d090", "warning": "#f0b048", "danger": "#e85050",
            "border": "#8a6828", "border_strong": "#e0b04a",
        },
    },
    "sisters_of_silence": {
        "label": "Сёстры Тишины", "icon": "⛨",
        "decor": "clean",
        "font_heading": "Georgia", "font_body": "Georgia",
        "font_urls": [],
        "palette": {
            "bg_deep": "#06080c", "bg_mid": "#0c1018", "bg_light": "#141a24",
            "bg_card": "#10161e", "bg_chat": "#181e28", "bg_hover": "#1c222c",
            "text": "#d8e0e8", "text_dim": "#8898a8", "text_faint": "#505c6c",
            "heading": "#e0f0ff", "link": "#b0c8e0",
            "accent": "#b0c8e0", "accent_dim": "#50687c", "accent_bright": "#e0f0ff",
            "accent_glow": "rgba(176,200,224,0.35)",
            "success": "#88c8a0", "warning": "#c8b878", "danger": "#c88080",
            "border": "#50687c", "border_strong": "#b0c8e0",
        },
    },
    # --- Хаос ---
    "chaos": {
        "label": "Хаос", "icon": "\U0001f441\ufe0f",
        "decor": "chaos",
        "font_heading": "Georgia", "font_body": "Georgia",
        "font_urls": [],
        "palette": {
            "bg_deep": "#140406", "bg_mid": "#1c0608", "bg_light": "#260a0c",
            "bg_card": "#1d0709", "bg_chat": "#2a0c10", "bg_hover": "#301014",
            "text": "#e8d4c0", "text_dim": "#b09a80", "text_faint": "#7a6a54",
            "heading": "#f5d08a", "link": "#d4a04a",
            "accent": "#a82020", "accent_dim": "#5a0e0e", "accent_bright": "#f5d08a",
            "accent_glow": "rgba(168,32,32,0.55)",
            "success": "#c0a840", "warning": "#f0a020", "danger": "#ff2020",
            "border": "#5a0e0e", "border_strong": "#a82020",
        },
    },
    # --- Эльдары ---
    "eldar": {
        "label": "Эльдары", "icon": "✦",
        "decor": "clean",
        "font_heading": "Georgia", "font_body": "Georgia",
        "font_urls": [],
        "palette": {
            "bg_deep": "#0a1418", "bg_mid": "#0f1c22", "bg_light": "#162830",
            "bg_card": "#122228", "bg_chat": "#1a2e38", "bg_hover": "#1e3440",
            "text": "#d8e8ec", "text_dim": "#8fa8b0", "text_faint": "#5a6c74",
            "heading": "#a0f0ff", "link": "#4dd0e1",
            "accent": "#4dd0e1", "accent_dim": "#2a8a9a", "accent_bright": "#a0f0ff",
            "accent_glow": "rgba(77,208,225,0.5)",
            "success": "#88e8b0", "warning": "#e8d070", "danger": "#e88888",
            "border": "#2a8a9a", "border_strong": "#4dd0e1",
        },
    },
    "drukhari": {
        "label": "Друкари", "icon": "☣",
        "decor": "chaos",
        "font_heading": "Georgia", "font_body": "Georgia",
        "font_urls": [],
        "palette": {
            "bg_deep": "#0f0a14", "bg_mid": "#150d1c", "bg_light": "#1e1428",
            "bg_card": "#1a1022", "bg_chat": "#221a2e", "bg_hover": "#2a1c36",
            "text": "#e0d8e8", "text_dim": "#a090b0", "text_faint": "#68587a",
            "heading": "#d0ffa0", "link": "#a8ff60",
            "accent": "#a8ff60", "accent_dim": "#6a9a38", "accent_bright": "#d0ffa0",
            "accent_glow": "rgba(168,255,96,0.5)",
            "success": "#c0ff60", "warning": "#ffd060", "danger": "#ff4060",
            "border": "#6a9a38", "border_strong": "#a8ff60",
        },
    },
    "harlequins": {
        "label": "Арлекины", "icon": "✿",
        "decor": "chaos",
        "font_heading": "Georgia", "font_body": "Georgia",
        "font_urls": [],
        "palette": {
            "bg_deep": "#100814", "bg_mid": "#1c0e24", "bg_light": "#28142e",
            "bg_card": "#1e1028", "bg_chat": "#2c1838", "bg_hover": "#361e44",
            "text": "#e8d8f0", "text_dim": "#b098c0", "text_faint": "#785878",
            "heading": "#ffb0f0", "link": "#f078d8",
            "accent": "#f078d8", "accent_dim": "#8a3880", "accent_bright": "#ffb0f0",
            "accent_glow": "rgba(240,120,216,0.55)",
            "success": "#90f0d0", "warning": "#ffe070", "danger": "#ff5090",
            "border": "#8a3880", "border_strong": "#f078d8",
        },
    },
    "ynnari": {
        "label": "Иннари", "icon": "☾",
        "decor": "gothic",
        "font_heading": "Georgia", "font_body": "Georgia",
        "font_urls": [],
        "palette": {
            "bg_deep": "#0a0814", "bg_mid": "#140e24", "bg_light": "#1e1432",
            "bg_card": "#181028", "bg_chat": "#221438", "bg_hover": "#2a1a44",
            "text": "#e0d8f0", "text_dim": "#a090b8", "text_faint": "#685878",
            "heading": "#e8c8ff", "link": "#c898e0",
            "accent": "#c898e0", "accent_dim": "#684888", "accent_bright": "#e8c8ff",
            "accent_glow": "rgba(200,152,224,0.5)",
            "success": "#90d8c0", "warning": "#e8c070", "danger": "#d87080",
            "border": "#684888", "border_strong": "#c898e0",
        },
    },
    "genestealer": {
        "label": "Генокрады", "icon": "⚡",
        "decor": "organic",
        "font_heading": "Georgia", "font_body": "Georgia",
        "font_urls": [],
        "palette": {
            "bg_deep": "#0a0814", "bg_mid": "#140e1e", "bg_light": "#1e1428",
            "bg_card": "#181024", "bg_chat": "#221a2e", "bg_hover": "#2a1e3a",
            "text": "#e0d0e8", "text_dim": "#a890b0", "text_faint": "#685878",
            "heading": "#f0a0d0", "link": "#d060b0",
            "accent": "#d060b0", "accent_dim": "#7a2868", "accent_bright": "#f0a0d0",
            "accent_glow": "rgba(208,96,176,0.5)",
            "success": "#80e0a0", "warning": "#e8b070", "danger": "#ff6080",
            "border": "#7a2868", "border_strong": "#d060b0",
        },
    },
    # --- Ксено ---
    "orks": {
        "label": "Орки", "icon": "☠",
        "decor": "chaos",
        "font_heading": "Georgia", "font_body": "Georgia",
        "font_urls": [],
        "palette": {
            "bg_deep": "#161a20", "bg_mid": "#1d222c", "bg_light": "#262d3a",
            "bg_card": "#222834", "bg_chat": "#262d3a", "bg_hover": "#2e3644",
            "text": "#e8eef0", "text_dim": "#a8b0b8", "text_faint": "#6d7580",
            "heading": "#d4ec5a", "link": "#b5d334",
            "accent": "#b5d334", "accent_dim": "#6b7d3a", "accent_bright": "#d4ec5a",
            "accent_glow": "rgba(181,211,52,0.5)",
            "success": "#b5d334", "warning": "#e8b020", "danger": "#e04020",
            "border": "#6b7d3a", "border_strong": "#b5d334",
        },
    },
    "tau": {
        "label": "Тау", "icon": "⊕",
        "decor": "clean",
        "font_heading": "Georgia", "font_body": "Georgia",
        "font_urls": [],
        "palette": {
            "bg_deep": "#0a1018", "bg_mid": "#0f1822", "bg_light": "#16202e",
            "bg_card": "#111a26", "bg_chat": "#18222e", "bg_hover": "#1c2838",
            "text": "#e0e8f0", "text_dim": "#98a8b8", "text_faint": "#5a6878",
            "heading": "#a0dcf5", "link": "#4fc3f7",
            "accent": "#4fc3f7", "accent_dim": "#2a80a8", "accent_bright": "#a0dcf5",
            "accent_glow": "rgba(79,195,247,0.45)",
            "success": "#80d8a0", "warning": "#e8b060", "danger": "#e07070",
            "border": "#2a80a8", "border_strong": "#4fc3f7",
        },
    },
    "necrons": {
        "label": "Некроны", "icon": "☥",
        "decor": "tech",
        "font_heading": "Georgia", "font_body": "Georgia",
        "font_urls": [],
        "palette": {
            "bg_deep": "#0a0d0c", "bg_mid": "#0f1413", "bg_light": "#161b1a",
            "bg_card": "#131918", "bg_chat": "#1a2321", "bg_hover": "#1e2a28",
            "text": "#d8e8e2", "text_dim": "#8fa89f", "text_faint": "#5a6f68",
            "heading": "#7effd0", "link": "#3dd9a4",
            "accent": "#3dd9a4", "accent_dim": "#2a9b76", "accent_bright": "#7effd0",
            "accent_glow": "rgba(61,217,164,0.55)",
            "success": "#7effd0", "warning": "#e8e070", "danger": "#e07070",
            "border": "#2a9b76", "border_strong": "#3dd9a4",
        },
    },
    "tyranids": {
        "label": "Тираниды", "icon": "☢",
        "decor": "organic",
        "font_heading": "Georgia", "font_body": "Georgia",
        "font_urls": [],
        "palette": {
            "bg_deep": "#100810", "bg_mid": "#180d18", "bg_light": "#221422",
            "bg_card": "#1a101a", "bg_chat": "#241624", "bg_hover": "#2c1c2c",
            "text": "#e8d8f0", "text_dim": "#a898b8", "text_faint": "#685878",
            "heading": "#c8a0ff", "link": "#9c5cff",
            "accent": "#9c5cff", "accent_dim": "#5a3888", "accent_bright": "#c8a0ff",
            "accent_glow": "rgba(156,92,255,0.55)",
            "success": "#90e0a0", "warning": "#e8b050", "danger": "#e84850",
            "border": "#5a3888", "border_strong": "#9c5cff",
        },
    },
}


# ============================================================
# API
# ============================================================

THEME_ORDER = [
    "grimdark", "imperium", "inquisition", "custodes", "deathwatch",
    "guard", "ecclesiarchy", "arbites", "rogue_trader", "mechanicus",
    "sororitas", "sisters_of_silence",
    "chaos",
    "eldar", "drukhari", "harlequins", "ynnari",
    "orks", "tau", "necrons", "tyranids", "genestealer",
]

DEFAULT_THEME = "inquisition"


def theme_keys():
    """Ключи тем в правильном порядке."""
    return [k for k in THEME_ORDER if k in THEMES]


def theme_label(key):
    t = THEMES.get(key) or THEMES[DEFAULT_THEME]
    return t.get("label", key)


def theme_icon(key):
    t = THEMES.get(key) or THEMES[DEFAULT_THEME]
    return t.get("icon", "")


def theme_display(key):
    """Готовый формат: '💀 Гримдарк'."""
    return f"{theme_icon(key)} {theme_label(key)}"


def get_theme(key):
    """Возвращает тему с fallback на дефолтную."""
    return THEMES.get(key) or THEMES[DEFAULT_THEME]


def get_decor(theme):
    """Возвращает DECOR-пресет темы."""
    name = theme.get("decor", "industrial")
    return DECOR.get(name, DECOR["industrial"])

# patch25: усиленные палитры
# Tau — неоново-голубой + глубокий синий
THEMES["tau"]["palette"].update({
    "bg_deep": "#021018", "bg_mid": "#04202c", "bg_light": "#083848",
    "bg_card": "#062430", "bg_chat": "#0a4050", "bg_hover": "#0d5060",
    "accent": "#00e0ff", "accent_dim": "#0080a0", "accent_bright": "#80f0ff",
    "accent_glow": "rgba(0,224,255,0.65)",
    "heading": "#80f0ff", "link": "#00e0ff",
})

# Necrons — ядерный зелёный на угольном
THEMES["necrons"]["palette"].update({
    "bg_deep": "#04080a", "bg_mid": "#08120e", "bg_light": "#101e18",
    "bg_card": "#0a1610", "bg_chat": "#102018", "bg_hover": "#142a20",
    "accent": "#00ff88", "accent_dim": "#008a4a", "accent_bright": "#88ffcc",
    "accent_glow": "rgba(0,255,136,0.7)",
    "heading": "#88ffcc", "link": "#00ff88",
})

# Orks — кислотно-зелёный + кроваво-красный
THEMES["orks"]["palette"].update({
    "bg_deep": "#0a1008", "bg_mid": "#141c10", "bg_light": "#1e2a18",
    "bg_card": "#182418", "bg_chat": "#202e1e", "bg_hover": "#2a3a24",
    "accent": "#c0ff20", "accent_dim": "#6a8a18", "accent_bright": "#e0ff80",
    "accent_glow": "rgba(192,255,32,0.6)",
    "heading": "#e0ff80", "link": "#c0ff20",
    "danger": "#ff2020",
})

# Chaos — тёмно-багровый + золото
THEMES["chaos"]["palette"].update({
    "bg_deep": "#0a0206", "bg_mid": "#180408", "bg_light": "#2a060e",
    "bg_card": "#1c040a", "bg_chat": "#2a0812", "bg_hover": "#380c18",
    "accent": "#d0a020", "accent_dim": "#6a4a08", "accent_bright": "#ffd060",
    "accent_glow": "rgba(208,160,32,0.6)",
    "heading": "#ffd060", "link": "#d0a020",
    "danger": "#ff1818",
})
