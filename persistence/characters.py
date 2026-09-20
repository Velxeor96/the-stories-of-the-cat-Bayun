"""persistence/characters.py — сохранение и загрузка листов персонажей."""
from __future__ import annotations

import json
import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_USERS_DIR = _ROOT / "data" / "users"
_NAME_RE = re.compile(r"^[\w\- ]{1,48}$", re.UNICODE)


class CharacterError(Exception):
    """Ошибка работы с персонажем."""


def _chars_dir(login: str) -> Path:
    d = _USERS_DIR / login / "characters"
    d.mkdir(parents=True, exist_ok=True)
    return d


def validate_name(name: str) -> tuple[bool, str]:
    if not name or not name.strip():
        return False, "Имя не может быть пустым"
    if not _NAME_RE.match(name.strip()):
        return False, "Имя: 1–48 символов, буквы, цифры, пробел, _, -"
    return True, ""


def list_characters(login: str) -> list[str]:
    return sorted(p.stem for p in _chars_dir(login).glob("*.json"))


def character_path(login: str, name: str) -> Path:
    return _chars_dir(login) / f"{name}.json"


def load_character(login: str, name: str) -> dict:
    p = character_path(login, name)
    if not p.exists():
        raise CharacterError(f"Персонаж {name!r} не найден")
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        raise CharacterError(f"Не читается {p.name}: {e}") from e


def save_character(login: str, name: str, data: dict) -> None:
    ok, err = validate_name(name)
    if not ok:
        raise CharacterError(err)
    p = character_path(login, name)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def delete_character(login: str, name: str) -> None:
    p = character_path(login, name)
    if p.exists():
        p.unlink()


def has_any(login: str) -> bool:
    return bool(list_characters(login))
