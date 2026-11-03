# scripts/patch.py — PATCH_97
# Объединение state_parser и state_applier в state_manager. Удаление master_actions.
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG = []

def main() -> int:
    print("=== PATCH_97: State Manager ===\n")
    
    parser_path = ROOT / "services" / "state_parser.py"
    applier_path = ROOT / "services" / "state_applier.py"
    
    if not parser_path.exists() or not applier_path.exists():
        print("[ERROR] Не найдены исходные файлы state_parser.py или state_applier.py")
        return 1

    parser_text = parser_path.read_text(encoding="utf-8")
    applier_text = applier_path.read_text(encoding="utf-8")
    
    # Безопасно вырезаем тела функций.
    parser_body = parser_text.split('import re\n', 1)[-1]
    applier_body = applier_text.split('from __future__ import annotations\n', 1)[-1]
    
    lines = []
    lines.append('"""services/state_manager.py — парсинг [STATE] и применение к персонажу.')
    lines.append('')
    lines.append('PATCH_97: Объединяет state_parser и state_applier в единый менеджер.')
    lines.append('"""')
    lines.append('from __future__ import annotations')
    lines.append('import re')
    lines.append('')
    lines.append('# --- Из state_parser ---')
    lines.append(parser_body.strip())
    lines.append('')
    lines.append('# --- Из state_applier ---')
    lines.append(applier_body.strip())
    lines.append('')
    lines.append('')
    lines.append('def parse_and_apply(narrative: str, char: dict) -> tuple[str, list[str]]:')
    lines.append('    """Парсит [STATE] и сразу применяет к персонажу."""')
    lines.append('    clean_text, changes = parse_state(narrative)')
    lines.append('    if not changes:')
    lines.append('        return clean_text, []')
    lines.append('    applied = apply_changes(char, changes)')
    lines.append('    return clean_text, applied')
    lines.append('')
    
    merged = "\n".join(lines)
    
    sm_path = ROOT / "services" / "state_manager.py"
    sm_path.write_text(merged, encoding="utf-8")
    LOG.append("[CREATE] services/state_manager.py")

    # Удаляем старые и мертвые файлы
    for f in ["state_parser.py", "state_applier.py", "master_actions.py"]:
        p = ROOT / "services" / f
        if p.exists():
            p.unlink()
            LOG.append(f"[DELETE] services/{f}")

    # Обновляем game.py
    game_path = ROOT / "ui" / "screens" / "game.py"
    if game_path.exists():
        text = game_path.read_text(encoding="utf-8")
        
        # Меняем импорты
        text = text.replace(
            "from services.state_parser import parse_state\nfrom services.state_applier import apply_changes",
            "from services.state_manager import parse_and_apply"
        )
        
        # Меняем вызов
        old_logic = """        clean_text, changes = parse_state(_narr_full)
        if changes:
            applied = apply_changes(char, changes)
            if applied:
                _save_char(login, char_name, char)
                print("[game] state applied: " + ", ".join(applied))"""
        
        new_logic = """        clean_text, applied = parse_and_apply(_narr_full, char)
        if applied:
            _save_char(login, char_name, char)
            print("[game] state applied: " + ", ".join(applied))"""
        
        if old_logic in text:
            text = text.replace(old_logic, new_logic)
            game_path.write_text(text, encoding="utf-8")
            LOG.append("[PATCH] ui/screens/game.py uses parse_and_apply")
        else:
            LOG.append("[WARN] ui/screens/game.py: якорь не найден, проверьте вручную")

    print("\n".join(LOG))
    print("\n=== ПРОВЕРКИ ===")
    print("python -m pytest tests/ -q")
    print("python -c \"import app\"")
    print("\nDONE — PATCH_97.")
    return 0

if __name__ == "__main__":
    sys.exit(main())