"""persistence/accounts.py — аккаунты (SQLite)."""
from __future__ import annotations

import hashlib
import json
import re
import secrets
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from persistence.db import get_conn, init_db

_ROOT = Path(__file__).resolve().parents[1]
_ACCOUNTS_DIR = _ROOT / "data" / "accounts"
_USERS_DIR = _ROOT / "data" / "users"
_LOGIN_RE = re.compile(r"^[a-zA-Z0-9_\-]{3,24}$")


class AuthError(Exception):
    pass


def _ensure_dirs() -> None:
    _ACCOUNTS_DIR.mkdir(parents=True, exist_ok=True)
    _USERS_DIR.mkdir(parents=True, exist_ok=True)


def _hash_password(password: str, salt: str) -> str:
    return hashlib.sha256((salt + password).encode("utf-8")).hexdigest()


def validate_login(login: str) -> tuple:
    if not login:
        return False, "Пустой логин"
    if not _LOGIN_RE.match(login):
        return False, "Логин: 3-24 символа, a-z, A-Z, 0-9, _, -"
    return True, ""


def validate_password(password: str) -> tuple:
    if not password or len(password) < 4:
        return False, "Пароль: минимум 4 символа"
    if len(password) > 128:
        return False, "Пароль слишком длинный"
    return True, ""


def account_exists(login: str) -> bool:
    init_db()
    with closing(get_conn()) as conn, conn:
        row = conn.execute(
            "SELECT 1 FROM accounts WHERE login = ?", (login,)
        ).fetchone()
    return row is not None


def get_account(login: str):
    init_db()
    with closing(get_conn()) as conn, conn:
        row = conn.execute(
            "SELECT data FROM accounts WHERE login = ?", (login,)
        ).fetchone()
    if row is None:
        return None
    try:
        return json.loads(row["data"])
    except Exception:
        return None


def register_user(login: str, password: str) -> None:
    ok, err = validate_login(login)
    if not ok:
        raise AuthError(err)
    ok, err = validate_password(password)
    if not ok:
        raise AuthError(err)
    if account_exists(login):
        raise AuthError("Логин " + repr(login) + " занят")

    salt = secrets.token_hex(16)
    pwd_hash = _hash_password(password, salt)
    data = {
        "login": login,
        "salt": salt,
        "password_hash": pwd_hash,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }

    init_db()
    with closing(get_conn()) as conn, conn:
        conn.execute(
            "INSERT OR REPLACE INTO accounts (login, data) VALUES (?, ?)",
            (login, json.dumps(data, ensure_ascii=False)),
        )

    _ensure_dirs()
    user_dir = _USERS_DIR / login
    (user_dir / "characters").mkdir(parents=True, exist_ok=True)
    (user_dir / "chats").mkdir(parents=True, exist_ok=True)


def verify_user(login: str, password: str) -> bool:
    if not login or not password:
        return False
    account = get_account(login)
    if account is None:
        return False
    salt = account.get("salt", "")
    expected = account.get("password_hash", "")
    actual = _hash_password(password, salt)
    return secrets.compare_digest(expected, actual)


def user_dir_for(login: str) -> Path:
    d = _USERS_DIR / login
    (d / "characters").mkdir(parents=True, exist_ok=True)
    (d / "chats").mkdir(parents=True, exist_ok=True)
    return d


def list_accounts() -> list:
    init_db()
    with closing(get_conn()) as conn, conn:
        rows = conn.execute(
            "SELECT login FROM accounts ORDER BY login"
        ).fetchall()
    return [row["login"] for row in rows]
