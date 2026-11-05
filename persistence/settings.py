"""persistence/settings.py — настройки пользователя (SQLite)."""
from __future__ import annotations

import json
from contextlib import closing

from persistence.db import get_conn, init_db


def get_settings(login: str) -> dict:
    # init_db()  # PATCH_130: moved to app startup
    with closing(get_conn()) as conn, conn:
        row = conn.execute(
            "SELECT data FROM user_settings WHERE login = ?", (login,)
        ).fetchone()
    if row is None:
        return {}
    try:
        data = json.loads(row["data"])
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def get_setting(login: str, key: str, default=None):
    return get_settings(login).get(key, default)


def set_setting(login: str, key: str, value) -> None:
    data = get_settings(login)
    data[key] = value
    # init_db()  # PATCH_130: moved to app startup
    with closing(get_conn()) as conn, conn:
        conn.execute(
            "INSERT OR REPLACE INTO user_settings (login, data) VALUES (?, ?)",
            (login, json.dumps(data, ensure_ascii=False)),
        )
