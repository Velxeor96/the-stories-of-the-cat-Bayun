"""Тесты Master с FakeLLM — 0 руб на API."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest

from services.analyst import ParsedCommand
from core.config import Config
from services.master import Master
from tests.fakes import (
    FAKE_MASTER_SCENE,
    FAKE_MASTER_SCENE_WITH_VARIANTS,
    patch_master,
)


class _FakeState(dict):
    """Мини-заглушка: Master ожидает dict-подобный state."""
    def __init__(self, **kw):
        super().__init__({
            "name": "Тест-Костопевец",
            "faction": "Эльдары",
            "subfaction": "Асуряни",
            "wounds": {"current": 10, "max": 10},
            "characteristics": {"WS": 40, "BS": 40, "S": 40, "T": 40,
                                "Ag": 40, "Int": 40, "Per": 40,
                                "WP": 40, "Fel": 40},
            **kw,
        })


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


def test_response_not_empty(master: Master) -> None:
    patch_master(master, FAKE_MASTER_SCENE)
    text = master.narrate(_FakeState(), _cmd())
    assert isinstance(text, str)
    assert len(text.strip()) > 50


def test_no_service_markers(master: Master) -> None:
    """Master не должен сам добавлять [STATE], эмодзи кубика и т.п."""
    patch_master(master, FAKE_MASTER_SCENE)
    text = master.narrate(_FakeState(), _cmd())
    assert "[STATE]" not in text
    assert "wounds=" not in text


def test_variants_passthrough(master: Master) -> None:
    """Если fake LLM вернул варианты — они в ответе."""
    patch_master(master, FAKE_MASTER_SCENE_WITH_VARIANTS)
    text = master.narrate(_FakeState(), _cmd())
    assert "Варианты действий" in text
    assert "Иное: опиши" in text


def test_no_duplicate_variants(master: Master) -> None:
    """Fake вернул варианты один раз — не должно быть двух 'Иное: опиши'."""
    patch_master(master, FAKE_MASTER_SCENE_WITH_VARIANTS)
    text = master.narrate(_FakeState(), _cmd())
    assert text.count("Иное: опиши") == 1


def test_history_accepted(master: Master) -> None:
    """Master принимает history без падения."""
    patch_master(master, FAKE_MASTER_SCENE)
    history = [
        {"role": "player", "text": "Иду к докам"},
        {"role": "master", "text": "Ты идёшь по коридору."},
    ]
    text = master.narrate(_FakeState(), _cmd(), history=history)
    assert isinstance(text, str)
    assert len(text.strip()) > 20


def test_roll_passed(master: Master) -> None:
    """Master принимает roll без падения."""
    from core.roll_engine import check
    r = check(45, reason="Внимание")
    patch_master(master, FAKE_MASTER_SCENE)
    text = master.narrate(_FakeState(), _cmd(), roll=r)
    assert isinstance(text, str)
