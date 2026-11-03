"""services/module_loader.py — Единая точка доступа к данным фракций.

PATCH_95: Внедрение модульной архитектуры.
Сначала ищем в data/modules/<active_module>/factions/, затем падаем
на старые пути (data/<faction_id>.json).
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Optional, Any

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
MODULES_DIR = DATA_DIR / "modules"

# Пока активен только один модуль
ACTIVE_MODULE = "rogue_trader"

_CACHE: dict[str, dict] = {}

def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[module_loader] Error loading {path}: {e}")
        return {}

def get_faction_data(faction_id: str) -> dict:
    """Загружает данные фракции. Ищет в модулях, потом в старых путях."""
    if faction_id in _CACHE:
        return _CACHE[faction_id]

    # 1. Новый путь (модульный)
    new_path = MODULES_DIR / ACTIVE_MODULE / "factions" / f"{faction_id}.json"
    if new_path.exists():
        data = _load_json(new_path)
        _CACHE[faction_id] = data
        return data

    # 2. Старый путь (fallback)
    old_path = DATA_DIR / f"{faction_id}.json"
    if old_path.exists():
        data = _load_json(old_path)
        _CACHE[faction_id] = data
        return data

    # 3. Нет данных
    print(f"[module_loader] Warning: no data found for faction '{faction_id}'")
    _CACHE[faction_id] = {}
    return {}

def get_archetype(faction_id: str, archetype_id: str) -> dict:
    data = get_faction_data(faction_id)
    for a in data.get("archetypes", []):
        if a.get("id") == archetype_id:
            return a
    return {}

def list_archetypes(faction_id: str) -> list:
    return get_faction_data(faction_id).get("archetypes", [])

def get_home_worlds(faction_id: str) -> list:
    return get_faction_data(faction_id).get("home_worlds", [])

def clear_cache():
    _CACHE.clear()
