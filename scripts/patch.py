# scripts/patch.py — PATCH_96
# Перенос JSON Империума в модули, архивация остальных.
# Перевод сервисов на module_loader.
from __future__ import annotations
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MOD_FACTIONS = ROOT / "data" / "modules" / "rogue_trader" / "factions"
INACTIVE = MOD_FACTIONS / "_inactive"
LOG = []

def move_data(src_name: str, dst_dir: Path):
    src = ROOT / "data" / src_name
    if src.exists():
        dst = dst_dir / src_name
        shutil.move(str(src), str(dst))
        # Вывод более аккуратного пути
        rel_dst = dst.relative_to(ROOT / "data" / "modules" / "rogue_trader")
        LOG.append(f"[MOVE] data/{src_name} -> data/modules/rogue_trader/{rel_dst}")

def refactor_service(svc_name: str, faction_id: str):
    path = ROOT / "services" / svc_name
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    
    # Ищем блок загрузки в старых сервисах
    pattern = r"def _load\(\) -> dict:\n    global _DATA\n    if _DATA is None:\n        p = Path\(__file__\)\.resolve\(\)\.parent\.parent / \"data\" / \".*?\.json\"\n        _DATA = json\.loads\(p\.read_text\(encoding=\"utf-8\"\)\)\n    return _DATA"
    
    replacement = f"def _load() -> dict:\n    global _DATA\n    if _DATA is None:\n        from services.module_loader import get_faction_data\n        _DATA = get_faction_data(\"{faction_id}\")\n    return _DATA"
    
    new_text, count = re.subn(pattern, replacement, text)
    if count > 0:
        path.write_text(new_text, encoding="utf-8")
        LOG.append(f"[PATCH] {svc_name} uses module_loader now")

def patch_necrons_tyranids():
    # В некронах и тиранидах пути к файлам прописаны в константах
    replacements = [
        ("necrons.py", 'ROOT / "data" / "necrons.json"', 'ROOT / "data" / "modules" / "rogue_trader" / "factions" / "_inactive" / "necrons" / "necrons.json"'),
        ("necrons.py", 'ROOT / "data" / "necrons_weapons.json"', 'ROOT / "data" / "modules" / "rogue_trader" / "factions" / "_inactive" / "necrons" / "necrons_weapons.json"'),
        ("necrons.py", 'ROOT / "data" / "necrons_armour.json"', 'ROOT / "data" / "modules" / "rogue_trader" / "factions" / "_inactive" / "necrons" / "necrons_armour.json"'),
        ("necrons.py", 'ROOT / "data" / "necrons_fleet.json"', 'ROOT / "data" / "modules" / "rogue_trader" / "factions" / "_inactive" / "necrons" / "necrons_fleet.json"'),
        ("tyranids.py", 'ROOT / "data" / "tyranids.json"', 'ROOT / "data" / "modules" / "rogue_trader" / "factions" / "_inactive" / "tyranids" / "tyranids.json"'),
        ("tyranids.py", 'ROOT / "data" / "tyranids_weapons.json"', 'ROOT / "data" / "modules" / "rogue_trader" / "factions" / "_inactive" / "tyranids" / "tyranids_weapons.json"'),
        ("tyranids.py", 'ROOT / "data" / "tyranids_armour.json"', 'ROOT / "data" / "modules" / "rogue_trader" / "factions" / "_inactive" / "tyranids" / "tyranids_armour.json"'),
        ("tyranids.py", 'ROOT / "data" / "tyranids_fleet.json"', 'ROOT / "data" / "modules" / "rogue_trader" / "factions" / "_inactive" / "tyranids" / "tyranids_fleet.json"'),
    ]
    for svc, old_path, new_path in replacements:
        path = ROOT / "services" / svc
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        if old_path in text:
            text = text.replace(old_path, new_path)
            path.write_text(text, encoding="utf-8")
            LOG.append(f"[PATCH] {svc} path updated -> _inactive")

def main() -> int:
    print("=== PATCH_96: Data Migration ===\n")
    MOD_FACTIONS.mkdir(parents=True, exist_ok=True)
    INACTIVE.mkdir(parents=True, exist_ok=True)
    (INACTIVE / "necrons").mkdir(exist_ok=True)
    (INACTIVE / "tyranids").mkdir(exist_ok=True)

    # 1. Империум (активные)
    imperium_files = [
        "imperial_guard.json", "mechanicus.json", "inquisition.json",
        "sororitas.json", "space_marines.json", "arbites.json"
    ]
    for f in imperium_files:
        move_data(f, MOD_FACTIONS)

    # 2. Некроны и Тираниды (в _inactive)
    for f in ["necrons.json", "necrons_armour.json", "necrons_fleet.json", "necrons_weapons.json"]:
        move_data(f, INACTIVE / "necrons")
    for f in ["tyranids.json", "tyranids_armour.json", "tyranids_fleet.json", "tyranids_weapons.json"]:
        move_data(f, INACTIVE / "tyranids")

    # 3. Обновляем Python-сервисы (отвязываем от старых путей)
    for svc, fid in [
        ("imperial_guard.py", "imperial_guard"),
        ("mechanicus.py", "mechanicus"),
        ("inquisition.py", "inquisition"),
        ("sororitas.py", "sororitas"),
        ("space_marines.py", "space_marines"),
        ("arbites.py", "arbites"),
    ]:
        refactor_service(svc, fid)
        
    patch_necrons_tyranids()

    print("\n".join(LOG))
    print("\n=== ПРОВЕРКИ ===")
    print("1. Тесты: python -m pytest tests/ -q")
    print("2. Игра: python -c \"import app\"")
    print("\nDONE — PATCH_96.")
    return 0

if __name__ == "__main__":
    sys.exit(main())