import os
import sys
from datetime import datetime


# ============================================================
# НАСТРОЙКИ
# ============================================================
DATA_DIR = "data"
OUTPUT_FILE = "dump_all.txt"

# Папки, которые не нужно включать в дамп
SKIP_DIRS = {"_replacements", "_replacement", "_glossary", "__pycache__"}

# Режимы:
#   --full     — полный дамп (весь текст всех файлов)
#   --outline  — только оглавление (список файлов + размеры + строки)
#   --preview N — первые N символов каждого файла (по умолчанию 500)
if "--full" in sys.argv:
    MODE = "full"
elif "--outline" in sys.argv:
    MODE = "outline"
elif "--preview" in sys.argv:
    MODE = "preview"
    # Ищем число после --preview
    try:
        idx = sys.argv.index("--preview")
        PREVIEW_LEN = int(sys.argv[idx + 1])
    except (IndexError, ValueError):
        PREVIEW_LEN = 500
else:
    MODE = "outline"  # безопасный режим по умолчанию


# ============================================================
# ОБХОД ФАЙЛОВ
# ============================================================
def find_txt_files(root_dir):
    """Возвращает отсортированный список .txt файлов, кроме служебных."""
    result = []
    for root, dirs, files in os.walk(root_dir):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        for fname in sorted(files):
            if fname.endswith(".txt"):
                result.append(os.path.join(root, fname))
    return result


# ============================================================
# СТАТИСТИКА ПО ФАЙЛУ
# ============================================================
def file_stats(path):
    """Возвращает размер (байт), количество строк и символов."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception:
        return None
    return {
        "size": os.path.getsize(path),
        "lines": content.count("\n") + 1,
        "chars": len(content),
        "content": content,
    }


# ============================================================
# ФОРМИРОВАНИЕ ДАМПА
# ============================================================
def build_outline(files):
    """Только оглавление: список файлов с размерами и статистикой."""
    lines = []
    lines.append("=" * 70)
    lines.append("ОГЛАВЛЕНИЕ БАЗЫ ЗНАНИЙ")
    lines.append(f"Создано: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 70)
    lines.append("")

    by_folder = {}
    total_files = 0
    total_size = 0
    total_chars = 0

    for path in files:
        rel = os.path.relpath(path, DATA_DIR).replace("\\", "/")
        folder = os.path.dirname(rel) or "(корень)"

        stats = file_stats(path)
        if stats is None:
            continue

        by_folder.setdefault(folder, []).append({
            "name": os.path.basename(rel),
            "rel": rel,
            "size": stats["size"],
            "lines": stats["lines"],
            "chars": stats["chars"],
        })
        total_files += 1
        total_size += stats["size"]
        total_chars += stats["chars"]

    for folder in sorted(by_folder.keys()):
        lines.append(f"📁 {folder}/")
        for f in sorted(by_folder[folder], key=lambda x: x["name"]):
            lines.append(
                f"   - {f['name']:40s} "
                f"{f['chars']:>7} симв. | "
                f"{f['lines']:>5} строк | "
                f"{f['size']:>7} байт"
            )
        lines.append("")

    lines.append("=" * 70)
    lines.append(f"ИТОГО: {total_files} файлов")
    lines.append(f"       {total_chars} символов ({total_chars // 1000} тыс.)")
    lines.append(f"       {total_size} байт ({total_size // 1024} КБ)")
    lines.append("=" * 70)

    return "\n".join(lines)


def build_preview(files, preview_len=500):
    """Краткая выжимка: путь + первые N символов каждого файла."""
    lines = []
    lines.append("=" * 70)
    lines.append("ПРЕДПРОСМОТР БАЗЫ ЗНАНИЙ")
    lines.append(f"Создано: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"По {preview_len} символов от каждого файла")
    lines.append("=" * 70)
    lines.append("")

    for path in files:
        rel = os.path.relpath(path, DATA_DIR).replace("\\", "/")
        stats = file_stats(path)
        if stats is None:
            continue

        preview = stats["content"][:preview_len].strip()
        truncated = "..." if len(stats["content"]) > preview_len else ""

        lines.append("─" * 70)
        lines.append(f"ФАЙЛ: {rel}")
        lines.append(f"Размер: {stats['chars']} симв. / {stats['lines']} строк")
        lines.append("─" * 70)
        lines.append(preview + truncated)
        lines.append("")

    return "\n".join(lines)


def build_full(files):
    """Полный дамп: весь текст всех файлов, разделённых заголовками."""
    lines = []
    lines.append("=" * 70)
    lines.append("ПОЛНЫЙ ДАМП БАЗЫ ЗНАНИЙ")
    lines.append(f"Создано: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 70)
    lines.append("")

    for path in files:
        rel = os.path.relpath(path, DATA_DIR).replace("\\", "/")
        stats = file_stats(path)
        if stats is None:
            continue

        lines.append("")
        lines.append("#" * 70)
        lines.append(f"# ФАЙЛ: {rel}")
        lines.append(f"# Размер: {stats['chars']} симв. / {stats['lines']} строк")
        lines.append("#" * 70)
        lines.append("")
        lines.append(stats["content"])
        lines.append("")

    return "\n".join(lines)


# ============================================================
# ГЛАВНАЯ ФУНКЦИЯ
# ============================================================
def main():
    print("=" * 60)
    print("ВЫГРУЗКА БАЗЫ ЗНАНИЙ")
    print(f"Режим: {MODE}")
    print("=" * 60)

    if not os.path.exists(DATA_DIR):
        print(f"❌ Папка {DATA_DIR}/ не найдена.")
        return

    files = find_txt_files(DATA_DIR)
    print(f"\n📂 Найдено {len(files)} .txt файлов.")

    if not files:
        print("Нечего выгружать.")
        return

    # Выбираем режим
    if MODE == "full":
        print("\n⚠ Полный дамп может быть очень большим.")
        print("   Убедитесь, что у вас есть место на диске.")
        dump = build_full(files)
    elif MODE == "preview":
        print(f"\n🔍 Режим предпросмотра: по {PREVIEW_LEN} символов на файл.")
        dump = build_preview(files, PREVIEW_LEN)
    else:
        print("\n📋 Режим оглавления: список файлов со статистикой.")
        dump = build_outline(files)

    # Сохраняем
    try:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write(dump)
    except Exception as e:
        print(f"❌ Ошибка записи: {e}")
        return

    size_kb = os.path.getsize(OUTPUT_FILE) / 1024
    print(f"\n✅ Файл сохранён: {OUTPUT_FILE}")
    print(f"   Размер: {size_kb:.1f} КБ")
    print(f"   Строк: {dump.count(chr(10)) + 1}")
    print(f"   Символов: {len(dump)}")

    # Предупреждения
    if size_kb > 500 and MODE == "full":
        print(f"\n⚠ Файл очень большой. Возможно, стоит использовать")
        print(f"   --preview или --outline вместо --full.")
    if size_kb > 3000:
        print(f"\n⚠ Файл больше 3 МБ. Скорее всего, его нельзя будет")
        print(f"   целиком прочитать в чате. Разбейте на части.")


if __name__ == "__main__":
    main()