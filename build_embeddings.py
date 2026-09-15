# build_embeddings.py
# Собирает векторную базу из data/ в ChromaDB.
# Использует GPU (CUDA) если доступен, иначе CPU.
# Модель: intfloat/multilingual-e5-small.
#
# Особенности:
# - Стабильные ID чанков = md5(источник + текст).
# - Автоочистка старого формата ID (chunk_N).
# - Дедупликация одинаковых чанков.
# - GPU: batch 256, ~50x быстрее CPU.

import sys
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

import os
import time
import hashlib
import torch
import chromadb
from sentence_transformers import SentenceTransformer


# ============================================================
# ОПРЕДЕЛЕНИЕ УСТРОЙСТВА
# ============================================================
if torch.cuda.is_available():
    DEVICE = "cuda"
    GPU_NAME = torch.cuda.get_device_name(0)
    VRAM_GB = torch.cuda.get_device_properties(0).total_memory / (1024 ** 3)
    BATCH = 256
    # Для GPU потоки CPU не важны
    _NUM_THREADS = 4
else:
    DEVICE = "cpu"
    GPU_NAME = None
    VRAM_GB = 0
    BATCH = 64
    _NUM_THREADS = min(8, os.cpu_count() or 4)

torch.set_num_threads(_NUM_THREADS)


# ============================================================
# НАСТРОЙКИ
# ============================================================
MODEL_NAME = "intfloat/multilingual-e5-small"

DATA_DIR = "data"
CHROMA_DIR = "./chroma_db"
COLLECTION_NAME = "knowledge"

MIN_CHUNK_LEN = 80
MAX_CHUNK_LEN = 2000

FACTION_MAP = {
    "eldar": "eldar",
    "imperium": "imperium",
    "chaos": "chaos",
    "orks": "orks",
    "tau": "tau",
    "necrons": "necrons",
    "tyranids": "tyranids",
    "general": "general",
    "glossary": "general",
    "imported": "general",
}


# ============================================================
# СБОР ЧАНКОВ
# ============================================================
def collect_chunks():
    chunks = []
    if not os.path.exists(DATA_DIR):
        print(f"❌ Папка {DATA_DIR}/ не найдена.")
        return chunks

    for root, dirs, files in os.walk(DATA_DIR):
        dirs[:] = sorted(d for d in dirs if not d.startswith("_") and d != "__pycache__")
        for fname in sorted(files):
            if not fname.endswith(".txt"):
                continue
            path = os.path.join(root, fname)
            rel = os.path.relpath(path, DATA_DIR).replace("\\", "/")
            folder = rel.split("/")[0]
            faction = FACTION_MAP.get(folder, "general")

            try:
                with open(path, encoding="utf-8") as f:
                    text = f.read()
            except Exception as e:
                print(f"⚠ Не удалось прочитать {rel}: {e}")
                continue

            paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

            buffer = ""
            for p in paragraphs:
                if len(buffer) + len(p) + 2 < MIN_CHUNK_LEN:
                    buffer = (buffer + "\n\n" + p).strip()
                    continue

                if buffer:
                    chunks.append({"text": buffer, "source": rel, "faction": faction})
                    buffer = ""

                if len(p) <= MAX_CHUNK_LEN:
                    chunks.append({"text": p, "source": rel, "faction": faction})
                else:
                    for i in range(0, len(p), MAX_CHUNK_LEN):
                        piece = p[i:i + MAX_CHUNK_LEN].strip()
                        if len(piece) >= MIN_CHUNK_LEN:
                            chunks.append({"text": piece, "source": rel, "faction": faction})

            if buffer and len(buffer) >= MIN_CHUNK_LEN:
                chunks.append({"text": buffer, "source": rel, "faction": faction})

    return chunks


