# PATCH_26
"""services/autosave.py — снапшот персонажа перед каждым ходом."""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
USERS_DIR = ROOT / "data" / "users"


def _path(login: str, char_name: str) -> Path:
    d = USERS_DIR / login / "autosave"
    d.mkdir(parents=True, exist_ok=True)
    safe = str(char_name).replace("/", "_").replace("\\", "_")
    return d / (safe + ".json")


def save_snapshot(login: str, char_name: str, char: dict) -> bool:
    if not login or not char_name or not isinstance(char, dict):
        return False
    try:
        payload = {
            "char": char,
        }
        _path(login, char_name).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8")
        return True
    except Exception as e:
        print("[autosave] save fail: " + str(e))
        return False


def load_snapshot(login: str, char_name: str) -> dict | None:
    p = _path(login, char_name)
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data.get("char")
    except Exception as e:
        print("[autosave] load fail: " + str(e))
        return None


def has_snapshot(login: str, char_name: str) -> bool:
    return _path(login, char_name).exists()


def clear_snapshot(login: str, char_name: str) -> bool:
    p = _path(login, char_name)
    if p.exists():
        try:
            p.unlink()
            return True
        except Exception:
            return False
    return False
