# test_master.py
# Автотест Мастера на галлюцинации.
# Идея: собирает словарь всех слов из базы → ищет в ответах Мастера
# термины с большой буквы, которых в базе НЕТ.

import os
import re
import json
import time
import argparse
from datetime import datetime

import streamlit as st

from gigachat import GigaChat
from gigachat.models import Chat, Messages, MessagesRole

from knowledge import KnowledgeBase


# ============================================================
# НАСТРОЙКИ
# ============================================================
try:
    API_KEY = st.secrets["GIGACHAT_API_KEY"]
except Exception:
    API_KEY = "MDFhMDk2NGMtZGQ0Yi03NGJiLTkzNWEtODgzMWEwNjZjZDYzOjBkNDViZDZmLTYxYzQtNGYyNC1hYzFlLTczZGY5OWI5MDZiMw=="

MODEL = "GigaChat-2-Pro"
MASTER_PROMPT_PATH = "prompts/master.txt"
QUESTIONS_PATH = "tests/questions.txt"
RESULTS_DIR = "tests"

MIN_WORD_LEN = 5
MAX_SUSPECTS = 5

# Слова, которые не считаем терминами даже если их нет в базе.
# Латиница фильтруется отдельно (_is_latin_only), сюда её писать не надо.
IGNORE_WORDS = {
    # русские общие
    "важнейшие", "являясь", "данный", "данная", "данное", "данные",
    "который", "которая", "которое", "которые", "которых",
    "некоторые", "некоторых", "определённый", "определённые",
    "различные", "различных", "большой", "большая", "большое",
    "маленький", "новая", "новое", "новые", "новых", "старый",
    "главный", "главная", "важный", "важная", "разный", "разные",
    "способный", "способен", "способна", "возможен", "возможна",
    "наиболее", "менее", "более", "очень", "почти", "именно",
    "является", "становится", "становятся", "используется",
    "используются", "применяется", "применяются", "называется",
    "называют", "называются", "существует", "существуют",
    "появляется", "появляются", "включает", "включают",
    # прилагательные-связки
    "основной", "основная", "основное", "основные",
    "дополнительный", "дополнительные", "ключевой", "ключевые",
    "типичный", "типичная", "типичное", "типичные",
    "стандартный", "стандартная", "стандартное", "стандартные",
    # каноничные термины, у которых стеммер не всегда сведёт форму
    "духовец", "духовцы", "духовцев", "духовцам", "духовцами",
    "страж", "стражи", "стражей", "стражам", "стражами",
    "владыка", "владыки", "владык", "владыкам", "владыками",
    "грот", "гроты", "гротов", "гротам",
    "сквиг", "сквиги", "сквигов", "сквигам",
    "кровопийца", "кровопийцы", "кровопийц", "кровопийцам",
    "инквизитор", "инквизиторы", "инквизиторов", "инквизиторам",
    "пуританин", "пуритане", "пуритан", "пуританам",
    "радикал", "радикалы", "радикалов", "радикалам",
    # орки: кланы и специализации
    "мекбой", "мекбои", "мекбоев", "мекбойз", "мекбойями",
    # друкхари: каноничные классы
    "архонт", "архонты", "архонтов",
    "суккуб", "суккубы", "суккубов",
    "гемункул", "гемункулы", "гемункулов",
    "инкуб", "инкубы", "инкубов",
    "кабалит", "кабалиты", "кабалитов",
    # канон: Ведьма / Ведьмы (Wych / Wyches)
    "ведьма", "ведьмы", "ведьм", "ведьмам", "ведьмами",
    # неканоничные варианты (Вичи, Вийки) — не должны триггерить тест,
    # правятся в replacements.txt
    "вич", "вичи", "вичей", "вичам", "вичами",
    "вийка", "вийки", "виек",
    # тау: имя Фарсайта (Kais, Mont'yr, Shova)
    "кайус", "кайса", "кайсу",
    "монт'йр", "монт'йор", "монт'йра",
    "шова", "шовы", "шове",
    # механикус
    "бог-машина", "бога-машины", "богу-машине", "богом-машиной",
    "боги-машины", "богов-машин",
    # корабли эльдар
    "тортур", "тортура", "тортуру", "тортурам", "тортурами",
    "тортуре", "тортуров",
    # Кхорн — каноничный бог, стеммер не свёл форму
    "кхорн", "кхорна", "кхорну", "кхорном", "кхорне",
    # Лорды Хаоса — каноничный термин
    "лорд", "лорды", "лордов", "лордам", "лордами",
}


