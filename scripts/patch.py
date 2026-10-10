# scripts/patch.py — PATCH_73a: cloud-aware persistence + тестеры
from __future__ import annotations
import ast, shutil, sys
from pathlib import Path

TAG = "PATCH_73a"
ROOT = Path(__file__).resolve().parent.parent
if not (ROOT / "app.py").exists():
    print("[ERROR] app.py не найден.")
    sys.exit(1)

r = {"modified": [], "errors": []}

def _bk(p):
    b = p.with_suffix(p.suffix + ".bak_pre_" + TAG)
    if not b.exists() and p.exists():
        try:
            shutil.copy2(p, b)
        except Exception:
            pass

def _write(p, content, marker=None):
    if marker and p.exists() and marker in p.read_text(encoding="utf-8"):
        r["modified"].append(f"{p.relative_to(ROOT)} — уже пропатчен")
        return
    try:
        ast.parse(content)
    except SyntaxError as e:
        r["errors"].append(f"{p.relative_to(ROOT)} syntax: {e}")
        return
    _bk(p)
    p.write_text(content, encoding="utf-8")
    r["modified"].append(f"{p.relative_to(ROOT)} — записан")


# === 1. credits.py — тестеры ===
p = ROOT / "ui" / "screens" / "credits.py"
text = p.read_text(encoding="utf-8")
if '"Кайса"' in text and '"Валерий"' in text:
    r["modified"].append("credits.py — уже обновлён")
else:
    OLD = '''THANKS_NAMES = [
    "Ксения",
    "Анна",
    "Игорь",
    "Сергей",
    "Роман",
    "друзья Романа (кем бы вы ни были, ребят)",
]'''
    NEW = '''THANKS_NAMES = [
    "Ксения",
    "Кайса",
    "Игорь",
    "Сергей",
    "Роман",
    "Валерий",
    "Анна",
    "друзья Романа (кем бы вы ни были, ребят)",
]'''
    if OLD in text:
        nt = text.replace(OLD, NEW, 1)
        try:
            ast.parse(nt)
        except SyntaxError as e:
            r["errors"].append("credits.py: " + str(e))
        else:
            _bk(p)
            p.write_text(nt, encoding="utf-8")
            r["modified"].append("credits.py — +Валерий, Анна, Кайса")
    else:
        r["errors"].append("credits.py: THANKS_NAMES не найден")


# === 2. cloud_store.py ===
CLOUD_STORE = '''"""persistence/cloud_store.py — облачное хранилище (Upstash Redis).

Если UPSTASH_REDIS_REST_URL и UPSTASH_REDIS_REST_TOKEN заданы — используем
облако. Если нет — null-store, persistence/* работает с локальными файлами.
"""
from __future__ import annotations
import json
import os

_CLIENT = None
_CONFIGURED = None


def _get_client():
    global _CLIENT, _CONFIGURED
    if _CONFIGURED is not None:
        return _CLIENT

    url = os.environ.get("UPSTASH_REDIS_REST_URL", "").strip()
    token = os.environ.get("UPSTASH_REDIS_REST_TOKEN", "").strip()

    if not url or not token:
        try:
            import streamlit as st
            url = url or str(st.secrets.get("UPSTASH_REDIS_REST_URL", "")).strip()
            token = token or str(st.secrets.get("UPSTASH_REDIS_REST_TOKEN", "")).strip()
        except Exception:
            pass

    if not url or not token:
        _CONFIGURED = False
        _CLIENT = None
        print("[cloud_store] Upstash не настроен → локальные файлы")
        return None

    try:
        from upstash_redis import Redis
        _CLIENT = Redis(url=url, token=token)
        _CONFIGURED = True
        print("[cloud_store] Upstash подключён")
    except Exception as e:
        print("[cloud_store] Ошибка: " + type(e).__name__ + ": " + str(e))
        _CONFIGURED = False
        _CLIENT = None
    return _CLIENT


def is_configured() -> bool:
    return _get_client() is not None


def hset_json(namespace: str, key: str, value) -> bool:
    r = _get_client()
    if r is None:
        return False
    try:
        r.hset(namespace, key, json.dumps(value, ensure_ascii=False))
        return True
    except Exception as e:
        print("[cloud_store] hset fail: " + type(e).__name__)
        return False


def hget_json(namespace: str, key: str):
    r = _get_client()
    if r is None:
        return None
    try:
        raw = r.hget(namespace, key)
        if raw is None:
            return None
        return json.loads(raw)
    except Exception as e:
        print("[cloud_store] hget fail: " + type(e).__name__)
        return None


def hkeys(namespace: str) -> list:
    r = _get_client()
    if r is None:
        return []
    try:
        return list(r.hkeys(namespace) or [])
    except Exception:
        return []


def hdel(namespace: str, key: str) -> bool:
    r = _get_client()
    if r is None:
        return False
    try:
        r.hdel(namespace, key)
        return True
    except Exception:
        return False
'''
_write(ROOT / "persistence" / "cloud_store.py", CLOUD_STORE,
       marker="def is_configured()")


