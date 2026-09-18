# translate_drukhari.py
# Читает drukhari.txt, чистит мусор, переводит английские абзацы через GigaChat.
# Работает с уже скачанным файлом — не перекачивает.

import os
import re
import time
import shutil
from datetime import datetime

from gigachat import GigaChat
from gigachat.models import Chat, Messages, MessagesRole

# ============================================================
# НАСТРОЙКИ
# ============================================================
API_KEY = "MDFhMDk2NGMtZGQ0Yi03NGJiLTkzNWEtODgzMWEwNjZjZDYzOjBkNDViZDZmLTYxYzQtNGYyNC1hYzFlLTczZGY5OWI5MDZiMw=="
MODEL = "GigaChat-2-Pro"
TARGET = "data/chaos/drukhari.txt"
BACKUP_DIR = "data_backup"

MAX_CHUNK_CHARS = 1800   # маленькие куски — GigaChat не падает
SLEEP_BETWEEN = 1.5      # пауза между запросами


# ============================================================
# ЧИСТКА МУСОРА
# ============================================================
JUNK_PATTERNS = [
    r"нет данных\s*\n?",
    r"Нет данных\s*\n?",
    r"Данных нет\s*\n?",
    r"Генеративные языковые модели не обладают собственным мнением.*?ограничены\.\s*\n?",
    r"\(Note:.*?canon\.\)\s*\n?",
    r"\(Примечание:.*?не указаны.*?\)\s*\n?",
    r"\*Примечание редактора:.*?\n",
    r"\(Игровая адаптация.*?отсутствует.*?\)\s*\n?",
]


