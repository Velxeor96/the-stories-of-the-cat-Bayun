"""settings_game.py — игровые настройки игрока (SQLite)."""
from __future__ import annotations

import json
from contextlib import closing

from persistence.db import get_conn, init_db

DEFAULTS = {
    "response_length": "Средний",
    "lethality": "Норма",
    "event_chance": 15,
}

LENGTH_VALUES = {"Короткий": 300, "Средний": 700, "Развёрнутый": 1200}
LETHALITY_MODS = {"Лёгкая": 0.5, "Норма": 1.0, "Хардкор": 1.5}


def get_settings(login: str) -> dict:
    init_db()
    with closing(get_conn()) as conn, conn:
        row = conn.execute(
            "SELECT data FROM settings WHERE login = ?",
            (login,),
        ).fetchone()

    if row is None:
        return dict(DEFAULTS)

    try:
        data = json.loads(row["data"])
    except Exception:
        return dict(DEFAULTS)

    out = dict(DEFAULTS)
    out.update(data or {})
    return out


def save_settings(login: str, data: dict) -> bool:
    try:
        merged = dict(DEFAULTS)
        merged.update(data or {})
        payload = json.dumps(merged, ensure_ascii=False)

        init_db()
        with closing(get_conn()) as conn, conn:
            conn.execute(
                "INSERT OR REPLACE INTO settings(login, data) VALUES (?, ?)",
                (login, payload),
            )
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