# ============================================================
# ГЛАВНАЯ ЛОГИКА
# ============================================================
def main():
    print("=" * 60)
    print("СБОРКА ВЕКТОРНОЙ БАЗЫ ЗНАНИЙ")
    print(f"Модель: {MODEL_NAME}")
    if DEVICE == "cuda":
        print(f"🎮 Устройство: GPU ({GPU_NAME}, {VRAM_GB:.1f} ГБ VRAM)")
    else:
        print(f"💻 Устройство: CPU ({_NUM_THREADS} потоков)")
    print(f"Размер батча: {BATCH}")
    print("=" * 60)

    client = chromadb.PersistentClient(path=CHROMA_DIR)

    try:
        collection = client.get_collection(name=COLLECTION_NAME)
    except Exception:
        collection = client.create_collection(name=COLLECTION_NAME)

    existing_ids = set()
    if collection.count() > 0:
        try:
            existing_ids = set(collection.get()["ids"])
        except Exception:
            pass

    # Автоочистка старого формата ID
    old_format_found = any(str(i).startswith("chunk_") for i in existing_ids)
    if old_format_found:
        print(f"\n⚠ Обнаружены СТАРЫЕ ID (формат chunk_N): {len(existing_ids)} чанков.")
        print("  Очищаем коллекцию для пересборки с новыми стабильными ID...\n")
        try:
            client.delete_collection(COLLECTION_NAME)
        except Exception as e:
            print(f"❌ Не удалось удалить коллекцию: {e}")
            return
        collection = client.create_collection(name=COLLECTION_NAME)
        existing_ids = set()

    print(f"Уже в базе: {len(existing_ids)} чанков")

    print("\nСобираем чанки из data/ ...")
    chunks = collect_chunks()
    print(f"Всего чанков найдено: {len(chunks)}")

    # Генерация ID и дедупликация
    new_chunks = []
    seen_new_ids = set()
    duplicate_count = 0
    for c in chunks:
        key = (c["source"] + "||" + c["text"]).encode("utf-8")
        cid = hashlib.md5(key).hexdigest()
        c["id"] = cid

        if cid in existing_ids:
            continue
        if cid in seen_new_ids:
            duplicate_count += 1
            continue
        seen_new_ids.add(cid)
        new_chunks.append(c)

    if duplicate_count > 0:
        print(f"  (пропущено дубликатов внутри партии: {duplicate_count})")

    print(f"Новых для обработки: {len(new_chunks)}")

    if not new_chunks:
        print("\n✅ Всё уже обработано. Выходим.")
        return

    print(f"\nЗагружаем модель {MODEL_NAME} на {DEVICE} ...")
    model = SentenceTransformer(MODEL_NAME, device=DEVICE)
    print("✅ Модель загружена.")

    print(f"\nСчитаем эмбеддинги (batch={BATCH}, device={DEVICE}) ...")
    processed = 0
    start_time = time.time()

    for i in range(0, len(new_chunks), BATCH):
        batch = new_chunks[i:i + BATCH]
        texts = [c["text"] for c in batch]

        embeddings = model.encode(
            texts,
            batch_size=BATCH,
            normalize_embeddings=True,
            show_progress_bar=False,
            convert_to_numpy=True,
        ).tolist()

        try:
            collection.add(
                documents=texts,
                embeddings=embeddings,
                metadatas=[{"source": c["source"], "faction": c["faction"]} for c in batch],
                ids=[c["id"] for c in batch],
            )
        except Exception as e:
            print(f"\n❌ Ошибка на батче {i}: {e}")
            print("Продолжаем со следующего батча...")
            continue

        processed += len(batch)

        elapsed = time.time() - start_time
        speed = processed / elapsed if elapsed > 0 else 0
        eta = (len(new_chunks) - processed) / speed if speed > 0 else 0

        print(f"  [{processed}/{len(new_chunks)}]  "
              f"{speed:.1f} чанк/сек  ETA: {eta:.0f} сек")

    print("\n" + "=" * 60)
    print(f"Обработано: {processed}")
    print(f"Всего в базе теперь: {collection.count()} чанков")
    print(f"Время: {time.time() - start_time:.1f} сек")
    print(f"Папка базы: {os.path.abspath(CHROMA_DIR)}")
    print("=" * 60)


if __name__ == "__main__":
    main()