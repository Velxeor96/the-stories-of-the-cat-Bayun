"""Аккаунты пользователей: регистрация, вход, изоляция данных.

Хранение:
  data/accounts/{login}.json  — {login, salt, password_hash, created_at}
  data/users/{login}/         — директория пользователя

Пароль: sha256(salt + password). Соль — 16 байт hex, случайная.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
from datetime import datetime, timezone
from pathlib import Path


class AuthError(Exception):
    """Ошибка аутентификации."""


_ACCOUNTS_DIR = Path("data") / "accounts"
_USERS_DIR = Path("data") / "users"
_LOGIN_RE = re.compile(r"^[a-zA-Z0-9_\-]{3,24}$")


def _accounts_dir() -> Path:
    d = Path(__file__).resolve().parents[1] / _ACCOUNTS_DIR
    d.mkdir(parents=True, exist_ok=True)
    return d


def _users_dir() -> Path:
    d = Path(__file__).resolve().parents[1] / _USERS_DIR
    d.mkdir(parents=True, exist_ok=True)
    return d


def _hash_password(password: str, salt: str) -> str:
    return hashlib.sha256((salt + password).encode("utf-8")).hexdigest()


def validate_login(login: str) -> tuple[bool, str]:
    if not login:
        return False, "Пустой логин"
    if not _LOGIN_RE.match(login):
        return False, "Логин: 3-24 символа, a-z, A-Z, 0-9, _, -"
    return True, ""


def validate_password(password: str) -> tuple[bool, str]:
    if not password or len(password) < 4:
        return False, "Пароль: минимум 4 символа"
    if len(password) > 128:
        return False, "Пароль слишком длинный (макс 128)"
    return True, ""


def account_exists(login: str) -> bool:
    return (_accounts_dir() / f"{login}.json").exists()


def register_user(login: str, password: str) -> None:
    ok, err = validate_login(login)
    if not ok:
        raise AuthError(err)
    ok, err = validate_password(password)
    if not ok:
        raise AuthError(err)
    if account_exists(login):
        raise AuthError(f"Логин {login!r} занят")

    salt = secrets.token_hex(16)
    pwd_hash = _hash_password(password, salt)
    data = {
        "login": login,
        "salt": salt,
        "password_hash": pwd_hash,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    path = _accounts_dir() / f"{login}.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    user_dir = _users_dir() / login
    (user_dir / "characters").mkdir(parents=True, exist_ok=True)
    (user_dir / "chats").mkdir(parents=True, exist_ok=True)


def verify_user(login: str, password: str) -> bool:
    if not login or not password:
        return False
    path = _accounts_dir() / f"{login}.json"
    if not path.exists():
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return False
    salt = data.get("salt", "")
    expected = data.get("password_hash", "")
    actual = _hash_password(password, salt)
    return secrets.compare_digest(expected, actual)


def user_dir_for(login: str) -> Path:
    d = _users_dir() / login
    (d / "characters").mkdir(parents=True, exist_ok=True)
    (d / "chats").mkdir(parents=True, exist_ok=True)
    return d


def list_accounts() -> list[str]:
    d = _accounts_dir()
    return sorted(p.stem for p in d.glob("*.json"))
