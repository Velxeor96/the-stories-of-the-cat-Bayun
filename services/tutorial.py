# PATCH_10_STYLE_V1
"""services/tutorial.py — движок туториала. Без LLM."""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Optional

from services import tutorial_data as td


class TutorialError(Exception):
    pass


@dataclass
class RollResult:
    roll: int
    target: int
    success: bool
    degrees: int
    crit_success: bool = False
    crit_fail: bool = False
    reason: str = ""
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "roll": self.roll, "target": self.target,
            "success": self.success, "degrees": self.degrees,
            "crit_success": self.crit_success, "crit_fail": self.crit_fail,
            "reason": self.reason, **self.extra,
        }


def roll_d100() -> int:
    return random.randint(1, 100)


def is_doubles(n: int) -> bool:
    return 11 <= n <= 99 and n % 11 == 0


def _check(threshold: int, reason: str = "") -> RollResult:
    r = roll_d100()
    success = r <= threshold
    degrees = abs(threshold - r) // 10
    crit_s = success and is_doubles(r)
    crit_f = (not success) and (r == 100 or is_doubles(r))
    return RollResult(roll=r, target=threshold, success=success,
                      degrees=degrees, crit_success=crit_s, crit_fail=crit_f,
                      reason=reason)


def _canon(name: str) -> Optional[str]:
    if not name:
        return None
    if name in td.CHARACTERISTIC_ALIASES:
        return td.CHARACTERISTIC_ALIASES[name]
    low = name.strip().lower()
    for k, v in td.CHARACTERISTIC_ALIASES.items():
        if k.lower() == low:
            return v
    return None


def skill_base(character: dict, skill_name: str) -> tuple[int, str]:
    skills = character.get("skills", {})
    chars = character.get("characteristics", {})
    if skill_name in skills:
        sk = skills[skill_name]
        linked = sk.get("linked")
        lv = chars.get(linked, 0)
        if sk.get("type") == "advanced" and sk.get("trained"):
            return lv + sk.get("talent_bonus", 0), f"{skill_name} (продв., {linked}={lv})"
        base = lv // 2 + sk.get("talent_bonus", 0)
        return base, f"{skill_name} (базовый, {linked}//2={lv // 2})"
    canon = _canon(skill_name)
    if canon and canon in chars:
        return chars[canon], f"{canon}={chars[canon]}"
    skill_aliases = {
        "Awareness": "Per", "Perception": "Per",
        "Charm": "Fel", "Command": "Fel",
        "Intimidate": "S", "Melee": "S",
        "Dodge": "Ag", "Pilot": "Ag", "Agility": "Ag",
    }
    if skill_name in skill_aliases:
        c = skill_aliases[skill_name]
        return chars.get(c, 0), f"{skill_name}→{c}={chars.get(c, 0)}"
    return 45, f"{skill_name} (default 45)"


