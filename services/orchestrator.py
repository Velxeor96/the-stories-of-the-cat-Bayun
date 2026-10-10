# PATCH_18
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


# PATCH_68: continuation + choice hint
def _parse_master_choices(text: str) -> list[str]:
    """Извлекает список вариантов действий из последнего ответа мастера."""
    if not text:
        return []
    import re as _re
    m = _re.search(
        r"(?i)(?:\*\*)?(варианты\s+действий|варианты)(?:\*\*)?[^\n]*\n((?:.|\n)*)",
        text,
    )
    if not m:
        return []
    block = m.group(2)
    entries: dict = {}
    for line in block.split("\n"):
        mm = _re.match(
            r"^\s*(\d+)\.\s+\*\*(.+?)\*\*[.\s]*(.*)$",
            line.strip(),
        )
        if mm:
            n = int(mm.group(1))
            title = mm.group(2).strip()
            body = mm.group(3).strip()
            entries[n] = title + (". " + body if body else "")
    return [entries[k] for k in sorted(entries.keys())]


def _choice_hint_for(player_input: str, history: list) -> str:
    """Если ввод — номер 1..9, возвращает подсказку мастеру с текстом выбора."""
    s = str(player_input).strip()
    if s not in ("1", "2", "3", "4", "5", "6", "7", "8", "9"):
        return ""
    if not history:
        return ""
    n = int(s)
    last_master = ""
    for t in reversed(history):
        if isinstance(t, dict) and str(t.get("role")) == "master":
            last_master = str(t.get("text", ""))
            break
    if not last_master:
        return ""
    choices = _parse_master_choices(last_master)
    if not choices or n > len(choices):
        return ""
    return (
        "\n\n=== ВЫБОР ИГРОКА ===\n"
        "Игрок написал \"" + s + "\" — это означает, что он выбирает "
        "вариант " + str(n) + " из твоего последнего блока «Варианты действий»:\n"
        "«" + choices[n-1] + "»\n"
        "Опиши, что происходит, когда игрок делает этот выбор. "
        "НЕ повторяй вступление и НЕ задавай вопрос «что делаешь?» снова — "
        "сразу переходи к последствиям и новой сцене."
    )
# /PATCH_68



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
        print("[analyst] action=" + command.action
              + " skill=" + str(command.skill)
              + " roll_needed=" + str(command.roll_needed)
              + " diff=" + command.difficulty)

        roll = None
        if command.roll_needed:
            skill = command.skill
            if not skill:
                print("[orchestrator] roll_needed=True без skill -> fallback на Per")
                skill = "Per"
            base = self._lookup_skill(state, skill)
            print("[orchestrator] base(" + str(skill) + ")=" + str(base))
            roll = roll_check(base, difficulty=command.difficulty, reason=skill)
            try:
                d = roll.to_dict()
                verdict = "SUCCESS" if d.get("success") else "FAIL"
                print("[orchestrator] roll: d100=" + str(d.get("roll"))
                      + " vs " + str(d.get("target")) + " -> " + verdict
                      + " (deg " + str(d.get("degrees")) + ")")
            except Exception:
                print("[orchestrator] roll: " + repr(roll))

        rag_ctx = ""
        rag_sources: list = []
        rag_n = 0
        faction = None
        if isinstance(state, dict):
            faction = state.get("faction_id") or None
        if self.kb is not None:
            enriched = self._enrich_query(player_input, command, state=state)
            try:
                chunks = self.kb.search(enriched, top_k=4, faction=faction) or []
                rag_n = len(chunks)
                if chunks:
                    rag_ctx = self.kb.format_context(
                        enriched, top_k=4, faction=faction,
                    )
                    rag_sources = self._extract_sources(chunks)
                print("[orchestrator] RAG q=" + repr(enriched[:70])
                      + " -> " + str(rag_n) + " chunks")
            except Exception as e:
                print("[orchestrator] RAG ошибка: " + str(e))
                rag_ctx = ""

        # PATCH_68: подсказка мастеру, если игрок выбрал вариант цифрой
        _choice_hint = _choice_hint_for(player_input, history or [])
        if _choice_hint:
            print("[orchestrator] choice hint: " + player_input.strip())
        narrative = self.master.narrate(
            state, command, roll=roll, history=history or [],
            extra_context=(rag_ctx or "") + _choice_hint,
        )
        narrative = ensure_action_variants(narrative)

        return TurnResult(
            player_input=player_input, moderation=mod,
            command=command, roll=roll, narrative=narrative,
            rag_sources=rag_sources, rag_chunks=rag_n,
        )

    @staticmethod
    def _enrich_query(player_input: str, command: ParsedCommand,
                      state: Any = None) -> str:
        parts: list[str] = [player_input]
        if command.target:
            parts.append(str(command.target))
        if command.action and command.action != "other":
            parts.append(command.action.replace("_", " "))
        if command.skill:
            parts.append(command.skill)
        if isinstance(state, dict):
            for key in ("faction", "subfaction", "home_world_name",
                        "career_name", "home_world_id", "career_id"):
                v = state.get(key)
                if v:
                    parts.append(str(v))
            loc = state.get("location")
            if isinstance(loc, dict):
                p = loc.get("place") or loc.get("world")
                if p:
                    parts.append(str(p))
            elif loc:
                parts.append(str(loc))
        return " ".join(p for p in parts if p).strip()

    @staticmethod
    def _extract_sources(chunks: list) -> list:
        out: list = []
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
        if not skill:
            return DEFAULT_SKILL_VALUE

        paths = [
            "characteristics." + skill,
            "characteristics." + skill.upper(),
            "characteristics." + skill.capitalize(),
            "skills." + skill,
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
