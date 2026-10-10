"""persistence/settings.py — настройки пользователя (cloud-aware)."""
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
