# PATCH_31
# services/data_loader.py — данные фракций со строгим whitelist.
from __future__ import annotations
import json
import re
import sys
import time
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
INDEX_FILE = DATA_DIR / "_index.json"

KNOWN_HOME_WORLDS = {
    "imperium": ["Мир-Улей", "Мир-Кузница", "Дикий мир", "Мир Смерти",
                 "Феодальный мир", "Схола Прогениум", "Рождённый в пустоте",
                 "Благородное происхождение"],
    "chaos": ["Око Ужаса", "Варп-шторм", "Мир-Демон", "Проклятый мир",
              "Планета-карантин", "Кровавый мир", "Забытый мир"],
    "eldar": ["Алайток", "Биэль-Тан", "Иянден", "Саим-Ханн",
              "Ультвэ", "Альтансар", "Луганат", "Кейлор"],
    "drukhari": ["Комморраг", "Владение Архонта", "Арена", "Тёмный город"],
    "orks": ["Гоффы", "Змеиные Клыки", "Злые Солнца", "Багровые Клыки",
             "Кровавые Топоры", "Черепа", "Дэт Скаллз"],
    "tau": ["Каста Огня", "Каста Земли", "Каста Воды", "Каста Воздуха",
            "Септ Тау", "Империя Тау"],
    "necrons": ["Мир-Гробница", "Корона Династии", "Спящий Мир",
                "Династия", "Мир-Хранилище"],
    "tyranids": ["Флот-улей Бегемот", "Флот-улей Кракен",
                 "Флот-улей Левиафан", "Флот-улей Йормунгандр"],
    "genestealers": ["Заражённый улей", "Мир-Культ", "Корабль-храм",
                     "Скрытый мир"],
}

KNOWN_CAREERS = {
    "imperium": ["Вольный Торговец", "Арх-Милитант", "Эксплоратор",
                 "Астропат", "Навигатор", "Сенешаль", "Владыка Пустоты",
                 "Миссионер"],
    "chaos": ["Космодесантник Хаоса", "Тёмный Механикум", "Культист",
              "Чемпион Хаоса", "Колдун Хаоса", "Одержимый"],
    "eldar": ["Путь Воина", "Путь Провидца", "Путь Костопевца",
              "Путь Корсара", "Путь Сновидений", "Путь Целителя",
              "Путь Морехода", "Путь Учёного", "Путь Служения",
              "Путь Командования"],
    "drukhari": ["Кабалит", "Ведьма Арены", "Гемункул", "Суккуб"],
    "orks": ["Фрибутер", "Мекбой", "Пейнбой", "Ноб", "Босс"],
    "tau": ["Воин Огня", "Воин Воды", "Воин Земли", "Воин Воздуха",
            "Эфирн", "Крут"],
    "necrons": ["Лорд", "Владыка", "Криптек", "Дестроер", "Фаэрон"],
    "tyranids": ["Воин Улья", "Генокрад", "Карнифекс", "Ликтор",
                 "Тиран Улья"],
    "genestealers": ["Магус", "Патриарх", "Гибрид", "Неофит"],
}

CATEGORY_FILES = {
    "eldar": {
        "home_worlds": [("eldar/craftworlds.txt", "dash_named_english")],
        "careers":     [("eldar/paths.txt", "h3_numbered")],
        "equipment":   [("eldar/equipment.txt", "h4_plain")],
    },
    "imperium": {
        "home_worlds": [("imperium/lore.txt", "h3_numbered")],
        "careers":     [("general/10_careers.txt", "h3_numbered")],
        "equipment":   [("imperium/equipment.txt", "h4_plain")],
    },
    "chaos": {
        "home_worlds": [("chaos/01_lore.txt", "h3_numbered")],
        "careers":     [("chaos/03_chaos_legions.txt", "h3_numbered")],
        "equipment":   [("chaos/07_equipment.txt", "h4_plain")],
    },
    "orks": {
        "home_worlds": [("orks/clans.txt", "h3_numbered")],
        "careers":     [],
        "equipment":   [("orks/equipment.txt", "h4_plain")],
    },
    "tau": {
        "home_worlds": [("tau/castes.txt", "h3_numbered")],
        "careers":     [("tau/castes.txt", "h3_numbered")],
        "equipment":   [("tau/equipment.txt", "h4_plain")],
    },
    "necrons": {
        "home_worlds": [("necrons/dynasties.txt", "h3_numbered")],
        "careers":     [("necrons/dynasties.txt", "h3_numbered")],
        "equipment":   [("necrons/equipment.txt", "h4_plain")],
    },
    "tyranids": {
        "home_worlds": [("tyranids/hive_fleets.txt", "h3_numbered")],
        "careers":     [],
        "equipment":   [("tyranids/equipment.txt", "h4_plain")],
    },
    "drukhari": {
        "home_worlds": [("eldar/drukhari.txt", "h3_numbered")],
        "careers":     [("eldar/drukhari.txt", "h3_numbered")],
        "equipment":   [("eldar/equipment.txt", "h4_plain")],
    },
    "genestealers": {"home_worlds": [], "careers": [], "equipment": []},
}

