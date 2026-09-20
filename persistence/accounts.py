"""persistence/accounts.py — аккаунты пользователей.

Хранение:
  data/accounts/{login}.json — {login, salt, password_hash, created_at}
  data/users/{login}/        — characters/, chats/

Пароль: sha256(salt + password). Совместимо с прежним форматом.
"""
from __future__ import annotations

import hashlib
import json
import re
import secrets
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_ACCOUNTS_DIR = _ROOT / "data" / "accounts"
_USERS_DIR = _ROOT / "data" / "users"
_LOGIN_RE = re.compile(r"^[a-zA-Z0-9_\-]{3,24}$")


class AuthError(Exception):
    """Ошибка аутентификации."""


def _ensure_dirs() -> None:
    _ACCOUNTS_DIR.mkdir(parents=True, exist_ok=True)
    _USERS_DIR.mkdir(parents=True, exist_ok=True)


def _hash_password(password: str, salt: str) -> str:
    return hashlib.sha256((salt + password).encode("utf-8")).hexdigest()


def validate_login(login: str) -> tuple[bool, str]:
    if not login:
        return False, "Пустой логин"
    if not _LOGIN_RE.match(login):
        return False, "Логин: 3–24 символа, a–z, A–Z, 0–9, _, -"
    return True, ""


def validate_password(password: str) -> tuple[bool, str]:
    if not password or len(password) < 4:
        return False, "Пароль: минимум 4 символа"
    if len(password) > 128:
        return False, "Пароль слишком длинный (макс 128)"
    return True, ""


def account_exists(login: str) -> bool:
    _ensure_dirs()
    return (_ACCOUNTS_DIR / f"{login}.json").exists()


def get_account(login: str) -> dict | None:
    _ensure_dirs()
    path = _ACCOUNTS_DIR / f"{login}.json"
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
        raise AuthError(f"Логин {login!r} занят")

    salt = secrets.token_hex(16)
    pwd_hash = _hash_password(password, salt)
    data = {
        "login": login,
        "salt": salt,
        "password_hash": pwd_hash,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    path = _ACCOUNTS_DIR / f"{login}.json"
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


def list_accounts() -> list[str]:
    _ensure_dirs()
    return sorted(p.stem for p in _ACCOUNTS_DIR.glob("*.json"))


# === PATCH_11_COMPAT: shim для отсутствующих функций ===
def _compat_ensure_symbols():
    global AccountError, login, create_account
    import hashlib as _hl
    import json as _js
    from pathlib import Path as _P

    _accounts_dir = _P(__file__).resolve().parents[1] / "data" / "accounts"

    if "AccountError" not in globals():
        class AccountError(Exception):
            pass

    if "login" not in globals():
        def login(login_name: str, password: str):
            path = _accounts_dir / (login_name + ".json")
            if not path.exists():
                raise AccountError("Неверный логин или пароль")
            try:
                data = _js.loads(path.read_text(encoding="utf-8"))
            except Exception as e:
                raise AccountError("Битый файл аккаунта: " + str(e))
            salt = str(data.get("salt", ""))
            stored = str(data.get("password_hash", ""))
            calc = _hl.sha256((salt + password).encode("utf-8")).hexdigest()
            if calc != stored:
                raise AccountError("Неверный логин или пароль")
            return data

    if "create_account" not in globals():
        def create_account(login_name: str, password: str):
            import os as _os
            from datetime import datetime as _dt
            _accounts_dir.mkdir(parents=True, exist_ok=True)
            path = _accounts_dir / (login_name + ".json")
            if path.exists():
                raise AccountError("Аккаунт с таким логином уже существует")
            salt = _os.urandom(16).hex()
            pwd_hash = _hl.sha256((salt + password).encode("utf-8")).hexdigest()
            data = {
                "login": login_name,
                "salt": salt,
                "password_hash": pwd_hash,
                "created_at": _dt.utcnow().isoformat() + "Z",
            }
            path.write_text(
                _js.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            return data


_compat_ensure_symbols()
try:
    del _compat_ensure_symbols
except NameError:
    pass

