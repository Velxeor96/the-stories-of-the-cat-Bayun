# PATCH_TUT_V2A
# services/tutorial.py - движок туториала с боем.
from __future__ import annotations

import random
import re
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

    def to_dict(self):
        return {
            "roll": self.roll, "target": self.target,
            "success": self.success, "degrees": self.degrees,
            "crit_success": self.crit_success, "crit_fail": self.crit_fail,
            "reason": self.reason, **self.extra,
        }


def roll_d100():
    return random.randint(1, 100)


def is_doubles(n):
    return 11 <= n <= 99 and n % 11 == 0


def _check(threshold, reason=""):
    r = roll_d100()
    success = r <= threshold
    degrees = abs(threshold - r) // 10
    crit_s = success and is_doubles(r)
    crit_f = (not success) and (r == 100 or is_doubles(r))
    return RollResult(roll=r, target=threshold, success=success,
                      degrees=degrees, crit_success=crit_s, crit_fail=crit_f,
                      reason=reason)


_DICE_RE = re.compile(r"^(\d+)d(\d+)([+-]\d+)?$")


def roll_dice(expr):
    m = _DICE_RE.match(expr.strip())
    if not m:
        return 0
    n, d, mod = int(m.group(1)), int(m.group(2)), m.group(3)
    total = sum(random.randint(1, d) for _ in range(n))
    if mod:
        total += int(mod)
    return total


def _tb(chars):
    return chars.get("T", 30) // 10


def _sb(chars):
    return chars.get("S", 30) // 10


def _canon(name):
    if not name:
        return None
    if name in td.CHARACTERISTIC_ALIASES:
        return td.CHARACTERISTIC_ALIASES[name]
    low = name.strip().lower()
    for k, v in td.CHARACTERISTIC_ALIASES.items():
        if k.lower() == low:
            return v
    return None


def skill_base(character, skill_name):
    skills = character.get("skills", {})
    chars = character.get("characteristics", {})
    if skill_name in skills:
        sk = skills[skill_name]
        linked = sk.get("linked")
        lv = chars.get(linked, 0)
        bonus = sk.get("talent_bonus", 0)
        if sk.get("trained"):
            return lv + bonus, skill_name + " (прод., " + str(linked) + "=" + str(lv) + ")"
        return lv // 2 + bonus, skill_name + " (база)"
    canon = _canon(skill_name)
    if canon and canon in chars:
        return chars[canon], canon + "=" + str(chars[canon])
    aliases = {
        "Awareness": "Per", "Perception": "Per",
        "Charm": "Fel", "Command": "Fel",
        "Intimidate": "S", "Melee": "WS",
        "Dodge": "Ag", "Pilot": "Ag", "Agility": "Ag",
    }
    if skill_name in aliases:
        c = aliases[skill_name]
        return chars.get(c, 0), skill_name + "->" + c
    return 45, skill_name + " (default 45)"