MODES_ORDER = [
    "dash_named_english", "h4_plain", "h3_numbered", "h3_plain",
    "h2_numbered", "h2_plain", "h1_plain", "dash_plain",
]

_MODE_RE = {
    "h1_plain":           re.compile(r"^#\s+(.+?)\s*$"),
    "h2_plain":           re.compile(r"^##\s+(.+?)\s*$"),
    "h2_numbered":        re.compile(r"^##\s+\d+\.\s+(.+?)\s*$"),
    "h3_numbered":        re.compile(r"^###\s+\d+\.\s+(.+?)\s*$"),
    "h3_plain":           re.compile(r"^###\s+(.+?)\s*$"),
    "h4_plain":           re.compile(r"^####\s+(.+?)\s*$"),
    "dash_named_english": re.compile(r"^---\s+(.+?)\s+\(.+?\)\s+---\s*$"),
    "dash_plain":         re.compile(r"^---\s+(.+?)\s+---\s*$"),
}

WORD_FIXES = [
    ("костопевецецецецец", "костопевец"),
    ("костопевецецецецеца", "костопевца"),
    ("костопевецецецецецца", "костопевца"),
    ("костопевецецецецеццы", "костопевцы"),
    ("костопевецецецецеццем", "костопевцем"),
]


def _slug(name):
    s = name.strip().lower()
    s = re.sub(r"[^\w\s-]", "", s, flags=re.UNICODE)
    s = re.sub(r"\s+", "_", s)
    return s[:60] or "item"


def _norm(s):
    s = s.strip().lower()
    s = re.sub(r"[^\w\s]", " ", s, flags=re.UNICODE)
    s = re.sub(r"\s+", " ", s)
    return s


def _clean(name):
    s = name.strip()
    s = re.sub(r"^\d+[\.\)]\s*", "", s)
    s = re.sub(r"^[IVXLC]+[\.\)]\s*", "", s, flags=re.IGNORECASE)
    s = re.sub(r"\s*\([^)]*\)\s*$", "", s)
    s = re.sub(r"\s+", " ", s)
    s = s.strip(" —-.").strip()
    low = s.lower()
    for bad, good in WORD_FIXES:
        if bad in low:
            s = re.sub(bad, good, s, flags=re.IGNORECASE)
            low = s.lower()
    return s


def _apply_mode(text, mode, limit):
    rx = _MODE_RE.get(mode)
    if not rx:
        return []
    lines = text.split("\n")
    hits = []
    for i, ln in enumerate(lines):
        m = rx.match(ln.strip())
        if m:
            hits.append((i, m.group(1).strip()))
    if len(hits) < 2:
        return []
    out = []
    for j, (idx, title) in enumerate(hits[:limit]):
        end = hits[j + 1][0] if j + 1 < len(hits) else len(lines)
        body = "\n".join(lines[idx + 1:end]).strip()
        out.append({"title": title, "body": body})
    return out


def _parse_file(text, preferred, limit):
    modes = [preferred] + [m for m in MODES_ORDER if m != preferred]
    for mode in modes:
        items = _apply_mode(text, mode, limit)
        if items:
            for it in items:
                it["_mode"] = mode
            return items
    return []


def _parse_bonuses(body):
    bonuses = {}
    penalties = {}
    for m in re.finditer(r"([+\-])(\d+)\s+к\s+([А-Яа-яЁёA-Za-z ]+)", body):
        sign = m.group(1)
        num = int(m.group(2))
        name = m.group(3).strip().lower()
        for k, code in (("оружейное мастерство", "WS"),
                        ("баллистическое мастерство", "BS"),
                        ("сила", "S"), ("выносливость", "T"),
                        ("ловкость", "Ag"), ("интеллект", "Int"),
                        ("восприятие", "Per"), ("сила воли", "WP"),
                        ("обаяние", "Fel")):
            if k in name:
                if sign == "+":
                    bonuses[code] = bonuses.get(code, 0) + num
                else:
                    penalties[code] = penalties.get(code, 0) + num
                break
    return {"bonus": bonuses, "penalty": penalties}


def _read(rel_path):
    p = DATA_DIR / rel_path
    if not p.exists():
        return ""
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