# === 3. characters.py ===
CHARACTERS = '''"""persistence/characters.py — сохранение персонажей (cloud-aware)."""
from __future__ import annotations
import json
import re
from pathlib import Path
from persistence import cloud_store

_ROOT = Path(__file__).resolve().parents[1]
_USERS_DIR = _ROOT / "data" / "users"
_NAME_RE = re.compile(r"^[\\w\\- ]{1,48}$", re.UNICODE)


class CharacterError(Exception):
    pass


def _chars_dir(login: str) -> Path:
    d = _USERS_DIR / login / "characters"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _cloud_ns(login: str) -> str:
    return "chars:" + login


def validate_name(name: str) -> tuple:
    if not name or not name.strip():
        return False, "Имя не может быть пустым"
    if not _NAME_RE.match(name.strip()):
        return False, "Имя: 1-48 символов, буквы, цифры, пробел, _, -"
    return True, ""


def list_characters(login: str) -> list:
    if cloud_store.is_configured():
        return sorted(cloud_store.hkeys(_cloud_ns(login)))
    return sorted(p.stem for p in _chars_dir(login).glob("*.json"))


def character_path(login: str, name: str) -> Path:
    return _chars_dir(login) / (name + ".json")


def load_character(login: str, name: str) -> dict:
    if cloud_store.is_configured():
        data = cloud_store.hget_json(_cloud_ns(login), name)
        if data is None:
            raise CharacterError("Персонаж " + repr(name) + " не найден")
        return data
    p = character_path(login, name)
    if not p.exists():
        raise CharacterError("Персонаж " + repr(name) + " не найден")
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        raise CharacterError("Не читается " + p.name + ": " + str(e)) from e


def save_character(login: str, name: str, data: dict) -> None:
    ok, err = validate_name(name)
    if not ok:
        raise CharacterError(err)
    if cloud_store.is_configured():
        if cloud_store.hset_json(_cloud_ns(login), name, data):
            return
        print("[characters] cloud fail → local")
    p = character_path(login, name)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def delete_character(login: str, name: str) -> None:
    if cloud_store.is_configured():
        cloud_store.hdel(_cloud_ns(login), name)
    p = character_path(login, name)
    if p.exists():
        p.unlink()


def has_any(login: str) -> bool:
    return bool(list_characters(login))
'''
_write(ROOT / "persistence" / "characters.py", CHARACTERS,
       marker="cloud_store")


# === 4. chats.py ===
CHATS = '''"""persistence/chats.py — история чата (cloud-aware)."""
from __future__ import annotations
import json
from pathlib import Path
from persistence import cloud_store

_ROOT = Path(__file__).resolve().parents[1]
_USERS_DIR = _ROOT / "data" / "users"


class ChatError(Exception):
    pass


def _chats_dir(login: str) -> Path:
    d = _USERS_DIR / login / "chats"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _cloud_ns(login: str) -> str:
    return "chats:" + login


def chat_path(login: str, character: str) -> Path:
    safe = character.replace("/", "_").replace("\\\\", "_")
    return _chats_dir(login) / (safe + ".json")


def load_history(login: str, character: str) -> list:
    if cloud_store.is_configured():
        data = cloud_store.hget_json(_cloud_ns(login), character)
        return data if isinstance(data, list) else []
    p = chat_path(login, character)
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def save_history(login: str, character: str, history: list) -> None:
    if cloud_store.is_configured():
        if cloud_store.hset_json(_cloud_ns(login), character, history):
            return
        print("[chats] cloud fail → local")
    p = chat_path(login, character)
    p.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")


def append_turn(login: str, character: str, player_input: str,
                master_text: str) -> list:
    h = load_history(login, character)
    h.append({"role": "player", "text": player_input})
    h.append({"role": "master", "text": master_text})
    save_history(login, character, h)
    return h
'''
_write(ROOT / "persistence" / "chats.py", CHATS, marker="cloud_store")


# === 5. settings.py ===
SETTINGS = '''"""persistence/settings.py — настройки пользователя (cloud-aware)."""
from __future__ import annotations
import json
from pathlib import Path
from persistence import cloud_store

_ROOT = Path(__file__).resolve().parents[1]
_USERS_DIR = _ROOT / "data" / "users"


def _settings_path(login: str) -> Path:
    return _USERS_DIR / login / "settings.json"


def _cloud_ns() -> str:
    return "settings"


def get_settings(login: str) -> dict:
    if cloud_store.is_configured():
        data = cloud_store.hget_json(_cloud_ns(), login)
        return data if isinstance(data, dict) else {}
    p = _settings_path(login)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def get_setting(login: str, key: str, default=None):
    return get_settings(login).get(key, default)


def set_setting(login: str, key: str, value) -> None:
    data = get_settings(login)
    data[key] = value
    if cloud_store.is_configured():
        if cloud_store.hset_json(_cloud_ns(), login, data):
            return
        print("[settings] cloud fail → local")
    p = _settings_path(login)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
'''
_write(ROOT / "persistence" / "settings.py", SETTINGS, marker="cloud_store")


# === 6. accounts.py ===
ACCOUNTS = '''"""persistence/accounts.py — аккаунты (cloud-aware)."""
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
_LOGIN_RE = re.compile(r"^[a-zA-Z0-9_\\-]{3,24}$")


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
'''
_write(ROOT / "persistence" / "accounts.py", ACCOUNTS, marker="cloud_store")


# === 7. requirements.txt ===
p = ROOT / "requirements.txt"
text = p.read_text(encoding="utf-8")
if "upstash-redis" in text:
    r["modified"].append("requirements.txt — upstash-redis уже есть")
else:
    _bk(p)
    p.write_text(text.rstrip() + "\nupstash-redis>=1.0.0\n", encoding="utf-8")
    r["modified"].append("requirements.txt — +upstash-redis")


print("=== PATCH " + TAG + " ===")
for m in r["modified"]:
    print("  [MODIFIED] " + m)
for e in r["errors"]:
    print("  [ERROR] " + e)
print("DONE" if not r["errors"] else "DONE (with errors)")