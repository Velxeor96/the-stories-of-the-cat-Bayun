"""persistence/characters.py — сохранение персонажей (cloud-aware)."""
from __future__ import annotations
import json
import re
from pathlib import Path
from persistence import cloud_store

_ROOT = Path(__file__).resolve().parents[1]
_USERS_DIR = _ROOT / "data" / "users"
_NAME_RE = re.compile(r"^[\w\- ]{1,48}$", re.UNICODE)


class CharacterError(Exception):
    pass


def _chars_dir(login: str) -> Path:
    d = _USERS_DIR / login / "characters"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _cloud_ns(login: str) -> str:
    return "chars:" + login


def validate_name(name: str) -> tuple:
    if not name or not name.strip():
        return False, "Имя не может быть пустым"
    if not _NAME_RE.match(name.strip()):
        return False, "Имя: 1-48 символов, буквы, цифры, пробел, _, -"
    return True, ""


def list_characters(login: str) -> list:
    if cloud_store.is_configured():
        return sorted(cloud_store.hkeys(_cloud_ns(login)))
    return sorted(p.stem for p in _chars_dir(login).glob("*.json"))


def character_path(login: str, name: str) -> Path:
    return _chars_dir(login) / (name + ".json")


def load_character(login: str, name: str) -> dict:
    if cloud_store.is_configured():
        data = cloud_store.hget_json(_cloud_ns(login), name)
        if data is None:
            raise CharacterError("Персонаж " + repr(name) + " не найден")
        return data
    p = character_path(login, name)
    if not p.exists():
        raise CharacterError("Персонаж " + repr(name) + " не найден")
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        raise CharacterError("Не читается " + p.name + ": " + str(e)) from e


def save_character(login: str, name: str, data: dict) -> None:
    ok, err = validate_name(name)
    if not ok:
        raise CharacterError(err)
    if cloud_store.is_configured():
        if cloud_store.hset_json(_cloud_ns(login), name, data):
            return
        print("[characters] cloud fail → local")
    p = character_path(login, name)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def delete_character(login: str, name: str) -> None:
    if cloud_store.is_configured():
        cloud_store.hdel(_cloud_ns(login), name)
    p = character_path(login, name)
    if p.exists():
        p.unlink()


def has_any(login: str) -> bool:
    return bool(list_characters(login))
