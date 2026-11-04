import sys
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from persistence.db import get_conn, init_db
from persistence import cloud_store

def migrate():
    print("=== Миграция данных в SQLite ===")
    init_db()

    # 1. Локальные JSON
    users_dir = ROOT / "data" / "users"
    if users_dir.exists():
        for user_dir in users_dir.iterdir():
            if not user_dir.is_dir():
                continue
            login = user_dir.name
            
            chars_dir = user_dir / "characters"
            if chars_dir.exists():
                for char_file in chars_dir.glob("*.json"):
                    name = char_file.stem
                    try:
                        data = json.loads(char_file.read_text(encoding="utf-8"))
                        with get_conn() as conn:
                            conn.execute("INSERT OR REPLACE INTO characters (login, name, data) VALUES (?, ?, ?)", (login, name, json.dumps(data, ensure_ascii=False)))
                        print(f"[JSON] Персонаж: {login} / {name}")
                    except Exception as e:
                        print(f"[Ошибка] {char_file}: {e}")
            
            chats_dir = user_dir / "chats"
            if chats_dir.exists():
                for chat_file in chats_dir.glob("*.json"):
                    character = chat_file.stem
                    try:
                        history = json.loads(chat_file.read_text(encoding="utf-8"))
                        if not isinstance(history, list): continue
                        with get_conn() as conn:
                            conn.execute("DELETE FROM chats WHERE login = ? AND character = ?", (login, character))
                            for item in history:
                                conn.execute("INSERT INTO chats (login, character, role, text) VALUES (?, ?, ?, ?)", (login, character, item.get("role", ""), item.get("text", "")))
                        print(f"[JSON] Чат: {login} / {character} ({len(history)} сообщений)")
                    except Exception as e:
                        print(f"[Ошибка] {chat_file}: {e}")

            settings_file = user_dir / "settings.json"
            if settings_file.exists():
                try:
                    data = json.loads(settings_file.read_text(encoding="utf-8"))
                    with get_conn() as conn:
                        conn.execute("INSERT OR REPLACE INTO user_settings (login, data) VALUES (?, ?)", (login, json.dumps(data, ensure_ascii=False)))
                    print(f"[JSON] Настройки: {login}")
                except Exception as e:
                    print(f"[Ошибка] {settings_file}: {e}")

    # Аккаунты (JSON)
    accounts_dir = ROOT / "data" / "accounts"
    if accounts_dir.exists():
        for acc_file in accounts_dir.glob("*.json"):
            login = acc_file.stem
            try:
                data = json.loads(acc_file.read_text(encoding="utf-8"))
                with get_conn() as conn:
                    conn.execute("INSERT OR REPLACE INTO accounts (login, data) VALUES (?, ?)", (login, json.dumps(data, ensure_ascii=False)))
                print(f"[JSON] Аккаунт: {login}")
            except Exception as e:
                print(f"[Ошибка] {acc_file}: {e}")

    # 2. Миграция из Gist
    if cloud_store.is_configured():
        print("\nНайден GitHub Gist. Начинаю миграцию из облака...")
        try:
            data = cloud_store._load_gist()
            if not data:
                print("[Gist] Данные пусты или не удалось загрузить.")
                return
            
            for ns, obj in data.items():
                if not isinstance(obj, dict): continue
                
                if ns.startswith("chars:"):
                    login = ns[6:]
                    for name, char_data in obj.items():
                        try:
                            with get_conn() as conn:
                                conn.execute("INSERT OR REPLACE INTO characters (login, name, data) VALUES (?, ?, ?)", (login, name, json.dumps(char_data, ensure_ascii=False)))
                            print(f"[Gist] Персонаж: {login} / {name}")
                        except Exception as e:
                            print(f"[Gist] Ошибка {login}/{name}: {e}")
                            
                elif ns.startswith("chats:"):
                    login = ns[6:]
                    for character, history in obj.items():
                        if not isinstance(history, list): continue
                        try:
                            with get_conn() as conn:
                                conn.execute("DELETE FROM chats WHERE login = ? AND character = ?", (login, character))
                                for item in history:
                                    conn.execute("INSERT INTO chats (login, character, role, text) VALUES (?, ?, ?, ?)", (login, character, item.get("role", ""), item.get("text", "")))
                            print(f"[Gist] Чат: {login} / {character} ({len(history)} сообщений)")
                        except Exception as e:
                            print(f"[Gist] Ошибка чата {login}/{character}: {e}")
                
                elif ns == "accounts":
                    for login, acc_data in obj.items():
                        try:
                            with get_conn() as conn:
                                conn.execute("INSERT OR REPLACE INTO accounts (login, data) VALUES (?, ?)", (login, json.dumps(acc_data, ensure_ascii=False)))
                            print(f"[Gist] Аккаунт: {login}")
                        except Exception as e:
                            print(f"[Gist] Ошибка аккаунта {login}: {e}")
                            
                elif ns == "settings":
                    for login, s_data in obj.items():
                        try:
                            with get_conn() as conn:
                                conn.execute("INSERT OR REPLACE INTO user_settings (login, data) VALUES (?, ?)", (login, json.dumps(s_data, ensure_ascii=False)))
                            print(f"[Gist] Настройки: {login}")
                        except Exception as e:
                            print(f"[Gist] Ошибка настроек {login}: {e}")

        except Exception as e:
            print(f"[Gist] Ошибка миграции: {type(e).__name__}: {e}")

    print("\n=== Миграция завершена ===")

if __name__ == "__main__":
    migrate()
