# PATCH_24B
"""services/combat.py — пошаговый бой + травмы."""
from __future__ import annotations
import random
from typing import Optional

ZONES = ["far", "mid", "close", "melee"]
ZONE_RU = {"far": "Дальняя", "mid": "Средняя",
           "close": "Ближняя", "melee": "Вплотную"}
ZONE_ORDER = {"far": 0, "mid": 1, "close": 2, "melee": 3}


def roll_initiative(ag: int) -> int:
    return random.randint(1, 10) + (ag // 10)


def distance_mod(az: str, dz: str, is_ranged: bool) -> int:
    diff = abs(ZONE_ORDER.get(az, 1) - ZONE_ORDER.get(dz, 1))
    if is_ranged:
        return {0: 0, 1: -10, 2: -20}.get(diff, -30)
    return {0: 10, 1: -10}.get(diff, -40)


class CombatState:
    def __init__(self):
        self.round = 0
        self.active = False
        self.outcome: Optional[str] = None
        self.participants: dict = {}
        self.initiative: list = []
        self.turn_index = 0
        self.log: list = []
        self.crit_hits_taken = 0

    def add(self, name, hp_max, ag, side, is_player=False,
            zone="mid", weapon_dmg="1d10+3", weapon_pen=0, is_ranged=True):
        self.participants[name] = {
            "hp": int(hp_max), "hp_max": int(hp_max),
            "ag": int(ag), "side": side, "is_player": bool(is_player),
            "zone": zone, "weapon_dmg": weapon_dmg, "weapon_pen": weapon_pen,
            "is_ranged": is_ranged, "defended": False, "moved": False,
            "max_hit_taken": 0,
        }

    def roll_all(self):
        self.initiative = sorted(
            [(roll_initiative(p["ag"]), n) for n, p in self.participants.items()],
            key=lambda x: -x[0])
        self.turn_index = 0
        self.active = True
        self.round = 1
        self.log.append("─── Раунд 1 ───")

    def current(self):
        if not self.initiative:
            return None
        _, name = self.initiative[self.turn_index % len(self.initiative)]
        return name

    def next_turn(self):
        self.turn_index += 1
        if self.turn_index >= len(self.initiative):
            self.turn_index = 0
            self.round += 1
            self.log.append("─── Раунд " + str(self.round) + " ───")
        name = self.current()
        if name and name in self.participants:
            self.participants[name]["defended"] = False
            self.participants[name]["moved"] = False

    def alive_enemies(self, side):
        return [n for n, p in self.participants.items()
                if p["side"] != side and p["hp"] > 0]

    def alive_side(self, side):
        return [n for n, p in self.participants.items()
                if p["side"] == side and p["hp"] > 0]

    def is_over(self):
        if not self.active:
            return True
        if not self.alive_side("player"):
            self.active = False
            self.outcome = "loss"
            return True
        if not self.alive_side("enemy"):
            self.active = False
            self.outcome = "win"
            return True
        return False

    def attack(self, attacker: str, target: str, base_skill: int) -> dict:
        if attacker not in self.participants or target not in self.participants:
            return {"error": "участник не найден"}
        a = self.participants[attacker]
        d = self.participants[target]
        if a["hp"] <= 0 or d["hp"] <= 0:
            return {"error": "мёртвый не атакует"}
        mod = distance_mod(a["zone"], d["zone"], a["is_ranged"])
        tv = base_skill + mod
        roll = random.randint(1, 100)
        hit = roll <= tv
        res = {"attacker": attacker, "target": target, "roll": roll,
               "target_val": tv, "mod": mod, "hit": hit, "damage": 0,
               "target_hp_left": d["hp"]}
        if not hit:
            self.log.append(attacker + " промах по " + target
                            + " (d100=" + str(roll) + " vs " + str(tv) + ")")
            return res
        import re as _re
        m = _re.match(r"(\d+)d(\d+)([+\-]\d+)?", a["weapon_dmg"])
        dmg = 0
        if m:
            n, f = int(m.group(1)), int(m.group(2))
            dmg = sum(random.randint(1, f) for _ in range(n))
            if m.group(3):
                dmg += int(m.group(3))
        d["hp"] = max(0, d["hp"] - dmg)
        if dmg > d.get("max_hit_taken", 0):
            d["max_hit_taken"] = dmg
        res["damage"] = dmg
        res["target_hp_left"] = d["hp"]
        self.log.append(attacker + " попал по " + target
                        + " (d100=" + str(roll) + " vs " + str(tv)
                        + "), урон " + str(dmg)
                        + ", HP " + str(d["hp"]) + "/" + str(d["hp_max"]))
        return res

    def move(self, name: str, direction: str) -> dict:
        if name not in self.participants:
            return {"error": "нет участника"}
        p = self.participants[name]
        if p["moved"]:
            return {"error": "уже двигался"}
        cur = ZONE_ORDER.get(p["zone"], 1)
        new = (min(len(ZONES) - 1, cur + 1) if direction == "closer"
               else max(0, cur - 1))
        p["zone"] = ZONES[new]
        p["moved"] = True
        self.log.append(name + " → " + ZONE_RU[p["zone"]])
        return {"zone": p["zone"]}

    def defend(self, name: str) -> dict:
        if name in self.participants:
            self.participants[name]["defended"] = True
            self.log.append(name + " в защите (+20)")
            return {"ok": True}
        return {"error": "нет участника"}

    def player_result(self) -> dict:
        """Итоги боя для игрока: макс. полученный урон, доля HP."""
        players = [p for p in self.participants.values() if p["is_player"]]
        if not players:
            return {}
        p = players[0]
        return {
            "hp": p["hp"], "hp_max": p["hp_max"],
            "hp_pct": (p["hp"] * 100 // max(1, p["hp_max"])),
            "max_hit_taken": p.get("max_hit_taken", 0),
        }


def state_to_master_text(cs: CombatState) -> str:
    if not cs or not cs.active:
        return ""
    lines = ["=== БОЕВОЕ СОСТОЯНИЕ ===", "Раунд " + str(cs.round) + "."]
    cur = cs.current()
    if cur:
        lines.append("Ход: " + cur)
    for n, p in cs.participants.items():
        if p["hp"] <= 0:
            lines.append("  " + n + " — ПОВЕРЖЕН")
        else:
            lines.append("  " + n + " [" + p["side"] + "] HP "
                         + str(p["hp"]) + "/" + str(p["hp_max"])
                         + ", " + ZONE_RU.get(p["zone"], p["zone"]))
    return "\n".join(lines)
