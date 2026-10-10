# scripts/patch.py — PATCH_75b: безопасное чтение .gitignore + дозапись дампов
from __future__ import annotations
import ast, sys
from pathlib import Path

TAG = "PATCH_75b"
ROOT = Path(__file__).resolve().parent.parent
if not (ROOT / "app.py").exists():
    print("[ERROR] app.py не найден.")
    sys.exit(1)

r = {"modified": [], "errors": []}


def _read_any(p: Path) -> str:
    """Пробует UTF-8, потом CP1251, потом latin-1."""
    for enc in ("utf-8", "cp1251", "latin-1"):
        try:
            return p.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
    return p.read_text(encoding="utf-8", errors="replace")


# === 1) Проверить, что секция «КРИТИЧЕСКИЕ ИСХОДЫ» в master_core.txt есть ===
p = ROOT / "prompts" / "master_core.txt"
text = _read_any(p)
if "КРИТИЧЕСКИЕ ИСХОДЫ" in text:
    r["modified"].append("master_core.txt — секция КРИТИЧЕСКИЕ ИСХОДЫ на месте")
else:
    r["errors"].append("master_core.txt: секция КРИТИЧЕСКИЕ ИСХОДЫ НЕ найдена")


# === 2) .gitignore — читаем в любой кодировке, перезаписываем в UTF-8 ===
p = ROOT / ".gitignore"
text = _read_any(p)

NEEDED = [
    "scripts/_d*.txt",
    "scripts/_diag*.txt",
]

missing = [pat for pat in NEEDED if pat not in text]

if not missing:
    r["modified"].append(".gitignore — паттерны дампов уже есть")
else:
    # Бэкап
    bak = p.with_suffix(p.suffix + ".bak_pre_" + TAG)
    if not bak.exists():
        try:
            bak.write_bytes(p.read_bytes())
        except Exception:
            pass

    add_lines = "\n# PATCH_75b: дампы патчей\n"
    for pat in missing:
        add_lines += pat + "\n"

    new_text = text.rstrip() + "\n" + add_lines
    # Перезаписываем в UTF-8 — теперь все комментарии будут корректны
    p.write_text(new_text, encoding="utf-8")
    r["modified"].append(
        ".gitignore — перезаписан в UTF-8, +" + str(len(missing)) + " паттерна"
    )


print("=== PATCH " + TAG + " ===")
for m in r["modified"]:
    print("  [MODIFIED] " + m)
for e in r["errors"]:
    print("  [ERROR] " + e)
print("DONE" if not r["errors"] else "DONE (with errors)")