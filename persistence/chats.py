"""persistence/chats.py — история чата (cloud-aware)."""
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
    safe = character.replace("/", "_").replace("\\", "_")
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
