"""persistence/chats.py — сохранение истории чата по персонажу."""
from __future__ import annotations

import json
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_USERS_DIR = _ROOT / "data" / "users"


class ChatError(Exception):
    """Ошибка чата."""


def _chats_dir(login: str) -> Path:
    d = _USERS_DIR / login / "chats"
    d.mkdir(parents=True, exist_ok=True)
    return d


def chat_path(login: str, character: str) -> Path:
    safe = character.replace("/", "_").replace("\\", "_")
    return _chats_dir(login) / f"{safe}.json"


def load_history(login: str, character: str) -> list[dict]:
    p = chat_path(login, character)
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def save_history(login: str, character: str, history: list[dict]) -> None:
    p = chat_path(login, character)
    p.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")


def append_turn(login: str, character: str, player_input: str,
                master_text: str) -> list[dict]:
    h = load_history(login, character)
    h.append({"role": "player", "text": player_input})
    h.append({"role": "master", "text": master_text})
    save_history(login, character, h)
    return h
