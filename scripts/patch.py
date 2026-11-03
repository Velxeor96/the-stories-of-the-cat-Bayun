# scripts/patch.py — PATCH_99
# Ограничение wizard до одной фракции (imperium) + защита в character_creation.
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG = []

def patch_wizard():
    """Ограничивает список фракций до imperium."""
    path = ROOT / "ui" / "screens" / "wizard.py"
    if not path.exists():
        LOG.append("[ERROR] ui/screens/wizard.py не найден")
        return
    text = path.read_text(encoding="utf-8")

    old_block = '''    st.markdown("#### 2. Фракция")
    faction_ids = list(FACTIONS.keys())
    faction_id = st.selectbox(
        "Фракция", options=faction_ids,
        format_func=lambda x: FACTIONS[x]["name"],
        key="wz_faction", on_change=_reset_subfaction_key,
    )'''

    new_block = '''    st.markdown("#### 2. Фракция")
    # PATCH_99: пока активен только модуль rogue_trader, играем за Империум.
    _ALLOWED_FACTIONS = ["imperium"]
    faction_id = st.selectbox(
        "Фракция", options=_ALLOWED_FACTIONS,
        format_func=lambda x: FACTIONS.get(x, {}).get("name", x),
        key="wz_faction", on_change=_reset_subfaction_key,
    )'''

    if old_block in text:
        text = text.replace(old_block, new_block)
        path.write_text(text, encoding="utf-8")
        LOG.append("[PATCH] wizard.py: фракция ограничена imperium")
    else:
        LOG.append("[WARN] wizard.py: якорь для блока фракции не найден, проверьте вручную")


def patch_character_creation():
    """Добавляет проверку в build_character: только imperium."""
    path = ROOT / "services" / "character_creation.py"
    if not path.exists():
        LOG.append("[ERROR] services/character_creation.py не найден")
        return
    text = path.read_text(encoding="utf-8")

    old_block = '''    if faction_id not in FACTIONS:
        raise ValueError("Неизвестная фракция: " + str(faction_id))'''

    new_block = '''    if faction_id not in FACTIONS:
        raise ValueError("Неизвестная фракция: " + str(faction_id))

    # PATCH_99: пока активен только модуль rogue_trader.
    # Для других фракций (эльдары, хаос, орки, тау и т.д.) данные
    # лежат в data/modules/rogue_trader/factions/_inactive/ и не загружаются.
    _ACTIVE_FACTIONS = {"imperium"}
    if faction_id not in _ACTIVE_FACTIONS:
        raise ValueError(
            "Фракция '" + str(faction_id) + "' пока недоступна. "
            "Сейчас играбелен только Империум (модуль Rogue Trader). "
            "Остальные фракции появятся в DLC."
        )'''

    if old_block in text:
        text = text.replace(old_block, new_block)
        path.write_text(text, encoding="utf-8")
        LOG.append("[PATCH] character_creation.py: активна только imperium")
    else:
        LOG.append("[WARN] character_creation.py: якорь для проверки фракции не найден")


def main() -> int:
    print("=== PATCH_99: Ограничение до Империума ===\n")

    patch_wizard()
    patch_character_creation()

    print("\n".join(LOG))
    print("\n=== ПРОВЕРКИ ===")
    print("1. python -c \"import app\"")
    print("2. python -c \"from services.character_creation import build_character; build_character(name='X',gender='male',age='30',appearance='',user_background='',faction_id='eldar',characteristics={})\"  # должен упасть с понятной ошибкой")
    print("3. python -m pytest tests/ -q")
    print("\nDONE — PATCH_99.")
    return 0


if __name__ == "__main__":
    sys.exit(main())