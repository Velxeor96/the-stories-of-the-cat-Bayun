# scripts/patch.py — PATCH_100c
# Валидация wounds и fate: значения не уходят в минус.
# Системный фикс: работает с любым форматированием state_manager.py.
from __future__ import annotations
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG = []

def main() -> int:
    print("=== PATCH_100c: Валидация wounds и fate ===\n")
    path = ROOT / "services" / "state_manager.py"
    if not path.exists():
        print("[ERROR] services/state_manager.py не найден")
        return 1

    text = path.read_text(encoding="utf-8")

    # --- Шаг 1: вставляем clamp для wounds ---
    pattern_wounds = re.compile(
        r'(if "wounds" in changes:\s*\n)'
        r'(\s*w = _ensure_dict\(char, "wounds"\)\s*\n)'
        r'(\s*is_d, v = _delta\(changes\["wounds"\]\)\s*\n)'
        r'(\s*cur = int\(w\.get\("current", 0\) or 0\)\s*\n)'
        r'(\s*)w\["current"\] = \(cur \+ v\) if is_d else _to_int\(changes\["wounds"\], cur\)\s*\n'
        r'(\s*applied\.append\("wounds"\)\s*\n)'
    )
    replacement_wounds = (
        r'\1\2\3\4'
        r'\5new_val = (cur + v) if is_d else _to_int(changes["wounds"], cur)\n'
        r'\5if new_val < 0:\n'
        r'\5    new_val = 0\n'
        r'\5w["current"] = new_val\n'
        r'\6'
    )
    new_text, count_w = pattern_wounds.subn(replacement_wounds, text)
    if count_w == 0:
        print("[ERROR] Блок обработки wounds не найден. Файл не тронут.")
        print("[HINT]  Скиньте первые 80 строк services/state_manager.py, я подгоню regex.")
        return 1
    LOG.append(f"[OK]   wounds: валидация внедрена (замен: {count_w})")
    text = new_text

    # --- Шаг 2: вставляем clamp для fate ---
    pattern_fate = re.compile(
        r'(if "fate" in changes:\s*\n)'
        r'(\s*fp = _ensure_dict\(char, "fate_points"\)\s*\n)'
        r'(\s*is_d, v = _delta\(changes\["fate"\]\)\s*\n)'
        r'(\s*cur = int\(fp\.get\("current", 0\) or 0\)\s*\n)'
        r'(\s*)fp\["current"\] = \(cur \+ v\) if is_d else _to_int\(changes\["fate"\], cur\)\s*\n'
        r'(\s*applied\.append\("fate"\)\s*\n)'
    )
    replacement_fate = (
        r'\1\2\3\4'
        r'\5new_val = (cur + v) if is_d else _to_int(changes["fate"], cur)\n'
        r'\5if new_val < 0:\n'
        r'\5    new_val = 0\n'
        r'\5fp["current"] = new_val\n'
        r'\6'
    )
    new_text, count_f = pattern_fate.subn(replacement_fate, text)
    if count_f == 0:
        print("[ERROR] Блок обработки fate не найден. Файл не тронут.")
        return 1
    LOG.append(f"[OK]   fate: валидация внедрена (замен: {count_f})")
    text = new_text

    # --- Шаг 3: финальная проверка ---
    if "if new_val < 0:" not in text:
        print("[ERROR] Правки не попали в файл. Ничего не сохранено.")
        return 1

    # --- Шаг 4: сохраняем (с бэкапом) ---
    bak = path.with_suffix(path.suffix + ".bak_pre_PATCH_100c")
    if not bak.exists():
        bak.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
        LOG.append(f"[BACKUP] {bak.name}")
    path.write_text(text, encoding="utf-8")
    LOG.append("[WRITE]  services/state_manager.py обновлён")

    print("\n".join(LOG))
    print("\n=== ПРОВЕРКИ ===")
    print("1. python -m pytest tests/test_integration.py -q")
    print("2. python -m pytest tests/ -q")
    print("3. python -c \"import app\"")
    print("\nDONE — PATCH_100c.")
    return 0


if __name__ == "__main__":
    sys.exit(main())