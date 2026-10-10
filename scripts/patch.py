# scripts/patch.py — PATCH_92
# Добавляет torch (CPU) + sentence-transformers в requirements.txt.
# Без этого RAG в Streamlit Cloud падает на импорте и работает на fallback.
from __future__ import annotations
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TAG = "PATCH_92"


def main() -> int:
    p = ROOT / "requirements.txt"
    if not p.exists():
        print("[ERROR] requirements.txt не найден: " + str(p))
        return 1

    bak = p.with_suffix(p.suffix + ".bak_pre_" + TAG)
    if not bak.exists():
        shutil.copy2(p, bak)
        print("[OK]   backup: " + bak.name)

    content = p.read_text(encoding="utf-8")
    lines = [l.rstrip() for l in content.splitlines()]
    non_empty = [l.strip() for l in lines if l.strip()]

    has_st = any(l.startswith("sentence-transformers") for l in non_empty)
    has_torch = any(l == "torch" or l.startswith("torch==")
                    or l.startswith("torch ") for l in non_empty)
    has_extra = any("download.pytorch.org" in l for l in non_empty)

    if has_st and has_torch and has_extra:
        print("[SKIP] requirements.txt уже содержит всё нужное")
        return 0

    new_lines: list[str] = []
    if not has_extra:
        new_lines.append("--extra-index-url https://download.pytorch.org/whl/cpu")
    new_lines.extend(lines)
    if not has_torch:
        new_lines.append("torch")
    if not has_st:
        new_lines.append("sentence-transformers")

    # Убираем возможные хвостовые пустые строки
    while new_lines and not new_lines[-1].strip():
        new_lines.pop()
    new_lines.append("")  # финальный \n

    p.write_text("\n".join(new_lines), encoding="utf-8")

    print("[OK]   requirements.txt обновлён")
    if not has_extra:
        print("       + --extra-index-url https://download.pytorch.org/whl/cpu")
    if not has_torch:
        print("       + torch")
    if not has_st:
        print("       + sentence-transformers")

    print("\nDONE — " + TAG)
    return 0


if __name__ == "__main__":
    sys.exit(main())