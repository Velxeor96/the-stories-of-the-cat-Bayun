r"""
Одноразовая миграция: добавить session_id/player_id/character_id
во все character.json в папке characters/.

Пропускает файлы *.chat.json — их обрабатывает fix_chat_ids.py.

Запуск (из корня проекта):
    python scripts\migrate_add_ids.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.state import CharacterState  # noqa: E402


def migrate_file(path: Path) -> bool:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    state = CharacterState(data, path)
    before = {k: data.get(k) for k in ("session_id", "player_id", "character_id")}
    ids = state.ensure_ids()
    after = {k: data.get(k) for k in ("session_id", "player_id", "character_id")}

    if before == after:
        print(f"[--] {path.name}: ID уже есть, пропуск")
        return False

    state.save()
    print(f"[OK] {path.name}: session={ids['session_id'][:8]}... "
          f"player={ids['player_id'][:8]}... char={ids['character_id'][:8]}...")
    return True


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    chars_dir = root / "characters"
    if not chars_dir.exists():
        print(f"Нет папки {chars_dir}")
        sys.exit(1)

    files = [f for f in chars_dir.glob("*.json") if not f.name.endswith(".chat.json")]

    if not files:
        print("Персонажей не найдено.")
        return

    changed = 0
    for f in files:
        try:
            if migrate_file(f):
                changed += 1
        except Exception as e:
            print(f"[ERR] {f.name}: {e}")

    print(f"\nГотово. Обновлено файлов: {changed} из {len(files)}.")


if __name__ == "__main__":
    main()