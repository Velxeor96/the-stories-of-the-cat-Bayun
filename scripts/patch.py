# scripts/patch.py — PATCH_93
# Генеральная уборка мусора + создание скелета модуля rogue_trader.
from __future__ import annotations
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TRASH = ROOT / "_trash_PATCH_93"
LOG = []

def to_trash(path: Path, reason: str) -> None:
    if not path.exists():
        return
    rel = path.relative_to(ROOT)
    dst = TRASH / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    try:
        shutil.move(str(path), str(dst))
        LOG.append(f"[MOVE]  {rel} -> _trash_PATCH_93/ ({reason})")
    except Exception as e:
        LOG.append(f"[ERROR] {rel}: {e}")

def main() -> int:
    print("=== PATCH_93: Генеральная уборка ===\n")
    TRASH.mkdir(exist_ok=True)
    LOG.append(f"[INIT]  Создана папка _trash_PATCH_93/")

    # 1. Старые бэкапы (оставляем только самый свежий на каждый файл)
    baks = sorted(ROOT.glob("**/*.bak_pre_PATCH_*"), key=lambda p: p.stat().st_mtime, reverse=True)
    kept = set()
    for b in baks:
        base = b.name.split(".bak_pre_PATCH_")[0]
        if base in kept:
            to_trash(b, "старый бэкап")
        else:
            kept.add(base)

    # 2. Дампы и диагностика
    for f in ["data_list.txt", "data_tree.txt", "dump_wh40k.txt", "dump_wh40k_tree.txt"]:
        to_trash(ROOT / f, "дамп/диагностика")

    # 3. Legacy папки
    to_trash(ROOT / "_reference_from_old", "устаревшая структура")
    to_trash(ROOT / "_trash_pre_PATCH_90", "старый трэш")

    # 4. Дубликаты
    to_trash(ROOT / "data" / "imperium" / "imperial_guard.json", "дубликат data/imperial_guard.json")

    # 5. Создание структуры модулей
    mod_dir = ROOT / "data" / "modules" / "rogue_trader"
    facts_dir = mod_dir / "factions"
    facts_dir.mkdir(parents=True, exist_ok=True)

    manifest = mod_dir / "manifest.json"
    if not manifest.exists():
        manifest.write_text("""{
  "id": "rogue_trader",
  "name": "Rogue Trader",
  "source_book": "Rogue Trader Core Rulebook (FFG, 2009)",
  "version": "1.0.0",
  "engine_version": "1.x",
  "factions": ["imperium"],
  "unique_mechanics": ["trade", "profit_factor", "ship_management"],
  "disabled_features": ["chaos_favor", "infamy"]
}
""", encoding="utf-8")
        LOG.append("[CREATE] data/modules/rogue_trader/manifest.json")

    LOG.append("[CREATE] data/modules/rogue_trader/factions/")

    print("\n".join(LOG))
    print("\n=== ПРОВЕРКИ ===")
    print(f"manifest.json существует: {manifest.exists()}")
    print(f"factions_dir существует: {facts_dir.exists()}")
    print("\nDONE — PATCH_93.")
    return 0

if __name__ == "__main__":
    sys.exit(main())