class TutorialEngine:
    def __init__(self, config=None):
        self.scenes = td.SCENES

    def initial_state(self, character_id):
        if character_id not in td.CHARACTERS:
            raise TutorialError("Персонаж не найден: " + str(character_id))
        char = td.CHARACTERS[character_id]
        first = self.scenes[0]["steps"][self.scenes[0]["start"]]
        return {
            "character_id": character_id,
            "scene_idx": 0,
            "step_id": self.scenes[0]["start"],
            "wounds": char["wounds"],
            "wounds_max": char["wounds_max"],
            "fate_points": char["fate_points"],
            "fate_max": char["fate_max"],
            "profit_factor": 35,
            "history": [{"role": "g91", "text": first["narration"]}],
            "pending_roll": None,
            "pending_post": None,
            "combat": None,
            "module_complete": False,
            "finish_action": None,
        }

    def get_current_step(self, state):
        scene = self.scenes[state["scene_idx"]]
        sid = state["step_id"]
        if sid not in scene["steps"]:
            raise TutorialError("Шаг не найден: " + str(sid))
        return scene["steps"][sid]

    def choose_option(self, state, option_idx):
        step = self.get_current_step(state)
        options = step.get("options", [])
        if option_idx < 0 or option_idx >= len(options):
            raise TutorialError("Опция вне диапазона")
        opt = options[option_idx]
        cost = opt.get("cost")
        if cost and "fate" in cost and state["fate_points"] >= cost["fate"]:
            state["fate_points"] -= cost["fate"]
        roll_dict = None
        post_text = None
        roll_spec = opt.get("roll")
        if roll_spec:
            char = td.CHARACTERS[state["character_id"]]
            roll_dict = self._resolve_roll(roll_spec, char, state)
            if roll_dict.get("success"):
                post_text = roll_spec.get("success_text")
                if roll_dict.get("crit_success"):
                    post_text = "**// КРИТИЧЕСКИЙ УСПЕХ //** " + (post_text or "")
                if roll_spec.get("type") == "fear":
                    state["fate_points"] = min(
                        state["fate_points"] + 1, state["fate_max"])
            else:
                post_text = roll_spec.get("fail_text")
                if roll_dict.get("crit_fail"):
                    post_text = "**// КРИТИЧЕСКИЙ ПРОВАЛ //** " + (post_text or "")
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
        if roll_dict is None and not post_text:
            self.advance(state)
        return state

    # PATCH_TUT_V2D
    def advance(self, state):
        post = state.get("pending_post")
        if post:
            state["history"].append({"role": "g91", "text": post})
        goto = state.pop("_pending_goto", None)
        state["pending_roll"] = None
        state["pending_post"] = None
        if goto == "__finish_with__":
            state["finish_action"] = "continue"
            state["module_complete"] = True
            return state
        if goto == "__finish_create__":
            state["finish_action"] = "create"
            state["module_complete"] = True
            return state
        if goto is None:
            state["scene_idx"] += 1
            if state["scene_idx"] >= len(self.scenes):
                state["module_complete"] = True
                return state
            state["wounds"] = state["wounds_max"]
            state["history"].append({
                "role": "g91",
                "text": ("**// СИСТЕМА: ЦЕЛОСТНОСТЬ ВОССТАНОВЛЕНА. "
                         "РАНЫ: " + str(state["wounds"]) + "/" +
                         str(state["wounds_max"]) + ". //**"),
            })
            ns = self.scenes[state["scene_idx"]]
            state["step_id"] = ns["start"]
            state["history"].append({
                "role": "g91",
                "text": ns["steps"][ns["start"]]["narration"],
            })
            if ns["steps"][ns["start"]].get("combat"):
                self._start_combat(state,
                                   ns["steps"][ns["start"]]["combat"])
            return state
        scene = self.scenes[state["scene_idx"]]
        if goto not in scene["steps"]:
            raise TutorialError("Шаг не найден: " + str(goto))
        state["step_id"] = goto
        new_step = scene["steps"][goto]
        state["history"].append({"role": "g91", "text": new_step["narration"]})
        if new_step.get("combat"):
            self._start_combat(state, new_step["combat"])
        return state


    def _resolve_roll(self, spec, char, state):
        rtype = spec.get("type", "skill")
        if rtype == "acquisition":
            pf = state.get("profit_factor", 35)
            av = td.AVAILABILITY_MODIFIERS.get(
                spec.get("availability", "Common"), 0)
            qv = td.QUANTITY_MODIFIERS.get(
                spec.get("quantity", "single"), 0)
            cv = td.CRAFTSMANSHIP_MODIFIERS.get(
                spec.get("craftsmanship", "Common"), 0)
            return _check(pf + av + qv + cv,
                          spec.get("reason", "Acquisition")).to_dict()
        if rtype == "fear":
            rating = spec.get("fear_rating", 3)
            mod = td.FEAR_MODIFIERS.get(rating, -20)
            wp = char["characteristics"].get("WP", 30)
            return _check(wp + mod, spec.get("reason", "Fear")).to_dict()
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
            return _check(threshold, spec.get("reason", "Космос")).to_dict()
        skill_name = spec.get("skill") or spec.get("characteristic") or "Per"
        mod = int(spec.get("mod", 0))
        base, src = skill_base(char, skill_name)
        r = _check(base + mod, spec.get("reason") or src)
        r.extra["base"] = base
        r.extra["modifier"] = mod
        return r.to_dict()

    def _start_combat(self, state, cfg):
        eid = cfg["enemy"]
        if eid not in td.ENEMIES:
            raise TutorialError("Враг не найден: " + str(eid))
        base = td.ENEMIES[eid]
        enemy = {
            "id": base["id"], "name": base["name"],
            "characteristics": dict(base["characteristics"]),
            "wounds": base["wounds"], "wounds_max": base["wounds_max"],
            "armour": dict(base.get("armour", {})),
            "weapons": list(base.get("weapons", [])),
            "tactics": base.get("tactics", "melee"),
            "abilities": list(base.get("tutorial_abilities", [])),
        }
        state["combat"] = {
            "enemy": enemy, "round": 0, "log": [],
            "cfg": cfg, "over": False, "outcome": None, "turn": "player",
        }

    def combat_player_action(self, state, action):
        c = state.get("combat")
        if not c or c["over"] or c["turn"] != "player":
            return state
        char = td.CHARACTERS[state["character_id"]]
        c["round"] += 1
        kind = action.get("kind")
        if kind == "attack_melee":
            wid = action.get("weapon")
            if not wid:
                for w in char["weapons"]:
                    if td.WEAPONS.get(w, {}).get("type") == "melee":
                        wid = w
                        break
            weapon = td.WEAPONS.get(wid or "unarmed", td.WEAPONS["unarmed"])
            self._pc_attack(state, char, weapon, melee=True)
        elif kind == "attack_ranged":
            wid = action.get("weapon")
            if not wid:
                for w in char["weapons"]:
                    if td.WEAPONS.get(w, {}).get("type") == "ranged":
                        wid = w
                        break
            weapon = td.WEAPONS.get(wid or "las_pistol",
                                    td.WEAPONS["las_pistol"])
            self._pc_attack(state, char, weapon, melee=False)
        elif kind == "psy_bolt":
            self._pc_psy_attack(state, char, td.WEAPONS["warp_bolt"])
        elif kind == "grenade":
            self._pc_grenade(state, char, td.WEAPONS["frag_grenade"])
        elif kind == "aim":
            c["log"].append({"t": "info",
                             "text": "Ты прицеливаешься. Следующая атака - "
                                     "+20 к порогу."})
            c["player_aim_bonus"] = 20
        else:
            c["log"].append({"t": "info", "text": "Неизвестное действие."})
        if c["enemy"]["wounds"] <= 0:
            c["over"] = True
            c["outcome"] = "win"
            c["log"].append({"t": "win",
                             "text": "**" + c["enemy"]["name"] +
                                     " падает. Бой окончен.**"})
            return state
        c["turn"] = "enemy"
        return state

    def combat_enemy_turn(self, state):
        c = state.get("combat")
        if not c or c["over"] or c["turn"] != "enemy":
            return state
        char = td.CHARACTERS[state["character_id"]]
        enemy = c["enemy"]
        tactics = enemy.get("tactics", "melee")
        wid = "unarmed"
        if tactics == "psyker" and "warp_bolt" in enemy.get("abilities", []):
            if c["round"] % 2 == 0:
                wid = "warp_bolt"
            elif enemy.get("weapons"):
                wid = enemy["weapons"][0]
        elif enemy.get("weapons"):
            wid = enemy["weapons"][0]
        weapon = td.WEAPONS.get(wid, td.WEAPONS["unarmed"])
        self._enemy_attack(state, char, enemy, weapon)
        if state["wounds"] <= 0:
            c["over"] = True
            c["outcome"] = "loss"
            c["log"].append({"t": "loss",
                             "text": "**Ты падаешь. Сознание уходит.**"})
            return state
        c["turn"] = "player"
        return state

    def combat_resolve(self, state):
        c = state.get("combat")
        if not c:
            return state
        cfg = c.get("cfg", {})
        if c["round"] >= cfg.get("max_rounds", 6) and not c["over"]:
            c["over"] = True
            c["outcome"] = "timeout"
        outcome = c.get("outcome") or "timeout"
        target = cfg.get("on_win")
        if outcome == "loss":
            target = cfg.get("on_loss", cfg.get("on_win"))
        elif outcome == "timeout":
            target = cfg.get("on_timeout", cfg.get("on_win"))
        state["combat"] = None
        if target:
            scene = self.scenes[state["scene_idx"]]
            if target in scene["steps"]:
                state["step_id"] = target
                step = scene["steps"][target]
                state["history"].append({"role": "g91",
                                         "text": step["narration"]})
                if step.get("combat"):
                    self._start_combat(state, step["combat"])
        return state

    def _pc_attack(self, state, char, weapon, melee):
        c = state["combat"]
        enemy = c["enemy"]
        chars = char["characteristics"]
        if weapon["type"] == "melee":
            base = chars.get("WS", 30)
            src = "WS=" + str(base)
        else:
            base = chars.get("BS", 30)
            src = "BS=" + str(base)
        aim = c.pop("player_aim_bonus", 0)
        threshold = base + aim
        r = _check(threshold,
                   "Атака " + weapon["name"] + " (" + src + ")")
        c["log"].append({"t": "roll", "roll": r.to_dict()})
        if not r.success:
            c["log"].append({"t": "info",
                             "text": "Промах по " + enemy["name"] + "."})
            return
        loc_roll = roll_d100()
        loc = td.roll_location(loc_roll)
        loc_ru = td.location_ru(loc)
        c["log"].append({
            "t": "info",
            "text": ("Попадание. Локация: d100=" + str(loc_roll) +
                     " -> **" + loc_ru + "**. Степеней успеха: " +
                     str(r.degrees) + "."),
        })
        dmg = roll_dice(weapon["dmg"])
        if weapon["type"] == "melee":
            dmg += _sb(chars)
        pen = weapon.get("pen", 0)
        armour = enemy["armour"].get(loc, 0)
        eff = max(0, armour - pen)
        tb = _tb(enemy["characteristics"])
        taken = max(0, dmg - tb - eff)
        enemy["wounds"] = max(0, enemy["wounds"] - taken)
        c["log"].append({
            "t": "damage",
            "text": ("Урон: " + weapon["dmg"] + " = " + str(dmg) +
                     ". TB " + str(tb) + ", броня " + str(eff) +
                     ". Итого **" + str(taken) + "** ран. У врага " +
                     str(enemy["wounds"]) + "/" + str(enemy["wounds_max"]) + "."),
        })

    def _pc_psy_attack(self, state, char, weapon):
        c = state["combat"]
        enemy = c["enemy"]
        wp = char["characteristics"].get("WP", 30)
        r = _check(wp, "Психосила " + weapon["name"] + " (WP=" + str(wp) + ")")
        c["log"].append({"t": "roll", "roll": r.to_dict()})
        if not r.success:
            c["log"].append({"t": "info",
                             "text": "Варп отказывает. Сила рассеивается."})
            return
        loc_roll = roll_d100()
        loc = td.roll_location(loc_roll)
        loc_ru = td.location_ru(loc)
        c["log"].append({"t": "info",
                         "text": "Психосила бьёт. Локация: **" + loc_ru + "**."})
        dmg = roll_dice(weapon["dmg"])
        pen = weapon.get("pen", 0)
        armour = enemy["armour"].get(loc, 0)
        eff = max(0, armour - pen)
        tb = _tb(enemy["characteristics"])
        taken = max(0, dmg - tb - eff)
        enemy["wounds"] = max(0, enemy["wounds"] - taken)
        c["log"].append({
            "t": "damage",
            "text": ("Урон психосилы: " + weapon["dmg"] + " = " +
                     str(dmg) + ". TB " + str(tb) + ", броня " + str(eff) +
                     ". Итого **" + str(taken) + "** ран."),
        })

    def _pc_grenade(self, state, char, weapon):
        c = state["combat"]
        enemy = c["enemy"]
        bs = char["characteristics"].get("BS", 30)
        r = _check(bs - 10, "Граната (BS-10)")
        c["log"].append({"t": "roll", "roll": r.to_dict()})
        if not r.success:
            c["log"].append({"t": "info",
                             "text": "Граната уходит в сторону."})
            return
        dmg = roll_dice(weapon["dmg"])
        tb = _tb(enemy["characteristics"])
        taken = max(0, dmg - tb)
        enemy["wounds"] = max(0, enemy["wounds"] - taken)
        c["log"].append({
            "t": "damage",
            "text": ("Взрыв. Урон " + weapon["dmg"] + " = " + str(dmg) +
                     ". TB " + str(tb) + ". Итого **" + str(taken) + "** ран."),
        })

    def _enemy_attack(self, state, char, enemy, weapon):
        c = state["combat"]
        chars = enemy["characteristics"]
        if weapon["type"] == "melee":
            base = chars.get("WS", 30)
            label = "WS"
        elif weapon["type"] == "psy":
            base = chars.get("WP", 30)
            label = "WP"
        else:
            base = chars.get("BS", 30)
            label = "BS"
        r = _check(base,
                   "Враг: " + weapon["name"] + " (" + label + "=" + str(base) + ")")
        c["log"].append({"t": "roll", "roll": r.to_dict()})
        if not r.success:
            c["log"].append({"t": "info",
                             "text": enemy["name"] + " промахивается."})
            return
        loc_roll = roll_d100()
        loc = td.roll_location(loc_roll)
        loc_ru = td.location_ru(loc)
        c["log"].append({
            "t": "info",
            "text": enemy["name"] + " попадает тебе в **" + loc_ru + "**.",
        })
        dmg = roll_dice(weapon["dmg"])
        if weapon["type"] == "melee":
            dmg += _sb(chars)
        pen = weapon.get("pen", 0)
        pc = td.CHARACTERS[state["character_id"]]
        armour = pc.get("armour", {}).get(loc, 0)
        eff = max(0, armour - pen)
        tb = _tb(pc["characteristics"])
        taken = max(0, dmg - tb - eff)
        state["wounds"] = max(0, state["wounds"] - taken)
        c["log"].append({
            "t": "damage",
            "text": ("Урон врага: " + weapon["dmg"] + " = " + str(dmg) +
                     ". Твой TB " + str(tb) + ", броня " + str(eff) +
                     ". Итого **" + str(taken) + "** ран. У тебя " +
                     str(state["wounds"]) + "/" + str(state["wounds_max"]) + "."),
        })
