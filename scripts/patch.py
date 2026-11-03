# scripts/patch.py — PATCH_95
# Создание единого загрузчика модулей (Module Loader) с fallback на старые пути.
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG = []

MODULE_LOADER_PY = '''"""services/module_loader.py — Единая точка доступа к данным фракций.

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
'''

TEST_MODULE_LOADER = '''"""tests/test_module_loader.py"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.module_loader import get_faction_data, get_archetype, list_archetypes

def test_loader_fallback_to_old_path():
    # imperial_guard.json сейчас лежит в старом пути data/imperial_guard.json
    data = get_faction_data("imperial_guard")
    assert data, "Данные не загрузились"
    assert "archetypes" in data
    assert len(data["archetypes"]) > 0

def test_get_archetype():
    arch = get_archetype("imperial_guard", "sergeant")
    assert arch, "Архетип sergeant не найден"
    assert arch.get("name") == "Сержант"

def test_list_archetypes():
    archs = list_archetypes("imperial_guard")
    assert len(archs) > 5

def test_missing_faction_returns_empty():
    data = get_faction_data("non_existent_faction")
    assert data == {}
'''

def main() -> int:
    print("=== PATCH_95: Module Loader ===\n")
    
    # 1. Создать сервис
    svc_path = ROOT / "services" / "module_loader.py"
    if not svc_path.exists():
        svc_path.write_text(MODULE_LOADER_PY, encoding="utf-8")
        LOG.append(f"[CREATE] services/module_loader.py")
    else:
        LOG.append(f"[SKIP] services/module_loader.py already exists")

    # 2. Создать тест
    test_path = ROOT / "tests" / "test_module_loader.py"
    if not test_path.exists():
        test_path.write_text(TEST_MODULE_LOADER, encoding="utf-8")
        LOG.append(f"[CREATE] tests/test_module_loader.py")
    else:
        LOG.append(f"[SKIP] tests/test_module_loader.py already exists")

    print("\n".join(LOG))
    print("\n=== ПРОВЕРКИ ===")
    print("Запустите: python -m pytest tests/test_module_loader.py -q")
    print("\nDONE — PATCH_95. Module Loader создан.")
    return 0

if __name__ == "__main__":
    sys.exit(main())