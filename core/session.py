"""Сессия игры: CharacterState + история Turn[] + сохранение/загрузка.

Не содержит логики правил — только связка и персистентность. Оркестратор
делает ход, Session хранит результат и умеет сохраняться в JSON.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from core.master import Turn
from core.orchestrator import Orchestrator, TurnResult


class SessionError(Exception):
    """Ошибка сессии."""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class Session:
    """Одна игровая сессия.

    Содержит оркестратор (для хода), состояние персонажа и историю.
    Сохраняется в JSON: state + история + метаданные.
    """

    orchestrator: Orchestrator
    state: Any
    history: list[Turn] = field(default_factory=list)
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)
    path: Optional[Path] = None
    history_limit: int = 50

    # ---------- Создание ----------

    @classmethod
    def new(
        cls,
        orchestrator: Orchestrator,
        state: Any,
        *,
        path: Optional[Path] = None,
    ) -> "Session":
        return cls(orchestrator=orchestrator, state=state, path=path)

    # ---------- Ход ----------

    def take_turn(self, player_input: str) -> TurnResult:
        """Один ход: оркестратор + запись в историю + автосохранение (если path)."""
        result = self.orchestrator.process_turn(
            player_input, self.state, history=self.history
        )
        self.history.append(Turn(player=player_input, master=result.narrative))
        if len(self.history) > self.history_limit:
            self.history = self.history[-self.history_limit:]
        self.updated_at = _now_iso()
        if self.path is not None:
            self.save()
        return result

    # ---------- Сохранение / загрузка ----------

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "state": self.state.to_dict(),
            "history": [t.to_dict() for t in self.history],
        }

    def save(self, path: Optional[Path] = None) -> Path:
        target = Path(path) if path is not None else self.path
        if target is None:
            raise SessionError("Не указан путь для сохранения")
        target = Path(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self.path = target
        return target

    @classmethod
    def load(
        cls,
        path: Path,
        orchestrator: Orchestrator,
        *,
        state_factory: Any,
    ) -> "Session":
        """Загружает сессию. state_factory — функция dict → CharacterState."""
        path = Path(path)
        if not path.exists():
            raise SessionError(f"Файл сессии не найден: {path}")
        data = json.loads(path.read_text(encoding="utf-8"))

        state = state_factory(data["state"])
        history = [
            Turn(player=t["player"], master=t["master"])
            for t in data.get("history", [])
        ]
        s = cls(
            orchestrator=orchestrator,
            state=state,
            history=history,
            session_id=data.get("session_id", str(uuid.uuid4())),
            created_at=data.get("created_at", _now_iso()),
            updated_at=data.get("updated_at", _now_iso()),
            path=path,
        )
        return s
