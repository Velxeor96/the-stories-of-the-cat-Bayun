"""Интеграционный тест: симуляция игры (PATCH_100)."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest

from core.config import Config
from services.orchestrator import Orchestrator
from services.character_creation import build_character
from services.state_manager import parse_and_apply
from tests.fakes import patch_master, patch_analyst, patch_moderator

# Фейковые ответы для Orchestrator
FAKE_MOD = '{"verdict": "ALLOW", "redirect": ""}'
FAKE_ANALYST = '{"action": "move", "target": "коридор", "skill": null, "roll_needed": false, "difficulty": "Ordinary", "raw": "Иду"}'
FAKE_MASTER = "Вы идете по коридору.\n[STATE]\nxp=+10\nwounds=-1\n[/STATE]"

def test_full_20_turns():
    """Симулирует 20 ходов. Проверяет стабильность и работу [STATE]."""
    cfg = Config.load()
    # Отключаем RAG для теста, чтобы не грузить ChromaDB
    orch = Orchestrator(cfg, use_rag=False)

    # Подменяем LLM на фейки
    patch_moderator(orch.moderator, FAKE_MOD)
    patch_analyst(orch.analyst, FAKE_ANALYST)
    patch_master(orch.master, FAKE_MASTER)

    # Создаем персонажа
    char = build_character(
        name="TestHero", gender="male", age="30",
        appearance="Tall", user_background="Noble",
        faction_id="imperium", subfaction_id="rogue_trader",
        characteristics={"WS": 40, "BS": 40, "S": 40, "T": 40, "Ag": 40, "Int": 40, "Per": 40, "WP": 40, "Fel": 40}
    )

    initial_xp = char["xp"]
    initial_wounds = char["wounds"]["current"]

    # Симулируем 20 ходов
    for i in range(20):
        res = orch.process_turn("Иду вперёд", char, history=[])
        
        # Проверяем, что модератор и мастер не заблокировали ход
        assert not res.blocked, f"Ход {i} заблокирован"
        assert "Вы идете по коридору" in res.narrative
        
        # Применяем [STATE], как это делает ui/screens/game.py
        clean_text, applied, updated_char = parse_and_apply(res.narrative, char)
        char = updated_char
        
        # Проверяем, что изменения применились
        assert "xp" in applied
        assert "wounds" in applied

    # Проверяем конечное состояние
    assert char["xp"] == initial_xp + 200, "XP должен вырасти на 200 (10 * 20)"
    
    # Раны не должны уйти в минус (валидация в state_manager)
    expected_wounds = max(0, initial_wounds - 20)
    assert char["wounds"]["current"] == expected_wounds, "Раны должны быть на нуле или выше"
