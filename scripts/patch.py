# scripts/patch.py — PATCH_73c: фикс списка тестеров
from __future__ import annotations
import ast, re, shutil, sys
from pathlib import Path

TAG = "PATCH_73c"
ROOT = Path(__file__).resolve().parent.parent
if not (ROOT / "app.py").exists():
    print("[ERROR] app.py не найден.")
    sys.exit(1)

r = {"modified": [], "errors": []}

def _bk(p):
    b = p.with_suffix(p.suffix + ".bak_pre_" + TAG)
    if not b.exists() and p.exists():
        try:
            shutil.copy2(p, b)
        except Exception:
            pass

p = ROOT / "ui" / "screens" / "credits.py"
text = p.read_text(encoding="utf-8")

# Целевой список
TARGET = [
    "Ксения",
    "Кайса",
    "Puslik",
    "Игорь",
    "Сергей",
    "Роман",
    "Валерий",
    "друзья Романа (кем бы вы ни были, ребят)",
]

# Найдём блок THANKS_NAMES = [...] по регулярке
pattern = re.compile(
    r"THANKS_NAMES\s*=\s*\[(.*?)\]",
    re.DOTALL,
)
m = pattern.search(text)
if not m:
    r["errors"].append("credits.py: блок THANKS_NAMES не найден")
else:
    # Парсим текущие строки
    old_body = m.group(1)
    old_names = re.findall(r'"([^"]*)"', old_body)

    # Проверим, что уже целевое
    if old_names == TARGET:
        r["modified"].append("credits.py — список уже целевой")
    else:
        # Собираем новый блок
        new_lines = ["THANKS_NAMES = ["]
        for n in TARGET:
            new_lines.append('    "' + n + '",')
        new_lines.append("]")
        new_block = "\n".join(new_lines)

        nt = text[:m.start()] + new_block + text[m.end():]
        try:
            ast.parse(nt)
        except SyntaxError as e:
            r["errors"].append("credits.py syntax: " + str(e))
        else:
            _bk(p)
            p.write_text(nt, encoding="utf-8")
            r["modified"].append(
                "credits.py — список тестеров обновлён ("
                + str(len(old_names)) + " → " + str(len(TARGET)) + ")"
            )
            # Покажем diff
            removed = [n for n in old_names if n not in TARGET]
            added = [n for n in TARGET if n not in old_names]
            if removed:
                print("  Убрано: " + ", ".join(removed))
            if added:
                print("  Добавлено: " + ", ".join(added))

print("=== PATCH " + TAG + " ===")
for m in r["modified"]:
    print("  [MODIFIED] " + m)
for e in r["errors"]:
    print("  [ERROR] " + e)
print("DONE" if not r["errors"] else "DONE (with errors)")