"""persistence/settings.py — настройки пользователя (seen_onboarding и т.п.)."""
from __future__ import annotations

import json
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_USERS_DIR = _ROOT / "data" / "users"


def _settings_path(login: str) -> Path:
    return _USERS_DIR / login / "settings.json"


def get_settings(login: str) -> dict:
    p = _settings_path(login)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def set_setting(login: str, key: str, value) -> None:
    p = _settings_path(login)
    p.parent.mkdir(parents=True, exist_ok=True)
    data = get_settings(login)
    data[key] = value
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# PATCH_9_FINAL_V1
def get_setting(login: str, key: str, default=None):
    """Читает настройку пользователя из settings.json."""
    import json
    from pathlib import Path
    path = Path(__file__).resolve().parents[1] / "data" / "users" / login / "settings.json"
    if not path.exists():
        return default
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default
    return data.get(key, default)


def set_setting(login: str, key: str, value) -> None:
    """Записывает настройку пользователя в settings.json."""
    import json
    from pathlib import Path
    path = Path(__file__).resolve().parents[1] / "data" / "users" / login / "settings.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {}
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    data[key] = value
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# === PATCH_11_COMPAT: get_setting/set_setting ===
def _compat_ensure_settings():
    global get_setting, set_setting
    import json as _js
    from pathlib import Path as _P

    if "get_setting" not in globals():
        def get_setting(login: str, key: str, default=None):
            path = (_P(__file__).resolve().parents[1] / "data" / "users"
                    / login / "settings.json")
            if not path.exists():
                return default
            try:
                data = _js.loads(path.read_text(encoding="utf-8"))
            except Exception:
                return default
            return data.get(key, default)

    if "set_setting" not in globals():
        def set_setting(login: str, key: str, value) -> None:
            path = (_P(__file__).resolve().parents[1] / "data" / "users"
                    / login / "settings.json")
            path.parent.mkdir(parents=True, exist_ok=True)
            data = {}
            if path.exists():
                try:
                    data = _js.loads(path.read_text(encoding="utf-8"))
                except Exception:
                    data = {}
            data[key] = value
            path.write_text(
                _js.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )


_compat_ensure_settings()
try:
    del _compat_ensure_settings
except NameError:
    pass

