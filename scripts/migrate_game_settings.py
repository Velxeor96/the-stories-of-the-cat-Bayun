"""Домиграция game_settings.json → таблица settings."""
import sys
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from persistence.db import get_conn, init_db


def migrate():
    print("=== Миграция game_settings.json ===")
    init_db()

    users_dir = ROOT / "data" / "users"
    if not users_dir.exists():
        print("Нет папки users")
        return

    count = 0
    for user_dir in users_dir.iterdir():
        if not user_dir.is_dir():
            continue
        login = user_dir.name
        game_settings = user_dir / "game_settings.json"
        if not game_settings.exists():
            continue
        try:
            data = json.loads(game_settings.read_text(encoding="utf-8"))
            with get_conn() as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO settings (login, data) "
                    "VALUES (?, ?)",
                    (login, json.dumps(data, ensure_ascii=False)),
                )
            print(f"[JSON] Игровые настройки: {login}")
            count += 1
        except Exception as e:
            print(f"[Ошибка] {game_settings}: {e}")

    print(f"=== Готово: {count} ===")


if __name__ == "__main__":
    migrate()
