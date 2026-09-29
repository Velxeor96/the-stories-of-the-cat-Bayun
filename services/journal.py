# PATCH_28
"""services/journal.py — дневник персонажа."""
from __future__ import annotations
from datetime import datetime


def get_entries(char: dict) -> list:
    if not isinstance(char, dict):
        return []
    j = char.get("journal")
    if not isinstance(j, list):
        j = []
        char["journal"] = j
    return j


def add_entry(char: dict, text: str, kind: str = "note") -> bool:
    if not isinstance(char, dict):
        return False
    text = (text or "").strip()
    if not text:
        return False
    j = get_entries(char)
    j.append({
        "text": text, "kind": kind,
        "ts": datetime.now().isoformat(timespec="seconds"),
    })
    return True


def remove_entry(char: dict, index: int) -> bool:
    j = get_entries(char)
    if index < 0 or index >= len(j):
        return False
    j.pop(index)
    return True


def auto_log_turn(char: dict, player_input: str, narrative: str) -> None:
    """Автозапись после хода (короткая выдержка)."""
    if not isinstance(char, dict):
        return
    text = (narrative or "").strip()
    if not text:
        return
    line = "→ " + (player_input or "").strip()[:80] + "\n"
    line += text[:300]
    add_entry(char, line, kind="turn")
