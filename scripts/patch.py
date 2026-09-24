# scripts/patch.py
# PATCH_16L — убрать data/ из .gitignore, чтобы лор ушёл на GitHub.
# Оставляем защищёнными: data/users/, data/accounts/, data/_replacements/.
# Запуск: python scripts\patch.py
from __future__ import annotations

import shutil
import sys
from pathlib import Path

TAG = "PATCH_16L"
ROOT = Path(__file__).resolve().parent.parent
GITIGNORE = ROOT / ".gitignore"

PROTECTED_MUST_EXIST = (
    "data/users/",
    "data/accounts/",
)
PROTECTED_ADD_IF_MISSING = (
    "data/_replacements/",
)


def _has_line(lines, needle):
    for ln in lines:
        if ln.strip() == needle:
            return True
    return False


def main():
    print("=" * 64)
    print("PATCH " + TAG + " — gitignore: открыть data/ для лора")
    print("ROOT: " + str(ROOT))
    print("=" * 64)

    if not GITIGNORE.exists():
        print("  ERROR: .gitignore not found")
        return 1

    try:
        src = GITIGNORE.read_text(encoding="utf-8")
    except Exception as e:
        print("  ERROR read: " + type(e).__name__ + ": " + str(e))
        return 1

    lines = src.splitlines()

    if not _has_line(lines, "data/"):
        print("  skip (data/ already removed)")
        # На всякий случай проверим, что защита есть
        missing = [p for p in PROTECTED_MUST_EXIST if not _has_line(lines, p)]
        if missing:
            print("  WARNING: missing protected rules: " + ", ".join(missing))
            print("  добавь их в .gitignore руками и повтори патч")
            return 2
        print("  защита data/users/, data/accounts/ на месте")
        return 0

    # Заменяем строку data/ на два комментария
    out = []
    removed = 0
    for line in lines:
        if line.strip() == "data/":
            out.append("# data/ убрано в PATCH_16L — лор должен уходить на GitHub.")
            out.append("# Приватные части data/ исключаются отдельными правилами ниже.")
            removed += 1
            continue
        out.append(line)

    # Добавляем data/_replacements/, если ещё нет
    added_rep = False
    if not _has_line(out, PROTECTED_ADD_IF_MISSING[0]):
        out.append("")
        out.append("# служебные материалы, публиковать не нужно")
        out.append(PROTECTED_ADD_IF_MISSING[0])
        added_rep = True

    new_src = "\n".join(out)
    if not new_src.endswith("\n"):
        new_src += "\n"

    # Проверка, что защита осталась
    new_lines = new_src.splitlines()
    missing = [p for p in PROTECTED_MUST_EXIST if not _has_line(new_lines, p)]

    # Бэкап
    bak = GITIGNORE.with_name(".gitignore.bak_pre_" + TAG)
    try:
        shutil.copy2(GITIGNORE, bak)
    except Exception as e:
        print("  ERROR backup: " + type(e).__name__ + ": " + str(e))
        return 1

    # Запись
    try:
        GITIGNORE.write_text(new_src, encoding="utf-8")
    except Exception as e:
        print("  ERROR write: " + type(e).__name__ + ": " + str(e))
        return 1

    print("  .gitignore -> backup + patched")
    print("    строк data/ удалено:  " + str(removed))
    print("    добавлено _replacements/:  " + ("да" if added_rep else "нет (уже было)"))
    if missing:
        print("  !!! WARNING: после правки не найдены: " + ", ".join(missing))
        print("  !!! проверь .gitignore и добавь их вручную")
    else:
        print("  защита data/users/, data/accounts/ — на месте")

    print()
    print("=" * 64)
    print("Дальше проверь руками, что data/ НЕ игнорируется, а users/ — игнорируется:")
    print()
    print("  git check-ignore -v data/general/general_rules.txt")
    print("  git check-ignore -v data/users/Admin/settings.json")
    print()
    print("Ожидаемо:")
    print("  1-я команда — ПУСТО (файл будет отслеживаться)")
    print("  2-я команда — строка с правилом data/users/ (файл не уйдёт)")
    print()
    print("Если так — добавь лор в git:")
    print()
    print("  git add data/")
    print("  git status --short data/")
    print()
    print("ВАЖНО: в выводе НЕ ДОЛЖНО быть data/users/ и data/accounts/.")
    print("Если они там — откати командой:  git reset data/")
    print()
    print("Если чисто:")
    print("  git commit -m \"lore: publish data/*.txt (rules, factions, glossary)\"")
    print("  git push origin main")
    print("  Streamlit Cloud -> Reboot app")
    print("=" * 64)
    return 0


if __name__ == "__main__":
    sys.exit(main())