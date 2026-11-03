"""tests/test_module_loader.py"""
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