def _load_category(faction_id, files, kind):
    whitelist = []
    if kind == "home_worlds":
        whitelist = KNOWN_HOME_WORLDS.get(faction_id, [])
    elif kind == "careers":
        whitelist = KNOWN_CAREERS.get(faction_id, [])
    limit = 60
    out = []
    seen = set()
    for rel_path, preferred_mode in files:
        text = _read(rel_path)
        if not text:
            continue
        items = _parse_file(text, preferred_mode, 200)
        for it in items:
            title = _clean(it["title"])
            key = _slug(title)
            if not key or key in seen:
                continue
            if kind in ("home_worlds", "careers") and whitelist:
                n_title = _norm(title)
                matched = False
                for w in whitelist:
                    if _norm(w) in n_title or n_title in _norm(w):
                        matched = True
                        break
                if not matched:
                    continue
            seen.add(key)
            entry = {
                "id": key, "name": title,
                "desc": it["body"][:400],
                "body": it["body"][:800],
                "source": rel_path,
                "mode": it.get("_mode", ""),
            }
            if kind in ("home_worlds", "careers"):
                b = _parse_bonuses(it["body"])
                entry["bonus"] = b["bonus"]
                entry["penalty"] = b["penalty"]
            out.append(entry)
            if len(out) >= limit:
                break
        if len(out) >= limit:
            break
    # PATCH_34: fallback — если парсер не нашёл ничего, но whitelist есть
    if not out and whitelist and kind in ("home_worlds", "careers"):
        for w in whitelist:
            key = _slug(w)
            if key in seen:
                continue
            seen.add(key)
            out.append({
                "id": key, "name": w,
                "desc": "Из справочника.",
                "body": "",
                "source": "_whitelist",
                "bonus": {}, "penalty": {},
            })
    return out


def _scan_all():
    out = {"_generated_at": time.time(), "_version": 5, "factions": {}}
    for fid, cats in CATEGORY_FILES.items():
        out["factions"][fid] = {
            "home_worlds": _load_category(fid, cats.get("home_worlds", []), "home_worlds"),
            "careers":     _load_category(fid, cats.get("careers", []), "careers"),
            "equipment":   _load_category(fid, cats.get("equipment", []), "equipment"),
        }
    return out


def _index_is_stale():
    if not INDEX_FILE.exists():
        return True
    try:
        idx = json.loads(INDEX_FILE.read_text(encoding="utf-8"))
        if idx.get("_version") != 5:
            return True
        gen = float(idx.get("_generated_at", 0))
    except Exception:
        return True
    for p in DATA_DIR.rglob("*.txt"):
        try:
            if p.stat().st_mtime > gen:
                return True
        except Exception:
            continue
    return False


_INDEX_CACHE = None


def build_index(force=False):
    global _INDEX_CACHE
    if not force and not _index_is_stale() and INDEX_FILE.exists():
        try:
            _INDEX_CACHE = json.loads(INDEX_FILE.read_text(encoding="utf-8"))
            return _INDEX_CACHE
        except Exception:
            pass
    idx = _scan_all()
    try:
        INDEX_FILE.write_text(
            json.dumps(idx, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        print("[data_loader] write fail: " + str(e))
    _INDEX_CACHE = idx
    return idx


def get_index():
    global _INDEX_CACHE
    if _INDEX_CACHE is None:
        build_index()
    return _INDEX_CACHE or {"factions": {}}


def _cat(faction_id, kind):
    return get_index().get("factions", {}).get(faction_id, {}).get(kind, [])


def list_home_world_ids(faction_id):
    return [it["id"] for it in _cat(faction_id, "home_worlds")]


def list_career_ids(faction_id):
    return [it["id"] for it in _cat(faction_id, "careers")]


def list_equipment_ids(faction_id):
    return [it["id"] for it in _cat(faction_id, "equipment")]


def _find(items, key):
    for it in items:
        if it["id"] == key:
            return it
    return None


def get_home_world(faction_id, key):
    f = _find(_cat(faction_id, "home_worlds"), key)
    if not f:
        return None
    return {"name": f["name"], "desc": f.get("desc", ""),
            "bonus": f.get("bonus", {}), "penalty": f.get("penalty", {}),
            "source": f.get("source", "")}


def get_career(faction_id, key):
    f = _find(_cat(faction_id, "careers"), key)
    if not f:
        return None
    return {"name": f["name"], "desc": f.get("desc", ""),
            "bonus": f.get("bonus", {}), "penalty": f.get("penalty", {}),
            "source": f.get("source", "")}


def get_equipment(faction_id, key):
    f = _find(_cat(faction_id, "equipment"), key)
    if not f:
        return None
    return {"name": f["name"], "body": f.get("body", ""),
            "source": f.get("source", "")}


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "build":
        idx = build_index(force=True)
        for fid, d in idx.get("factions", {}).items():
            print(fid + ": hw=" + str(len(d.get("home_worlds", [])))
                  + " careers=" + str(len(d.get("careers", [])))
                  + " equipment=" + str(len(d.get("equipment", []))))
            for it in d.get("home_worlds", [])[:8]:
                print("   hw: " + it["name"])
            for it in d.get("careers", [])[:8]:
                print("   cr: " + it["name"])
        print("Index -> " + str(INDEX_FILE))
