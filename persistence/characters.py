"""persistence/characters.py — сохранение персонажей (SQLite)."""
from __future__ import annotations

import json
import re
from contextlib import closing
from pathlib import Path

from persistence.db import get_conn, init_db

_ROOT = Path(__file__).resolve().parents[1]
_USERS_DIR = _ROOT / "data" / "users"
_NAME_RE = re.compile(r"^[\w\- ]{1,48}$", re.UNICODE)


class CharacterError(Exception):
    pass


def _chars_dir(login: str) -> Path:
    d = _USERS_DIR / login / "characters"
    d.mkdir(parents=True, exist_ok=True)
    return d


def validate_name(name: str) -> tuple:
    if not name or not name.strip():
        return False, "Имя не может быть пустым"
    if not _NAME_RE.match(name.strip()):
        return False, "Имя: 1-48 символов, буквы, цифры, пробел, _, -"
    return True, ""


def list_characters(login: str) -> list:
    init_db()
    with closing(get_conn()) as conn, conn:
        rows = conn.execute(
            "SELECT name FROM characters WHERE login = ? ORDER BY name",
            (login,),
        ).fetchall()
    return [row["name"] for row in rows]


def character_path(login: str, name: str) -> Path:
    return _chars_dir(login) / (name + ".json")


def load_character(login: str, name: str) -> dict:
    init_db()
    with closing(get_conn()) as conn, conn:
        row = conn.execute(
            "SELECT data FROM characters WHERE login = ? AND name = ?",
            (login, name),
        ).fetchone()
    if row is None:
        raise CharacterError("Персонаж " + repr(name) + " не найден")
    try:
        return json.loads(row["data"])
    except Exception as e:
        raise CharacterError("Не читается персонаж " + repr(name) + ": " + str(e)) from e


def save_character(login: str, name: str, data: dict) -> None:
    ok, err = validate_name(name)
    if not ok:
        raise CharacterError(err)

    payload = json.dumps(data, ensure_ascii=False)
    init_db()
    with closing(get_conn()) as conn, conn:
        conn.execute(
            "INSERT OR REPLACE INTO characters(login, name, data) VALUES (?, ?, ?)",
            (login, name, payload),
        )


def delete_character(login: str, name: str) -> None:
    init_db()
    with closing(get_conn()) as conn, conn:
        conn.execute(
            "DELETE FROM characters WHERE login = ? AND name = ?",
            (login, name),
        )


def has_any(login: str) -> bool:
    return bool(list_characters(login))
