# scripts/patch.py — PATCH_101 + PATCH_102
# Anti-hallucination + Story Profiles (Rogue Trader: Imperium)
from __future__ import annotations
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
LOG = []

def write_file(rel_path: str, content: str) -> None:
    p = ROOT / rel_path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content.strip() + "\n", encoding="utf-8")
    LOG.append(f"[CREATE] {rel_path}")

def patch_file(rel_path: str, old: str, new: str) -> None:
    p = ROOT / rel_path
    if not p.exists():
        LOG.append(f"[ERROR] {rel_path} не найден")
        return
    text = p.read_text(encoding="utf-8")
    if old not in text:
        LOG.append(f"[WARN] {rel_path}: якорь не найден")
        return
    p.write_text(text.replace(old, new, 1), encoding="utf-8")
    LOG.append(f"[PATCH] {rel_path}")

# --- PATCH_101: Anti-Hallucination ---
UNKNOWN_TERMS_TXT = """
=== ЗАПРЕЩЁННЫЕ ТЕРМИНЫ (НЕ КАНОН) ===
Если игрок упоминает эти термины, отвечай: "Такого нет в каноне Warhammer 40,000".

- Новый Иерусалим (нет такой планеты в секторе Коронус)
- Патриарх Михаил (нет такого святого)
- Император-Кровопийца (нет такого титула)
- Варпоман (правильно: псайкер)
- Храм-психоз (нет такого термина)
- Ахарак (правильно: Сзарек)
- Иннарис (правильно: Иннеад)
"""

VALIDATOR_PY = r'''"""services/text_validator.py — Пост-фильтр для ответов Мастера."""
from __future__ import annotations
import re

# Словарь жестких замен
_FIXES = {
    r"\bАхарак\b": "Сзарек",
    r"\bАбадон\b": "Абаддон",
    r"\bАзуриан\b": "Асуриан",
    r"\bварпоман\b": "псайкер",
    r"\bТёмные Механикум\b": "Тёмный Механикум",
}

def scrub(text: str) -> str:
    """Применяет жесткие замены к тексту мастера."""
    if not text:
        return text
    out = text
    for pattern, repl in _FIXES.items():
        out = re.sub(pattern, repl, out, flags=re.IGNORECASE)
    
    # Если ИИ начал выдумывать Новый Иерусалим — мягко гасим
    if "Новый Иерусалим" in out:
        out = out.replace("Новый Иерусалим", "улей")
        
    return out
'''

# --- PATCH_102: Story Profiles ---
STORY_PROFILE_JSON = {
    "faction_id": "imperium",
    "opening_hooks": [
        "Наследство дяди — корабль, обременённый долгами",
        "Пропавший груз из порта Странствие",
        "Инквизитор, который ищет встречи"
    ],
    "starting_goals": ["Найти экипаж", "Разобраться с наследием"],
    "immediate_threats": ["Пираты", "Инквизиция", "Кредиторы"],
    "narrative_arc": "Негодяй с благородными задатками / имперский патриот",
    "taboo_topics": ["Хаос", "Ксеносы в экипаже"]
}

# --- Модификация module_loader ---
LOADER_ADD = '''

def get_story_profile(faction_id: str) -> dict:
    """Загружает сюжетный профиль фракции."""
    p = MODULES_DIR / ACTIVE_MODULE / "story" / f"{faction_id}.json"
    return _load_json(p)
'''

# --- Модификация master ---
MASTER_OLD = '''        try:
            from services.notes import render_notes_for_master
            nb = render_notes_for_master(state)
            if nb:
                parts.append(nb)
        except Exception:
            pass'''

MASTER_NEW = '''        try:
            from services.notes import render_notes_for_master
            nb = render_notes_for_master(state)
            if nb:
                parts.append(nb)
        except Exception:
            pass

        # PATCH_102: Story Profiles
        try:
            from services.module_loader import get_story_profile
            fid = str(state.get("faction_id") or "imperium")
            sp = get_story_profile(fid)
            if sp:
                lines = ["=== СЮЖЕТНЫЙ ПРОФИЛЬ (СКРЫТО ОТ ИГРОКА) ==="]
                if sp.get("opening_hooks"):
                    lines.append("Крючки: " + "; ".join(sp["opening_hooks"]))
                if sp.get("starting_goals"):
                    lines.append("Цели: " + "; ".join(sp["starting_goals"]))
                if sp.get("immediate_threats"):
                    lines.append("Угрозы: " + "; ".join(sp["immediate_threats"]))
                if sp.get("narrative_arc"):
                    lines.append("Арка: " + str(sp["narrative_arc"]))
                parts.append("\\n".join(lines))
        except Exception as e:
            print("[master] story profile fail: " + type(e).__name__)
'''

# --- Модификация master (scrub) ---
MASTER_SCRUB_OLD = '''            if _is_gigachat_refusal(text):
                print("[master] GigaChat refused — fallback")
                return _master_refusal_fallback()
            return text'''

MASTER_SCRUB_NEW = '''            if _is_gigachat_refusal(text):
                print("[master] GigaChat refused — fallback")
                return _master_refusal_fallback()
            
            # PATCH_101: Anti-Hallucination
            try:
                from services.text_validator import scrub
                text = scrub(text)
            except Exception as e:
                print("[master] scrub fail: " + type(e).__name__)
            return text'''

def main() -> int:
    print("=== PATCH_101 + PATCH_102 ===\n")

    # 1. Anti-Hallucination
    write_file("data/modules/rogue_trader/lore/unknown_terms.txt", UNKNOWN_TERMS_TXT)
    write_file("services/text_validator.py", VALIDATOR_PY)

    # 2. Story Profiles
    p = ROOT / "data" / "modules" / "rogue_trader" / "story" / "imperium.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(STORY_PROFILE_JSON, ensure_ascii=False, indent=2), encoding="utf-8")
    LOG.append("[CREATE] data/modules/rogue_trader/story/imperium.json")

    # 3. Патчим loader
    loader_path = ROOT / "services" / "module_loader.py"
    text = loader_path.read_text(encoding="utf-8")
    if "def get_story_profile" not in text:
        text += LOADER_ADD
        loader_path.write_text(text, encoding="utf-8")
        LOG.append("[PATCH] module_loader.py: + get_story_profile")

    # 4. Патчим master
    patch_file("services/master.py", MASTER_OLD, MASTER_NEW)
    patch_file("services/master.py", MASTER_SCRUB_OLD, MASTER_SCRUB_NEW)

    print("\n".join(LOG))
    print("\n=== ПРОВЕРКИ ===")
    print("1. python -c \"import app\"")
    print("2. python -m pytest tests/ -q")
    print("\nDONE — PATCH_101 + PATCH_102.")
    return 0

if __name__ == "__main__":
    sys.exit(main())