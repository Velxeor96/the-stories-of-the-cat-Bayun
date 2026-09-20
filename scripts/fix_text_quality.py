# fix_text_quality.py
# Убирает мусор из файлов базы знаний:
# - английские абзацы
# - дубликаты абзацев
# - битые заголовки
# - осколки английского внутри строк
# Плюс применяет замены из _replacements/replacements.txt.
#
# Использование:
#   python fix_text_quality.py --dry-run          # показать, что будет сделано
#   python fix_text_quality.py --file <path>      # один файл
#   python fix_text_quality.py --folder eldar     # вся папка
#   python fix_text_quality.py --all              # вся база

import os
import re
import sys
import shutil
import argparse
from datetime import datetime


DATA_DIR = "data"
BACKUP_DIR = "data_backup"
REPLACEMENTS_FILE = "_replacements/replacements.txt"


# ============================================================
# ЗАГРУЗКА ПРАВИЛ
# ============================================================
def load_replacements():
    """Возвращает список (паттерн, замена, комментарий)."""
    if not os.path.exists(REPLACEMENTS_FILE):
        print(f"⚠ Файл {REPLACEMENTS_FILE} не найден, замены пропущены.")
        return []

    rules = []
    with open(REPLACEMENTS_FILE, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line.strip() or line.strip().startswith("#"):
                continue
            parts = line.split("|")
            if len(parts) < 2:
                continue
            wrong = parts[0].strip()
            right = parts[1].strip() if len(parts) > 1 else ""
            comment = parts[2].strip() if len(parts) > 2 else ""
            if wrong:
                rules.append((wrong, right, comment))
    return rules


def apply_case(original: str, replacement: str) -> str:
    """Сохраняет регистр: ШУРИКЕН → СЮРИКЕН, Шурикен → Сюрикен, шурикен → сюрикен."""
    if not original:
        return replacement
    if original.isupper():
        return replacement.upper()
    if original[0].isupper():
        return replacement[0].upper() + replacement[1:]
    return replacement


def apply_replacements(text, rules):
    """Применяет замены. Возвращает (новый_текст, количество_замен)."""
    total = 0
    for wrong, right, _ in rules:
        # Границы слова — чтобы "Шурикен" не нашлось внутри "Шурикеновая"
        pattern = re.compile(r"\b" + re.escape(wrong) + r"\b", re.IGNORECASE)

        def repl(match):
            return apply_case(match.group(0), right) if right else ""

        new_text, count = pattern.subn(repl, text)
        total += count
        text = new_text
    return text, total


# ============================================================
# УБОРКА МУСОРА
# ============================================================
def _is_mostly_english(text: str) -> bool:
    """Абзац больше чем наполовину английский?"""
    letters = [c for c in text if c.isalpha()]
    if len(letters) < 20:
        return False
    latin = sum(1 for c in letters if "a" <= c.lower() <= "z")
    cyrillic = sum(1 for c in letters if "а" <= c.lower() <= "я" or c.lower() == "ё")
    if latin + cyrillic == 0:
        return False
    return latin / (latin + cyrillic) > 0.5


def remove_english_paragraphs(text: str) -> str:
    """Убирает абзацы, состоящие преимущественно из английского."""
    paragraphs = text.split("\n\n")
    kept = []
    for p in paragraphs:
        p = p.strip()
        if not p:
            continue
        # Не удаляем заголовки (=== ... ===)
        if p.startswith("===") and p.endswith("==="):
            kept.append(p)
            continue
        if _is_mostly_english(p):
            continue
        kept.append(p)
    return "\n\n".join(kept)


def remove_duplicate_paragraphs(text: str, min_length: int = 60) -> str:
    """Убирает повторяющиеся абзацы (длиннее min_length символов)."""
    paragraphs = text.split("\n\n")
    seen = set()
    kept = []
    for p in paragraphs:
        p_stripped = p.strip()
        if not p_stripped:
            continue
        # Нормализуем: убираем пробелы, регистр
        key = re.sub(r"\s+", " ", p_stripped.lower())
        if len(p_stripped) >= min_length and key in seen:
            continue
        if len(p_stripped) >= min_length:
            seen.add(key)
        kept.append(p)
    return "\n\n".join(kept)


def remove_empty_headers(text: str) -> str:
    """Убирает заголовки, за которыми нет текста (пустые секции)."""
    paragraphs = text.split("\n\n")
    kept = []
    for i, p in enumerate(paragraphs):
        p_stripped = p.strip()
        if p_stripped.startswith("===") and p_stripped.endswith("==="):
            # Смотрим следующий непустой
            next_text = ""
            for j in range(i + 1, len(paragraphs)):
                if paragraphs[j].strip():
                    next_text = paragraphs[j].strip()
                    break
            # Если следующего нет или он тоже заголовок — удаляем текущий
            if not next_text or (next_text.startswith("===") and next_text.endswith("===")):
                continue
        kept.append(p)
    return "\n\n".join(kept)


def collapse_blank_lines(text: str) -> str:
    """Убирает больше двух переносов подряд."""
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# ============================================================
# ОБРАБОТКА ФАЙЛА
# ============================================================
def process_file(path: str, rules, dry_run: bool = False) -> dict:
    try:
        with open(path, encoding="utf-8") as f:
            original = f.read()
    except Exception as e:
        return {"status": "error", "error": str(e)}

    text = original

    # Считаем длину до
    len_before = len(text)

    # 1. Замены
    text, replaces_count = apply_replacements(text, rules)

    # 2. Уборка английских абзацев
    text = remove_english_paragraphs(text)

    # 3. Уборка дубликатов
    text = remove_duplicate_paragraphs(text)

    # 4. Уборка пустых заголовков
    text = remove_empty_headers(text)

    # 5. Уборка лишних переносов
    text = collapse_blank_lines(text)

    len_after = len(text)

    changed = text != original

    if changed and not dry_run:
        # Бэкап
        today = datetime.now().strftime("%Y-%m-%d")
        rel = os.path.relpath(path, DATA_DIR)
        backup_path = os.path.join(BACKUP_DIR, today, rel)
        os.makedirs(os.path.dirname(backup_path), exist_ok=True)
        shutil.copy2(path, backup_path)

        with open(path, "w", encoding="utf-8") as f:
            f.write(text)

    return {
        "status": "changed" if changed else "clean",
        "replaces": replaces_count,
        "before": len_before,
        "after": len_after,
        "delta": len_before - len_after,
    }


# ============================================================
# СБОР ФАЙЛОВ
# ============================================================
def collect_files(args) -> list:
    files = []
    if args.file:
        if os.path.isfile(args.file):
            files.append(args.file)
    elif args.folder:
        folder_path = os.path.join(DATA_DIR, args.folder)
        if os.path.isdir(folder_path):
            for root, _, fs in os.walk(folder_path):
                for fn in fs:
                    if fn.endswith(".txt"):
                        files.append(os.path.join(root, fn))
    elif args.all:
        for root, _, fs in os.walk(DATA_DIR):
            for fn in fs:
                if fn.endswith(".txt"):
                    files.append(os.path.join(root, fn))
    return sorted(files)


# ============================================================
# MAIN
# ============================================================
def main():
    parser = argparse.ArgumentParser(description="Уборка мусора в базе знаний.")
    parser.add_argument("--dry-run", action="store_true", help="Не сохранять")
    parser.add_argument("--file", help="Обработать один файл")
    parser.add_argument("--folder", help="Обработать одну папку в data/")
    parser.add_argument("--all", action="store_true", help="Обработать всю базу")
    args = parser.parse_args()

    if not (args.file or args.folder or args.all):
        parser.print_help()
        return

    rules = load_replacements()
    print(f"📋 Правил замен загружено: {len(rules)}")
    print(f"🔧 Режим: {'DRY-RUN (без сохранения)' if args.dry_run else 'Сохранение'}")
    print()

    files = collect_files(args)
    if not files:
        print("❌ Файлы не найдены.")
        return

    print(f"📂 Файлов для обработки: {len(files)}\n")
    print("=" * 70)

    total_changed = 0
    total_saved_bytes = 0

    for path in files:
        rel = os.path.relpath(path, DATA_DIR).replace("\\", "/")
        result = process_file(path, rules, dry_run=args.dry_run)

        if result["status"] == "error":
            print(f"❌ {rel}: {result['error']}")
            continue

        if result["status"] == "clean":
            print(f"✓ {rel} (без изменений)")
        else:
            total_changed += 1
            total_saved_bytes += result["delta"]
            print(
                f"🔧 {rel}: замен={result['replaces']}, "
                f"было={result['before']} → стало={result['after']} "
                f"(−{result['delta']} симв.)"
            )

    print("=" * 70)
    print(f"Изменено файлов: {total_changed}/{len(files)}")
    print(f"Убрано символов: {total_saved_bytes}")
    if args.dry_run:
        print("\n⚠ DRY-RUN. Ничего не сохранено.")
    else:
        print(f"\n✅ Бэкапы в: {os.path.abspath(BACKUP_DIR)}")


if __name__ == "__main__":
    main()