"""persistence/accounts.py — аккаунты (cloud-aware)."""
from __future__ import annotations
import hashlib
import json
import re
import secrets
from datetime import datetime, timezone
from pathlib import Path
from persistence import cloud_store

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


def _cloud_ns() -> str:
    return "accounts"


def account_exists(login: str) -> bool:
    if cloud_store.is_configured():
        return cloud_store.hget_json(_cloud_ns(), login) is not None
    _ensure_dirs()
    return (_ACCOUNTS_DIR / (login + ".json")).exists()


def get_account(login: str):
    if cloud_store.is_configured():
        return cloud_store.hget_json(_cloud_ns(), login)
    _ensure_dirs()
    path = _ACCOUNTS_DIR / (login + ".json")
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
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

    if cloud_store.is_configured():
        if cloud_store.hset_json(_cloud_ns(), login, data):
            return
        print("[accounts] cloud fail → local")

    _ensure_dirs()
    path = _ACCOUNTS_DIR / (login + ".json")
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
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
    if cloud_store.is_configured():
        return sorted(cloud_store.hkeys(_cloud_ns()))
    _ensure_dirs()
    return sorted(p.stem for p in _ACCOUNTS_DIR.glob("*.json"))
