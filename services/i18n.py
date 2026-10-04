"""services/i18n.py — переводчик навыков и талантов."""
from __future__ import annotations
import json
from pathlib import Path

_TABLE = None

def _load() -> dict:
    global _TABLE
    if _TABLE is None:
        p = Path(__file__).resolve().parent.parent / "data" / "_i18n.json"
        try:
            _TABLE = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            _TABLE = {}
    return _TABLE

def translate(text: str) -> str:
    if not text:
        return text
    return _load().get(str(text), str(text))

def translate_skills(skills) -> list:
    out = []
    for s in skills or []:
        if isinstance(s, dict):
            d = dict(s)
            d["name"] = translate(d.get("name", ""))
            out.append(d)
        else:
            out.append(translate(str(s)))
    return out

def translate_talents(talents) -> list:
    out = []
    for t in talents or []:
        if isinstance(t, dict):
            d = dict(t)
            d["name"] = translate(d.get("name", ""))
            out.append(d)
        else:
            out.append(translate(str(t)))
    return out
