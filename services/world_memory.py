"""services/world_memory.py — Память мира (убитые NPC, события)."""
import json
from contextlib import closing
from persistence.db import get_conn, init_db
from core.logger import get_logger

logger = get_logger(__name__)

def add_memory(login: str, character: str, event_text: str) -> None:
    if not event_text or len(event_text) < 5:
        return
    try:
        init_db()
        with closing(get_conn()) as conn, conn:
            conn.execute(
                "INSERT INTO world_memory (login, character, event_text) VALUES (?, ?, ?)",
                (login, character, event_text)
            )
        logger.info(f"World memory added: {event_text[:50]}")
    except Exception as e:
        logger.error(f"Failed to add world memory: {e}")

def get_memory(login: str, character: str, limit: int = 10) -> list[str]:
    try:
        init_db()
        with closing(get_conn()) as conn, conn:
            rows = conn.execute(
                "SELECT event_text FROM world_memory WHERE login=? AND character=? ORDER BY id DESC LIMIT ?",
                (login, character, limit)
            ).fetchall()
        return [r["event_text"] for r in reversed(rows)]
    except Exception as e:
        logger.error(f"Failed to load world memory: {e}")
        return []
