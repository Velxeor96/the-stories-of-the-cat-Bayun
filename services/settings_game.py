# PATCH_26
"""services/settings_game.py — игровые настройки игрока."""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
USERS_DIR = ROOT / "data" / "users"

DEFAULTS = {
    "response_length": "Средний",
    "lethality": "Норма",
    "event_chance": 15,
}

LENGTH_VALUES = {"Короткий": 300, "Средний": 700, "Развёрнутый": 1200}
LETHALITY_MODS = {"Лёгкая": 0.5, "Норма": 1.0, "Хардкор": 1.5}


def _path(login: str) -> Path:
    d = USERS_DIR / login
    d.mkdir(parents=True, exist_ok=True)
    return d / "game_settings.json"


def get_settings(login: str) -> dict:
    p = _path(login)
    if not p.exists():
        return dict(DEFAULTS)
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return dict(DEFAULTS)
    out = dict(DEFAULTS)
    out.update(data or {})
    return out


def save_settings(login: str, data: dict) -> bool:
    try:
        merged = dict(DEFAULTS)
        merged.update(data or {})
        _path(login).write_text(
            json.dumps(merged, ensure_ascii=False, indent=2),
            encoding="utf-8")
        return True
    except Exception as e:
        print("[settings_game] save: " + str(e))
        return False


def max_tokens_for(login: str) -> int:
    s = get_settings(login)
    return LENGTH_VALUES.get(s.get("response_length", "Средний"), 700)


def event_chance_for(login: str) -> int:
    s = get_settings(login)
    try:
        return int(s.get("event_chance", 15))
    except Exception:
        return 15
