r"""
Синхронизация ID: chat.json должен ссылаться на те же
session_id / player_id / character_id, что и одноимённый character.json.

Запуск (из корня проекта):
    python scripts\fix_chat_ids.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.state import CharacterState  # noqa: E402


def sync_pair(char_path: Path, chat_path: Path) -> bool:
    """Возвращает True, если что-то изменилось."""
    if not chat_path.exists():
        return False

    char_state = CharacterState.load(char_path)
    ids = char_state.ensure_ids()

    with chat_path.open("r", encoding="utf-8") as f:
        chat_data = json.load(f)

    changed = False
    for key in ("session_id", "player_id", "character_id"):
        if chat_data.get(key) != ids[key]:
            chat_data[key] = ids[key]
            changed = True

    if not changed:
        print(f"[--] {chat_path.name}: ID уже совпадают")
        return False

    tmp = chat_path.with_suffix(chat_path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(chat_data, f, ensure_ascii=False, indent=2)
    tmp.replace(chat_path)

    print(f"[OK] {chat_path.name}: IDs синхронизированы с {char_path.name}")
    return True


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    chars_dir = root / "characters"
    if not chars_dir.exists():
        print(f"Нет папки {chars_dir}")
        sys.exit(1)

    chats = list(chars_dir.glob("*.chat.json"))
    if not chats:
        print("Файлов *.chat.json не найдено.")
        return

    changed = 0
    for chat in chats:
        char_name = chat.name[: -len(".chat.json")] + ".json"
        char_path = chars_dir / char_name
        if not char_path.exists():
            print(f"[!!] {chat.name}: нет пары {char_name}, пропуск")
            continue
        try:
            if sync_pair(char_path, chat):
                changed += 1
        except Exception as e:
            print(f"[ERR] {chat.name}: {e}")

    print(f"\nГотово. Синхронизировано: {changed} из {len(chats)}.")


if __name__ == "__main__":
    main()