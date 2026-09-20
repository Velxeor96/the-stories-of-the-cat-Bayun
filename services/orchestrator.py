# PATCH_6B_7_V2
"""services/orchestrator.py — полный цикл одного хода."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from core.config import Config
from core.roll_engine import RollResult, check as roll_check
from services.analyst import Analyst, ParsedCommand
from services.master import Master
from services.moderator import ModerationResult, Moderator
from services.rag import get_kb
from services.variants import ensure_action_variants

DEFAULT_SKILL_VALUE = 45


@dataclass
class TurnResult:
    player_input: str
    moderation: ModerationResult
    command: Optional[ParsedCommand] = None
    roll: Optional[RollResult] = None
    narrative: str = ""
    rag_sources: list = field(default_factory=list)
    rag_chunks: int = 0

    @property
    def blocked(self) -> bool:
        return self.moderation.verdict != "ALLOW"

    def to_dict(self) -> dict:
        return {
            "player_input": self.player_input,
            "blocked": self.blocked,
            "moderation": {
                "verdict": self.moderation.verdict,
                "reason": self.moderation.reason,
                "matched_rule": self.moderation.matched_rule,
            },
            "command": self.command.to_dict() if self.command else None,
            "roll": self.roll.to_dict() if self.roll else None,
            "narrative": self.narrative,
            "rag_chunks": self.rag_chunks,
            "rag_sources": list(self.rag_sources),
        }


class Orchestrator:
    def __init__(self, config: Config, *, use_rag: bool = True):
        self.config = config
        self.master = Master(config)
        self.moderator = Moderator(config)
        self.analyst = Analyst(config)
        self.use_rag = use_rag
        self._kb = None

    @property
    def kb(self):
        if not self.use_rag:
            return None
        if self._kb is None:
            self._kb = get_kb()
        return self._kb

    def process_turn(self, player_input: str, state: Any,
                     *, history: Optional[list] = None) -> TurnResult:
        mod = self.moderator.check(player_input)
        if mod.verdict != "ALLOW":
            redirect = (mod.redirect or "").strip() or "Ты возвращаешься к сцене."
            narrative = ensure_action_variants(redirect)
            return TurnResult(
                player_input=player_input, moderation=mod, narrative=narrative,
            )

        command = self.analyst.parse(player_input)
        print(f"[analyst] action={command.action} skill={command.skill} "
              f"roll_needed={command.roll_needed} diff={command.difficulty}")

        roll = None
        if command.roll_needed:
            skill = command.skill
            if not skill:
                print("[orchestrator] roll_needed=True без skill → fallback на Per")
                skill = "Per"
            base = self._lookup_skill(state, skill)
            print(f"[orchestrator] base({skill})={base}")
            roll = roll_check(base, difficulty=command.difficulty, reason=skill)
            try:
                d = roll.to_dict()
                verdict = "SUCCESS" if d.get("success") else "FAIL"
                print(f"[orchestrator] roll: d100={d.get('roll')} vs "
                      f"{d.get('target')} → {verdict} (deg {d.get('degrees')})")
            except Exception:
                print(f"[orchestrator] roll: {roll!r}")

        rag_ctx = ""
        rag_sources: list = []
        rag_n = 0
        if self.kb is not None:
            enriched = self._enrich_query(player_input, command)
            try:
                chunks = self.kb.search(enriched, top_k=4) or []
                rag_n = len(chunks)
                if chunks:
                    rag_ctx = self.kb.format_context(enriched, top_k=4)
                    rag_sources = self._extract_sources(chunks)
                print(f"[orchestrator] RAG q={enriched[:70]!r} → {rag_n} chunks")
            except Exception as e:
                print(f"[orchestrator] RAG ошибка: {e}")
                rag_ctx = ""

        narrative = self.master.narrate(
            state, command, roll=roll, history=history or [],
            extra_context=rag_ctx,
        )
        narrative = ensure_action_variants(narrative)

        return TurnResult(
            player_input=player_input, moderation=mod,
            command=command, roll=roll, narrative=narrative,
            rag_sources=rag_sources, rag_chunks=rag_n,
        )

    @staticmethod
    def _enrich_query(player_input: str, command: ParsedCommand) -> str:
        parts: list[str] = [player_input]
        if command.target:
            parts.append(str(command.target))
        if command.action and command.action != "other":
            parts.append(command.action.replace("_", " "))
        if command.skill:
            parts.append(command.skill)
        return " ".join(p for p in parts if p).strip()

    @staticmethod
    def _extract_sources(chunks: list) -> list:
        out: list[str] = []
        for c in chunks:
            if isinstance(c, dict):
                src = c.get("source") or (c.get("metadata") or {}).get("source")
            else:
                src = getattr(c, "source", None)
            if src:
                out.append(str(src))
        return out

    @staticmethod
    def _lookup_skill(state: Any, skill: str) -> int:
        """Рекурсивный path-lookup: 'characteristics.Per' → state['characteristics']['Per']."""
        if not skill:
            return DEFAULT_SKILL_VALUE

        paths = [
            f"characteristics.{skill}",
            f"characteristics.{skill.upper()}",
            f"characteristics.{skill.capitalize()}",
            f"skills.{skill}",
        ]
        for path in paths:
            v = Orchestrator._get_by_path(state, path)
            if isinstance(v, (int, float)):
                return int(v)
            if isinstance(v, dict) and "value" in v:
                try:
                    return int(v["value"])
                except (TypeError, ValueError):
                    pass

        chars = Orchestrator._get_by_path(state, "characteristics")
        if isinstance(chars, dict):
            sk_low = skill.lower()
            for k, v in chars.items():
                if str(k).lower() == sk_low and isinstance(v, (int, float)):
                    return int(v)

        return DEFAULT_SKILL_VALUE

    @staticmethod
    def _get_by_path(state: Any, path: str) -> Any:
        """Универсальный обход: dict['a']['b'] или obj.a.b."""
        cur = state
        for part in path.split("."):
            if isinstance(cur, dict):
                if part in cur:
                    cur = cur[part]
                    continue
                return None
            if hasattr(cur, part):
                cur = getattr(cur, part)
                continue
            return None
        return cur
