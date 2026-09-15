import os
import re
import hashlib
import shutil
import sys
from collections import defaultdict


# ============================================================
# НАСТРОЙКИ
# ============================================================
DATA_DIR = "data"
BACKUP_DIR = "data_backup"

# Возможные пути к файлу замен — скрипт попробует их по очереди
REPLACEMENTS_CANDIDATES = [
    os.path.join("_replacements", "replacements.txt"),
    os.path.join("replacements", "replacements.txt"),
    "replacements.txt",
    os.path.join(DATA_DIR, "_replacements", "replacements.txt"),
    os.path.join(DATA_DIR, "replacements", "replacements.txt"),
    os.path.join(DATA_DIR, "_replacement", "replacements.txt"),
    os.path.join(DATA_DIR, "_replacements.txt"),
    os.path.join(DATA_DIR, "replacements.txt"),
]

# Папки внутри data/, которые НЕ нужно трогать при чистке
SKIP_DIRS = {"_replacements", "_replacement", "_glossary", "_backup", "__pycache__"}

DRY_RUN = "--dry-run" in sys.argv


# ============================================================
# ПОИСК ФАЙЛА ЗАМЕН
# ============================================================
def find_replacements_file():
    for path in REPLACEMENTS_CANDIDATES:
        if os.path.exists(path):
            return path
    return None


# ============================================================
# НОРМАЛИЗАЦИЯ ПУТИ
# ============================================================
def normalize_path(path):
    """Приводит путь к формату с прямыми слэшами."""
    return path.replace("\\", "/")