def clean_junk(text: str) -> str:
    for pat in JUNK_PATTERNS:
        text = re.sub(pat, "", text, flags=re.DOTALL | re.IGNORECASE)
    # Множественные пустые строки → двойной перенос
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Пустые заголовки
    text = re.sub(r"^#{1,4}\s*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"^={2,}\s*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# ============================================================
# ОПРЕДЕЛЕНИЕ ЯЗЫКА
# ============================================================
def is_english(text: str) -> bool:
    """
    Эвристика: доля латинских букв среди всех букв.
    Если больше 50% — считаем английским.
    """
    latin = sum(1 for c in text if 'a' <= c.lower() <= 'z')
    cyr = sum(1 for c in text if 'а' <= c.lower() <= 'я' or c.lower() == 'ё')
    total = latin + cyr
    if total < 10:  # слишком мало букв — не трогаем
        return False
    return latin / total > 0.5


# ============================================================
# ПЕРЕВОД ЧЕРЕЗ GIGACHAT
# ============================================================
_giga = None

def get_giga():
    global _giga
    if _giga is None:
        _giga = GigaChat(
            credentials=API_KEY,
            verify_ssl_certs=False,
            scope="GIGACHAT_API_PERS",
            model=MODEL,
        )
    return _giga


TRANSLATE_PROMPT = """Переведи следующий текст на русский язык.

ТРЕБОВАНИЯ:
- Сохрани структуру: заголовки, списки, переносы, markdown.
- Имена собственные (люди, планеты, корабли) и термины Warhammer 40,000 транслитерируй кириллицей:
  Drukhari → Друкхари, Dark Eldar → Тёмные Эльдары, Commorragh → Комморраг,
  Archon → Архонт, Kabal → Кабал, Succubus → Суккуб, Wych → Ведьма, Wyches → Ведьмы,
  Haemonculus → Гемункул, Incubi → Инкубы, Wracks → Враки, Mandrakes → Мандрагоры,
  Cegorach → Цегорах, Slaanesh → Слаанеш, Webway → Паутина, Voidraven → Войдрейвен,
  Razorwing → Рейзорвинг, Ravager → Раваджер, Talos → Талос, Cronos → Кронос,
  Grotesque → Гротеск, Scourge → Скаты, Hellion → Хеллион, Reaver → Ривер,
  Asdrubael Vect → Асдрубаэль Вект.
- НЕ добавляй от себя ничего. НЕ объясняй. НЕ пиши «вот перевод».
- Если в тексте уже русские слова — оставь их как есть.

ТЕКСТ:
{text}

ПЕРЕВОД:"""


def translate(text: str, label: str) -> str:
    giga = get_giga()

    # Режем на куски, чтобы не рвать по живому
    chunks = []
    current = ""
    for para in text.split("\n\n"):
        if len(current) + len(para) + 2 < MAX_CHUNK_CHARS:
            current = (current + "\n\n" + para).strip()
        else:
            if current:
                chunks.append(current)
            current = para
    if current:
        chunks.append(current)

    translated_parts = []
    for i, chunk in enumerate(chunks, 1):
        print(f"      чанк {i}/{len(chunks)} ({len(chunk)} симв.)...")
        prompt = TRANSLATE_PROMPT.replace("{text}", chunk)

        result = None
        for attempt in range(1, 4):  # 3 попытки
            try:
                resp = giga.chat(Chat(messages=[
                    Messages(role=MessagesRole.USER, content=prompt),
                ]))
                result = resp.choices[0].message.content.strip()
                if result:
                    break
            except Exception as e:
                print(f"         попытка {attempt} упала: {e}")
                time.sleep(3)

        if result:
            translated_parts.append(result)
        else:
            print(f"      ⚠ чанк {i} не перевёлся — оставляю как есть")
            translated_parts.append(chunk)

        time.sleep(SLEEP_BETWEEN)

    return "\n\n".join(translated_parts)


# ============================================================
# ГЛАВНОЕ
# ============================================================
def main():
    if not os.path.exists(TARGET):
        print(f"❌ Файл {TARGET} не найден.")
        return

    # Бэкап
    os.makedirs(BACKUP_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_path = os.path.join(BACKUP_DIR, f"drukhari_pre_translate_{ts}.txt")
    shutil.copy2(TARGET, backup_path)
    print(f"📦 Бэкап: {backup_path}")

    # Читаем
    with open(TARGET, encoding="utf-8") as f:
        text = f.read()
    original_len = len(text)
    print(f"📄 Исходный файл: {original_len} симв.")

    # Чистим мусор
    text = clean_junk(text)
    print(f"🧹 После чистки мусора: {len(text)} симв.")

    # Разбиваем на абзацы, английские отправляем в перевод
    paragraphs = text.split("\n\n")
    print(f"📑 Абзацев всего: {len(paragraphs)}")

    english_count = sum(1 for p in paragraphs if is_english(p) and len(p) > 50)
    print(f"🇬🇧 Английских абзацев для перевода: {english_count}")

    if english_count == 0:
        print("✅ Английского нет — сохраняю почищенный файл.")
        with open(TARGET, "w", encoding="utf-8") as f:
            f.write(text)
        return

    # Переводим блоками: собираем последовательные английские абзацы
    # в один блок, чтобы не терять контекст
    blocks = []       # (is_eng, [paragraphs])
    current_block = []
    current_is_eng = None

    for p in paragraphs:
        eng = is_english(p) and len(p) > 50
        if current_is_eng is None:
            current_is_eng = eng
            current_block = [p]
        elif eng == current_is_eng:
            current_block.append(p)
        else:
            blocks.append((current_is_eng, current_block))
            current_is_eng = eng
            current_block = [p]
    if current_block:
        blocks.append((current_is_eng, current_block))

    print(f"🔄 Блоков: {len(blocks)} (русские + английские)")

    result_parts = []
    processed = 0
    for i, (is_eng, paras) in enumerate(blocks, 1):
        block_text = "\n\n".join(paras)
        if is_eng:
            processed += 1
            print(f"\n🌐 [{i}/{len(blocks)}] Перевод блока ({len(block_text)} симв.):")
            translated = translate(block_text, f"block{i}")
            result_parts.append(translated)
        else:
            result_parts.append(block_text)

    new_text = "\n\n".join(result_parts)
    # Финальная уборка
    new_text = re.sub(r"\n{3,}", "\n\n", new_text)

    with open(TARGET, "w", encoding="utf-8") as f:
        f.write(new_text)

    print(f"\n✅ Готово: {TARGET}")
    print(f"   Было:  {original_len} симв.")
    print(f"   Стало: {len(new_text)} симв.")
    print(f"   Бэкап: {backup_path}")


if __name__ == "__main__":
    main()