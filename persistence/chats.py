"""persistence/chats.py — история чата (SQLite)."""
from __future__ import annotations

from contextlib import closing
from pathlib import Path

from persistence.db import get_conn, init_db

_ROOT = Path(__file__).resolve().parents[1]
_USERS_DIR = _ROOT / "data" / "users"


class ChatError(Exception):
    pass


def _chats_dir(login: str) -> Path:
    d = _USERS_DIR / login / "chats"
    d.mkdir(parents=True, exist_ok=True)
    return d


def chat_path(login: str, character: str) -> Path:
    safe = character.replace("/", "_").replace("\\", "_")
    return _chats_dir(login) / (safe + ".json")


def load_history(login: str, character: str) -> list:
    # init_db()  # PATCH_130: moved to app startup
    with closing(get_conn()) as conn, conn:
        rows = conn.execute(
            "SELECT role, text FROM chats "
            "WHERE login = ? AND character = ? ORDER BY id ASC",
            (login, character),
        ).fetchall()
    return [{"role": row["role"], "text": row["text"]} for row in rows]


def save_history(login: str, character: str, history: list) -> None:
    # init_db()  # PATCH_130: moved to app startup
    with closing(get_conn()) as conn, conn:
        conn.execute(
            "DELETE FROM chats WHERE login = ? AND character = ?",
            (login, character),
        )
        for item in history or []:
            role = item.get("role", "") if isinstance(item, dict) else ""
            text = item.get("text", "") if isinstance(item, dict) else ""
            conn.execute(
                "INSERT INTO chats(login, character, role, text) VALUES (?, ?, ?, ?)",
                (login, character, role, text),
            )


def append_turn(login: str, character: str, player_input: str,
                master_text: str) -> list:
    h = load_history(login, character)
    h.append({"role": "player", "text": player_input})
    h.append({"role": "master", "text": master_text})
    save_history(login, character, h)
    return h
