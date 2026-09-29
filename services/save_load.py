# PATCH_17
"""services/save_load.py — экспорт/импорт листа персонажа в .json-файл."""
from __future__ import annotations

import json
from datetime import datetime
from io import BytesIO


def export_character_json(char: dict) -> bytes:
    payload = {
        "format": "wh40k_character_v1",
        "exported_at": datetime.now().isoformat(timespec="seconds"),
        "character": char,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")


def import_character_json(data: bytes) -> tuple[dict | None, str]:
    try:
        obj = json.loads(data.decode("utf-8"))
    except Exception as e:
        return None, "Не удалось прочитать JSON: " + str(e)
    if not isinstance(obj, dict):
        return None, "Ожидался JSON-объект."
    if "character" in obj and isinstance(obj["character"], dict):
        return obj["character"], ""
    if "name" in obj and "characteristics" in obj:
        return obj, ""
    return None, "Не найден раздел 'character' или базовые поля."
