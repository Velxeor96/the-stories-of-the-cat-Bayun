import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "game.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS characters (
                login TEXT, name TEXT, data TEXT,
                PRIMARY KEY (login, name)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                login TEXT, character TEXT, role TEXT, text TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                login TEXT PRIMARY KEY, data TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS accounts (
                login TEXT PRIMARY KEY, data TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_settings (
                login TEXT PRIMARY KEY, data TEXT
            )
        """)
