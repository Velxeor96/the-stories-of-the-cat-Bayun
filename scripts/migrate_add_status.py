r"""
Миграция: добавить поле "status" в character.json.

Допустимые значения (см. core/death.py):
    "alive", "dying", "dead", "retired".

Идемпотентно: повторный запуск ничего не меняет.

Запуск (из корня проекта):
    python scripts\migrate_add_status.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.state import CharacterState  # noqa: E402

DEFAULT_STATUS = "alive"


def migrate_file(path: Path) -> bool:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if data.get("status") == DEFAULT_STATUS:
        print(f"[--] {path.name}: status='{DEFAULT_STATUS}' уже есть")
        return False

    state = CharacterState(data, path)
    before = state.get("status")
    state.set("status", DEFAULT_STATUS)
    state.save()

    print(f"[OK] {path.name}: status '{before}' → '{DEFAULT_STATUS}'")
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