# PATCH_17
"""services/notes.py — пользовательские заметки игрока по персонажу."""
from __future__ import annotations

from datetime import datetime


def get_notes(char: dict) -> list[dict]:
    if not isinstance(char, dict):
        return []
    notes = char.get("player_notes")
    if not isinstance(notes, list):
        return []
    return [n for n in notes if isinstance(n, dict)]


def add_note(char: dict, text: str, tag: str = "") -> bool:
    if not isinstance(char, dict):
        return False
    text = (text or "").strip()
    if not text:
        return False
    notes = char.setdefault("player_notes", [])
    if not isinstance(notes, list):
        notes = []
        char["player_notes"] = notes
    notes.append({
        "text": text,
        "tag": (tag or "").strip(),
        "ts": datetime.now().isoformat(timespec="seconds"),
    })
    return True


def remove_note(char: dict, index: int) -> bool:
    if not isinstance(char, dict):
        return False
    notes = char.get("player_notes")
    if not isinstance(notes, list) or index < 0 or index >= len(notes):
        return False
    notes.pop(index)
    return True


def clear_notes(char: dict) -> bool:
    if not isinstance(char, dict):
        return False
    char["player_notes"] = []
    return True


def render_notes_for_master(char: dict, max_items: int = 8) -> str:
    notes = get_notes(char)[-max_items:]
    if not notes:
        return ""
    lines = ["=== ЗАМЕТКИ ИГРОКА ==="]
    for n in notes:
        tag = n.get("tag") or ""
        prefix = ("[" + tag + "] ") if tag else ""
        lines.append("- " + prefix + str(n.get("text", "")))
    return "\n".join(lines)