# ============================================================
# ЗАГРУЗКА
# ============================================================
def load_questions(path):
    if not os.path.exists(path):
        print(f"❌ Файл {path} не найден.")
        return []
    questions = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            questions.append(line)
    return questions


def load_master_prompt(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


# ============================================================
# СЛОВА И СТЕММЕР
# ============================================================
# Регулярка для слова: первая буква — любая (заглавная/строчная, рус/лат),
# далее — буквы, дефисы, апострофы. Заглавные внутри слова разрешены
# (Стражей-Призраков, Шас'О).
_WORD_RE = re.compile(
    r"[А-ЯЁA-Zа-яёa-z][А-ЯЁA-Zа-яёa-z\-']*",
    re.UNICODE,
)

# ВАЖНО: длинные окончания идут ПЕРВЫМИ, иначе короткие съедят лишнее.
_STEM_RE = re.compile(
    r"(ами|ями|ого|ому|ыми|ими|"
    r"ов|ев|ах|ях|ам|ям|ой|ей|ые|ых|ое|ая|ий|ый|ом|ем|"
    r"а|я|ы|и|у|ю|е|о)$"
)


def _is_latin_only(word: str) -> bool:
    """True, если в слове НЕТ ни одной кириллической буквы."""
    for c in word:
        if 'А' <= c <= 'я' or c in 'Ёё':
            return False
    return True


def stem(word: str) -> str:
    """
    Простой стеммер — убирает частые русские окончания.
    Для слов с дефисом стеммит последнюю часть:
      Стражей-Призраков → стражей-призрак
    """
    w = word.lower()
    if '-' in w:
        head, _, tail = w.rpartition('-')
        return f"{head}-{stem(tail)}"
    s = _STEM_RE.sub("", w)
    return s if len(s) >= 4 else w


# ============================================================
# СБОР СЛОВАРЯ ИЗ БАЗЫ
# ============================================================
def build_vocabulary(data_dir="data"):
    """Собирает множество стемов всех слов из базы."""
    vocab = set()
    for root, dirs, files in os.walk(data_dir):
        dirs[:] = [d for d in dirs if not d.startswith("_") and d != "__pycache__"]
        for fname in files:
            if not fname.endswith(".txt"):
                continue
            path = os.path.join(root, fname)
            try:
                with open(path, encoding="utf-8") as f:
                    text = f.read()
            except Exception:
                continue
            for word in _WORD_RE.findall(text):
                if len(word) >= MIN_WORD_LEN:
                    vocab.add(stem(word))
    return vocab


# ============================================================
# ПОИСК ПОДОЗРИТЕЛЬНЫХ
# ============================================================
def extract_candidates(text):
    """
    Извлекает слова с большой буквы длиной >= MIN_WORD_LEN,
    исключая первые слова предложений и латиницу.
    """
    candidates = []
    seen = set()

    sentences = re.split(r"[.!?]\s+", text)

    for sent in sentences:
        words = _WORD_RE.findall(sent)
        for i, w in enumerate(words):
            if i == 0 and sent.strip().startswith(w):
                continue
            if len(w) < MIN_WORD_LEN:
                continue
            if not w[0].isupper():
                continue
            if _is_latin_only(w):
                continue
            if w.lower() in IGNORE_WORDS:
                continue
            if w in seen:
                continue
            seen.add(w)
            candidates.append(w)

    return candidates


def find_suspects(text, vocab):
    """Возвращает список подозрительных слов (которых нет в словаре базы)."""
    candidates = extract_candidates(text)
    suspects = []
    for w in candidates:
        if stem(w) not in vocab:
            suspects.append(w)
        if len(suspects) >= MAX_SUSPECTS:
            break
    return suspects


# ============================================================
# ЗАПРОС К МАСТЕРУ
# ============================================================
def ask_master(giga, master_prompt, kb, question):
    context = kb.format_context(question, top_k=5)
    enriched = (
        f"{context}\n\n=== ВОПРОС ИГРОКА ===\n{question}\n\n"
        f"Ответь прямо, как Мастер, без сцены с NPC. "
        f"Используй только информацию из справки выше."
    )
    messages = [
        Messages(role=MessagesRole.SYSTEM, content=master_prompt),
        Messages(role=MessagesRole.USER, content=enriched),
    ]
    try:
        resp = giga.chat(Chat(messages=messages))
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"ОШИБКА: {e}"


# ============================================================
# ГЛАВНАЯ ЛОГИКА
# ============================================================
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    questions = load_questions(QUESTIONS_PATH)
    if not questions:
        return
    if args.limit > 0:
        questions = questions[:args.limit]

    print("=" * 70)
    print("АВТОТЕСТ МАСТЕРА")
    print(f"Вопросов: {len(questions)}")
    print("=" * 70)

    print("\n📚 Собираю словарь из базы...")
    vocab = build_vocabulary("data")
    print(f"   Уникальных стемов: {len(vocab)}")

    print("\n📚 Загружаю базу знаний...")
    kb = KnowledgeBase()
    print(f"   Чанков: {kb.chunk_count}")

    print("\n📖 Загружаю промт Мастера...")
    master_prompt = load_master_prompt(MASTER_PROMPT_PATH)

    print("\n🤖 Подключаюсь к GigaChat...")
    giga = GigaChat(
        credentials=API_KEY,
        verify_ssl_certs=False,
        scope="GIGACHAT_API_PERS",
        model=MODEL,
    )

    os.makedirs(RESULTS_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    results = []
    suspicious = []

    for i, q in enumerate(questions, 1):
        print(f"\n[{i}/{len(questions)}] {q}")
        answer = ask_master(giga, master_prompt, kb, q)
        print(f"   Ответ: {len(answer)} симв.")

        if args.verbose:
            print(f"   ---\n{answer}\n   ---")

        suspects = find_suspects(answer, vocab)
        if suspects:
            print(f"   ⚠ Подозрительные: {', '.join(suspects)}")

        results.append({
            "question": q,
            "answer": answer,
            "suspects": suspects,
        })
        if suspects:
            suspicious.append(results[-1])

        time.sleep(0.5)

    json_path = os.path.join(RESULTS_DIR, f"results_{ts}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": ts,
            "model": MODEL,
            "chunks_in_db": kb.chunk_count,
            "vocabulary_size": len(vocab),
            "total_questions": len(questions),
            "suspicious_count": len(suspicious),
            "results": results,
        }, f, ensure_ascii=False, indent=2)

    report_path = os.path.join(RESULTS_DIR, f"report_{ts}.txt")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("=" * 70 + "\n")
        f.write("ОТЧЁТ О ПРОВЕРКЕ МАСТЕРА\n")
        f.write(f"Создан: {ts}\n")
        f.write(f"Всего вопросов: {len(questions)}\n")
        f.write(f"С подозрительными: {len(suspicious)}\n")
        f.write("=" * 70 + "\n\n")

        if not suspicious:
            f.write("✅ Подозрительных терминов не найдено.\n")
        else:
            for i, item in enumerate(suspicious, 1):
                f.write(f"\n{'=' * 70}\n")
                f.write(f"[{i}] ВОПРОС: {item['question']}\n")
                f.write(f"{'=' * 70}\n")
                f.write("⚠ Подозрительные:\n")
                for t in item['suspects']:
                    f.write(f"   - {t}\n")
                f.write(f"\nОтвет:\n{item['answer']}\n")

    print("\n" + "=" * 70)
    print("ГОТОВО")
    print("=" * 70)
    print(f"📁 Все ответы: {json_path}")
    print(f"📁 Отчёт:      {report_path}")
    print(f"\nВсего:              {len(questions)}")
    print(f"С подозрительными:  {len(suspicious)}")


if __name__ == "__main__":
    main()