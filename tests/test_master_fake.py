"""Тесты Master с FakeLLM — 0 ₽ на API.

Проверяют инварианты ответа Мастера:
  - Блок «Варианты действий» + «Иное: опиши» присутствует всегда.
  - Если модель сама вернула блок — он не дублируется.
  - Служебных маркеров ([STATE], key=value, эмодзи кубика) нет.
  - Ответ не пустой.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest

from core.analyst import ParsedCommand
from core.config import Config
from core.master import Master
from tests.fakes import (
    FAKE_MASTER_SCENE,
    FAKE_MASTER_SCENE_WITH_VARIANTS,
    patch_master,
)


class _FakeState:
    """Минимальная заглушка CharacterState — нужен только get_summary()."""
    def get_summary(self) -> str:
        return "Имя: Тест-Костопевец\nРаны: 10/10"


def _cmd(text: str = "осмотреться") -> ParsedCommand:
    return ParsedCommand(
        action="observe",
        target=None,
        skill="Per",
        roll_needed=False,
        difficulty="Ordinary",
        raw=text,
    )


@pytest.fixture
def master() -> Master:
    cfg = Config.load()
    return Master(cfg)


def test_fallback_when_model_forgot_variants(master: Master) -> None:
    """Модель забыла блок вариантов — Python дописывает fallback."""
    patch_master(master, FAKE_MASTER_SCENE)
    text = master.narrate(_FakeState(), _cmd())
    assert "Варианты действий" in text
    assert "Иное: опиши" in text


def test_no_duplicate_when_variants_present(master: Master) -> None:
    """Модель сама вернула блок — не дублируем."""
    patch_master(master, FAKE_MASTER_SCENE_WITH_VARIANTS)
    text = master.narrate(_FakeState(), _cmd())
    assert text.count("Иное: опиши") == 1


def test_no_service_markers(master: Master) -> None:
    """Никаких [STATE], key=value, эмодзи кубика в ответе."""
    patch_master(master, FAKE_MASTER_SCENE)
    text = master.narrate(_FakeState(), _cmd())
    assert "[STATE]" not in text
    assert "🎲" not in text
    assert "wounds=" not in text


def test_response_not_empty(master: Master) -> None:
    patch_master(master, FAKE_MASTER_SCENE)
    text = master.narrate(_FakeState(), _cmd())
    assert len(text.strip()) > 50


def test_variants_contains_inoe_last(master: Master) -> None:
    """«Иное: опиши» — последний пункт блока."""
    patch_master(master, FAKE_MASTER_SCENE)
    text = master.narrate(_FakeState(), _cmd())
    idx = text.rfind("Иное: опиши")
    assert idx != -1
    after = text[idx + len("Иное: опиши"):].strip()
    # Реальный формат: "4. **Иное: опиши.**" — после слова идёт ".**"
    assert after in ("", ".", ".**"), f"После 'Иное' что-то есть: {after!r}"