# ============================================================
# ЧТЕНИЕ ПРАВИЛ ЗАМЕН
# ============================================================
def load_replacements(path):
    """
    Читает файл замен.

    Поддерживает строки-исключения:
        # EXCEPT: file1.txt, file2.txt
    Исключения действуют на СЛЕДУЮЩЕЕ правило.

    Возвращает список словарей:
        [{"wrong": ..., "right": ..., "comment": ..., "except_files": [...]}, ...]
    """
    if path is None or not os.path.exists(path):
        print("❌ Файл с заменами не найден.")
        print("   Искал в следующих местах:")
        for p in REPLACEMENTS_CANDIDATES:
            print(f"     - {p}")
        sys.exit(1)

    print(f"   Найден файл: {path}")

    rules = []
    pending_except = []

    with open(path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            raw = line.rstrip("\n")
            stripped = raw.strip()

            if not stripped:
                continue

            # Строка исключения: # EXCEPT: file1, file2
            if stripped.upper().startswith("# EXCEPT:"):
                files_str = stripped[len("# EXCEPT:"):].strip()
                pending_except = [
                    normalize_path(f.strip())
                    for f in files_str.split(",")
                    if f.strip()
                ]
                continue

            # Обычный комментарий
            if stripped.startswith("#"):
                continue

            # Правило
            parts = raw.split("|")
            if len(parts) < 2:
                print(f"⚠ Строка {line_num}: неправильный формат → {stripped}")
                continue

            wrong = parts[0].strip()
            right = parts[1].strip() if len(parts) >= 2 else ""
            comment = parts[2].strip() if len(parts) >= 3 else ""

            if not wrong:
                print(f"⚠ Строка {line_num}: пустое поле 'неправильно'")
                continue

            rules.append({
                "wrong": wrong,
                "right": right,
                "comment": comment,
                "except_files": pending_except,
            })
            pending_except = []

    return rules


# ============================================================
# ЗАМЕНА С УЧЁТОМ РЕГИСТРА
# ============================================================
def restore_case(original, replacement):
    if not original or not replacement:
        return replacement
    if original.isupper():
        return replacement.upper()
    if original[0].isupper() and original[1:].islower():
        return replacement[0].upper() + replacement[1:].lower()
    return replacement.lower()


def apply_rule(text, wrong, right):
    pattern = re.compile(re.escape(wrong), re.IGNORECASE)

    def repl(match):
        original = match.group(0)
        if not right:
            return ""
        return restore_case(original, right)

    new_text, count = pattern.subn(repl, text)
    return new_text, count


def clean_text(text, rules, current_file_rel):
    """
    Применяет все правила, учитывая исключения по файлам.
    current_file_rel — относительный путь файла от data/,
    в формате с прямыми слэшами (например, "chaos/dark_mechanicum.txt").
    """
    total = 0
    applied = []
    current = text

    for rule in rules:
        wrong = rule["wrong"]
        right = rule["right"]
        except_files = rule["except_files"]

        # Проверяем, не входит ли текущий файл в список исключений
        if current_file_rel in except_files:
            continue

        new_text, count = apply_rule(current, wrong, right)
        if count > 0:
            applied.append((wrong, right, count))
            total += count
            current = new_text

    # Убираем двойные пробелы и пробелы перед знаками препинания
    current = re.sub(r"[ \t]{2,}", " ", current)
    current = re.sub(r"\s+([,.!?;:])", r"\1", current)

    return current, total, applied


# ============================================================
# ОБХОД ФАЙЛОВ
# ============================================================
def find_txt_files(root_dir):
    result = []
    for root, dirs, files in os.walk(root_dir):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fname in files:
            if fname.endswith(".txt"):
                result.append(os.path.join(root, fname))
    return result


# ============================================================
# РЕЗЕРВНОЕ КОПИРОВАНИЕ
# ============================================================
def make_backup(files, backup_dir):
    if os.path.exists(backup_dir):
        print(f"⚠ Папка {backup_dir}/ уже существует.")
        answer = input("  Перезаписать? (y/N): ").strip().lower()
        if answer != "y":
            print("  Пропускаю создание резервной копии.")
            return False
        shutil.rmtree(backup_dir)

    os.makedirs(backup_dir)
    for path in files:
        rel = os.path.relpath(path, DATA_DIR)
        dst = os.path.join(backup_dir, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(path, dst)
    print(f"  ✅ Резервная копия создана: {backup_dir}/ ({len(files)} файлов)")
    return True


# ============================================================
# ПОИСК ДУБЛИКАТОВ
# ============================================================
def file_hash(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception:
        return None
    normalized = re.sub(r"\s+", " ", content.lower()).strip()
    return hashlib.md5(normalized.encode("utf-8")).hexdigest()


def find_duplicates(files):
    hashes = defaultdict(list)
    for path in files:
        h = file_hash(path)
        if h:
            hashes[h].append(path)
    return {h: paths for h, paths in hashes.items() if len(paths) > 1}


# ============================================================
# ГЛАВНАЯ ФУНКЦИЯ
# ============================================================
def main():
    print("=" * 60)
    print("ЧИСТКА БАЗЫ ЗНАНИЙ")
    if DRY_RUN:
        print("⚠ РЕЖИМ СУХОГО ПРОГОНА — файлы не будут изменены")
    print("=" * 60)

    if not os.path.exists(DATA_DIR):
        print(f"❌ Папка {DATA_DIR}/ не найдена.")
        return

    # === Загрузка правил ===
    print(f"\n📖 Ищу файл с заменами...")
    replacements_file = find_replacements_file()
    rules = load_replacements(replacements_file)
    print(f"  ✅ Загружено {len(rules)} правил.")

    # === Поиск файлов ===
    files = find_txt_files(DATA_DIR)
    print(f"\n📂 Найдено {len(files)} .txt файлов для обработки.")

    if not files:
        print("Нечего обрабатывать. Завершаю.")
        return

    # === Резервная копия ===
    if not DRY_RUN:
        print(f"\n📦 Создаю резервную копию...")
        make_backup(files, BACKUP_DIR)
    else:
        print(f"\n📦 (Сухой прогон) Резервная копия не создаётся.")

    # === Применение замен ===
    print(f"\n🔧 Применяю замены...")
    total_replacements = 0
    total_files_changed = 0
    report = []

    for path in files:
        try:
            with open(path, "r", encoding="utf-8") as f:
                original = f.read()
        except Exception as e:
            print(f"  ⚠ Ошибка чтения {path}: {e}")
            continue

        # Нормализованный относительный путь
        rel = normalize_path(os.path.relpath(path, DATA_DIR))

        new_text, count, applied = clean_text(original, rules, rel)

        if count == 0:
            continue

        total_files_changed += 1
        total_replacements += count
        report.append((rel, applied))

        if not DRY_RUN:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(new_text)
            except Exception as e:
                print(f"  ⚠ Ошибка записи {path}: {e}")

    # === Отчёт по заменам ===
    print(f"\n{'=' * 60}")
    print("ОТЧЁТ ПО ЗАМЕНАМ")
    print("=" * 60)

    if not report:
        print("✅ Ничего не потребовалось менять — база уже чистая.")
    else:
        for rel, applied in report:
            print(f"\n📝 {rel}")
            for wrong, right, cnt in applied:
                arrow = right if right else "(удалено)"
                print(f"    {wrong} → {arrow}   ×{cnt}")

        print(f"\n{'=' * 60}")
        print(f"ИТОГО: {total_replacements} замен в {total_files_changed} файлах.")

    # === Поиск дубликатов ===
    print(f"\n{'=' * 60}")
    print("ПОИСК ДУБЛИКАТОВ ФАЙЛОВ")
    print("=" * 60)

    duplicates = find_duplicates(files)

    if not duplicates:
        print("✅ Дубликатов не найдено.")
    else:
        print(f"⚠ Найдено {len(duplicates)} групп дубликатов:\n")
        for i, (h, paths) in enumerate(duplicates.items(), 1):
            print(f"  Группа {i}:")
            for p in paths:
                rel = os.path.relpath(p, DATA_DIR)
                size = os.path.getsize(p)
                print(f"    - {rel}  ({size} байт)")
            print()
        print("  Действие: удалите лишние вручную, оставив один файл из группы.")

    # === Итог ===
    print(f"\n{'=' * 60}")
    print("ГОТОВО!")
    print("=" * 60)
    if not DRY_RUN and report:
        print(f"\n📦 Резервная копия: {BACKUP_DIR}/")
        print("   Если что-то сломалось — удалите data/ и переименуйте")
        print("   data_backup/ обратно в data/.")
    if DRY_RUN:
        print("\n⚠ Сухой прогон завершён. Файлы НЕ были изменены.")
        print("   Запустите без --dry-run, чтобы применить изменения.")


if __name__ == "__main__":
    main()