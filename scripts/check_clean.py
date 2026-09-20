import os
import re

# ============================================================
# ПРОВЕРКА ЧИСТОТЫ БАЗЫ ЗНАНИЙ
# ============================================================

DATA_DIR = "data"


def scan_files(words_should_not_exist, words_should_exist, specific_checks=None):
    skip_dirs = {"_replacements", "_replacement", "_glossary", "__pycache__"}

    all_files = []
    for root, dirs, files in os.walk(DATA_DIR):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        for f in files:
            if f.endswith(".txt"):
                all_files.append(os.path.join(root, f))

    print(f"📂 Проверяю {len(all_files)} файлов\n")

    # === 1. Слова, которых НЕ должно быть (с границами слова) ===
    print("=" * 60)
    print("1. СЛОВА, КОТОРЫХ НЕ ДОЛЖНО БЫТЬ")
    print("=" * 60)
    for word in words_should_not_exist:
        found_in = []
        # \b — граница слова, чтобы "Костопев" не находилось в "Костопевец"
        pattern = re.compile(r"\b" + re.escape(word) + r"\b", re.IGNORECASE)

        for path in all_files:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
            except Exception:
                continue
            matches = pattern.findall(content)
            if matches:
                rel = os.path.relpath(path, DATA_DIR)
                found_in.append(f"{rel} ×{len(matches)}")

        if not found_in:
            print(f"  ✅ '{word}' — не найдено (OK)")
        else:
            print(f"  ❌ '{word}' — НАЙДЕНО:")
            for item in found_in:
                print(f"      {item}")

    # === 2. Слова, которые ДОЛЖНЫ быть ===
    print(f"\n{'=' * 60}")
    print("2. СЛОВА, КОТОРЫЕ ДОЛЖНЫ ПРИСУТСТВОВАТЬ")
    print("=" * 60)
    for word in words_should_exist:
        total = 0
        for path in all_files:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
            except Exception:
                continue
            total += content.lower().count(word.lower())

        if total > 0:
            print(f"  ✅ '{word}' — найдено ×{total} (OK)")
        else:
            print(f"  ❌ '{word}' — НЕ найдено (проблема!)")

    # === 3. Специальные проверки по файлам ===
    if specific_checks:
        print(f"\n{'=' * 60}")
        print("3. СПЕЦИАЛЬНЫЕ ПРОВЕРКИ")
        print("=" * 60)
        for rel_path, word, expectation in specific_checks:
            full_path = os.path.join(DATA_DIR, rel_path)
            if not os.path.exists(full_path):
                print(f"  ❌ Файл не найден: {rel_path}")
                continue

            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    content = f.read()
            except Exception as e:
                print(f"  ⚠ Ошибка чтения {rel_path}: {e}")
                continue

            count = content.lower().count(word.lower())

            if expectation == "must_exist" and count > 0:
                print(f"  ✅ {rel_path}: '{word}' ×{count} (OK — должно быть)")
            elif expectation == "must_not_exist" and count == 0:
                print(f"  ✅ {rel_path}: '{word}' не найдено (OK — не должно быть)")
            elif expectation == "must_exist" and count == 0:
                print(f"  ❌ {rel_path}: '{word}' НЕ найдено (должно быть!)")
            elif expectation == "must_not_exist" and count > 0:
                print(f"  ❌ {rel_path}: '{word}' НАЙДЕНО ×{count} (не должно быть!)")


def main():
    print("=" * 60)
    print("ПРОВЕРКА ЧИСТОТЫ БАЗЫ ЗНАНИЙ")
    print("=" * 60)
    print()

    # Слова, которых не должно остаться (опечатки/выдумки)
    words_should_not_exist = [
        "Шурикен",
        "Костопев",
        "Фарсир",
        "Иннарис",
        "варпоман",
        "храм-психоз",
        "Термагант",
        "Хормагаунт",
        "Азуриан",
        "Адептус Арбитес",
        "Тёмные Механикум",
        "Хаос-спейсмарины",
        "Цегоррах",
        "Иянна",
        "Инари",
        "Т'ау",
        "Мон'кау",
        "Ктан",
        "Ваагх",
    ]

    # Слова, которые должны появиться после чистки
    words_should_exist = [
        "Сюрикен",
        "Костопевец",
        "Провидец",
        "Термигант",
        "Асуриан",
        "Адептус Арбитрес",
        "Тёмный Механикум",
        "Космодесантники Хаоса",
        "Цегорах",
        "Иврайна",
        "Иннари",
        "Тау",
        "Монт'ау",
        "К'тан",
        "Вааагх!",
    ]

    # Специальные проверки по конкретным файлам
    specific_checks = [
        # Магос Кейн должен остаться в этих двух файлах
        ("chaos/dark_mechanicum.txt", "Кейн", "must_exist"),
        ("imperium/mechanicus.txt", "Кейн", "must_exist"),
    ]

    scan_files(words_should_not_exist, words_should_exist, specific_checks)

    print(f"\n{'=' * 60}")
    print("ПРОВЕРКА ЗАВЕРШЕНА")
    print("=" * 60)


if __name__ == "__main__":
    main()