class TutorialEngine:
    def __init__(self, config=None):
        self.scenes = td.SCENES

    def initial_state(self, character_id: str) -> dict:
        if character_id not in td.CHARACTERS:
            raise TutorialError(f"Персонаж {character_id!r} не найден")
        char = td.CHARACTERS[character_id]
        first = self.scenes[0]["steps"][self.scenes[0]["start"]]
        return {
            "character_id": character_id,
            "scene_idx": 0,
            "step_id": self.scenes[0]["start"],
            "wounds": char["wounds"],
            "fate_points": char["fate_points"],
            "profit_factor": 35,
            "history": [{"role": "master", "text": first["narration"]}],
            "pending_roll": None,
            "pending_post": None,
            "module_complete": False,
        }

    def get_current_step(self, state: dict) -> dict:
        scene = self.scenes[state["scene_idx"]]
        sid = state["step_id"]
        if sid not in scene["steps"]:
            raise TutorialError(f"Шаг {sid!r} не найден в {scene['id']!r}")
        return scene["steps"][sid]

    def choose_option(self, state: dict, option_idx: int) -> dict:
        step = self.get_current_step(state)
        options = step.get("options", [])
        if option_idx < 0 or option_idx >= len(options):
            raise TutorialError(f"Опция {option_idx} вне диапазона")
        opt = options[option_idx]

        # плата
        cost = opt.get("cost")
        if cost:
            if "fate" in cost and state["fate_points"] >= cost["fate"]:
                state["fate_points"] -= cost["fate"]
            if "pf" in cost and state["profit_factor"] >= cost["pf"]:
                state["profit_factor"] -= cost["pf"]

        roll_dict = None
        post_text = None
        roll_spec = opt.get("roll")
        if roll_spec:
            char = td.CHARACTERS[state["character_id"]]
            roll_dict = self._resolve_roll(roll_spec, char, state)
            if roll_dict.get("success"):
                post_text = roll_spec.get("success_text")
                if roll_dict.get("crit_success"):
                    post_text = "**КРИТИЧЕСКИЙ УСПЕХ!** " + (post_text or "")
            else:
                post_text = roll_spec.get("fail_text")
                if roll_dict.get("crit_fail"):
                    post_text = "**КРИТИЧЕСКИЙ ПРОВАЛ.** " + (post_text or "")
        else:
            post = opt.get("post")
            if isinstance(post, dict):
                post_text = post.get("success") or post.get("fail")
            elif isinstance(post, str):
                post_text = post

        state["history"].append({"role": "player", "text": opt["label"]})
        state["pending_roll"] = roll_dict
        state["pending_post"] = post_text
        state["_pending_goto"] = opt.get("goto")

        # ФИКС: если ни броска, ни пост-текста — переходим сразу
        if roll_dict is None and not post_text:
            self.advance(state)
        return state

    def advance(self, state: dict) -> dict:
        post = state.get("pending_post")
        if post:
            state["history"].append({"role": "master", "text": post})

        goto = state.pop("_pending_goto", None)
        state["pending_roll"] = None
        state["pending_post"] = None

        if goto == "__finish__":
            state["module_complete"] = True
            return state

        if goto is None:
            state["scene_idx"] += 1
            if state["scene_idx"] >= len(self.scenes):
                state["module_complete"] = True
                return state
            ns = self.scenes[state["scene_idx"]]
            state["step_id"] = ns["start"]
            state["history"].append({
                "role": "master",
                "text": ns["steps"][ns["start"]]["narration"],
            })
            return state

        scene = self.scenes[state["scene_idx"]]
        if goto not in scene["steps"]:
            raise TutorialError(f"Шаг {goto!r} не найден")
        state["step_id"] = goto
        state["history"].append({
            "role": "master",
            "text": scene["steps"][goto]["narration"],
        })
        return state

    def _resolve_roll(self, spec: dict, char: dict, state: dict) -> dict:
        rtype = spec.get("type", "skill")
        if rtype == "acquisition":
            pf = state.get("profit_factor", 35)
            av = td.AVAILABILITY_MODIFIERS.get(spec.get("availability", "Common"), 0)
            qv = td.QUANTITY_MODIFIERS.get(spec.get("quantity", "single"), 0)
            cv = td.CRAFTSMANSHIP_MODIFIERS.get(spec.get("craftsmanship", "Common"), 0)
            r = _check(pf + av + qv + cv, reason=spec.get("reason", "Acquisition"))
            return r.to_dict()
        if rtype == "fear":
            rating = spec.get("fear_rating", 3)
            mod = td.FEAR_MODIFIERS.get(rating, -20)
            wp = char["characteristics"].get("WP", 30)
            r = _check(wp + mod, reason=spec.get("reason", f"Fear {rating}"))
            return r.to_dict()
        if rtype == "space_combat":
            subtype = spec.get("subtype", "shooting")
            mod = int(spec.get("mod", 0))
            if subtype == "manoeuvre":
                base, _ = skill_base(char, "Pilot")
                threshold = base + 15 + mod
            elif subtype == "extended":
                base, _ = skill_base(char, spec.get("skill", "Command"))
                threshold = base + mod
            else:
                threshold = char["characteristics"].get("BS", 30) + mod
            r = _check(threshold, reason=spec.get("reason", f"Космос [{subtype}]"))
            return r.to_dict()
        skill_name = spec.get("skill") or spec.get("characteristic") or "Per"
        mod = int(spec.get("mod", 0))
        base, src = skill_base(char, skill_name)
        r = _check(base + mod, reason=spec.get("reason") or f"{src} ({mod:+d})")
        r.extra["base"] = base
        r.extra["modifier"] = mod
        return r.to_dict()
