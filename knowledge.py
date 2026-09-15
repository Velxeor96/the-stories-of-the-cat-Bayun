# knowledge.py
# RAG-поиск через локальные эмбеддинги intfloat/multilingual-e5-small + ChromaDB.
# Использует GPU (CUDA) если доступен, иначе CPU.
# Если база не построена — автоматически падает на word-overlap fallback.

import os
import torch
import chromadb
from sentence_transformers import SentenceTransformer


# ============================================================
# УСТРОЙСТВО
# ============================================================
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


# ============================================================
# НАСТРОЙКИ
# ============================================================
MODEL_NAME = "intfloat/multilingual-e5-small"

CHROMA_DIR = "./chroma_db"
COLLECTION_NAME = "knowledge"

FACTION_KEYWORDS = {
    "eldar": [
        "эльдар", "аэльдари", "асуриани", "друкхари", "арлекин", "экзодит",
        "иннари", "крафтворлд", "сюрикен", "провидец", "костопевец", "баньши",
        "скорпион", "аспект", "кхейн", "цегорах", "слаанеш",
    ],
    "imperium": [
        "империум", "космодесантник", "астартес", "гвардия", "инквизиц",
        "механикус", "сороритас", "экклезиарх", "комиссар", "терра",
        "император", "болтер", "лазган", "адептус",
    ],
    "chaos": [
        "хаос", "кхорн", "тзинч", "нургл", "слаанеш", "космодесант хаоса",
        "демон", "варп", "ересь хоруса", "абаддон", "несущие слово",
        "тысяча сынов", "гвардия смерти", "пожиратели миров",
    ],
    "orks": [
        "орк", "орки", "ваагх", "гофф", "смертельный череп", "гретчин",
        "мекбой", "чоппа", "шута", "слагга", "свободный орк", "клан",
        "змеиные клыки", "багровые клыки", "кровавые топоры", "злые солнца",
    ],
    "tau": [
        "тау", "каста огня", "каста воды", "каста земли", "каста воздуха",
        "эфирн", "крут", "веспид", "импульсн", "боевой костюм", "септ",
        "фарсайт", "воин огня",
    ],
    "necrons": [
        "некрон", "некронтир", "гробниц", "династи", "к'тан", "гаусс",
        "проклят", "сарек", "молчаливый", "имотех", "тразин", "некродермис",
    ],
    "tyranids": [
        "тиранид", "генокрад", "флот-улей", "сверхразум", "биоморф",
        "термигант", "хормагант", "карнифекс", "ликтор", "воин улья",
        "тень в варпе",
    ],
}


QUERY_TO_FILE_HINTS = [
    (["клан", "кланы", "кланов", "клан "], ["clans", "klan"]),
    (["каста", "касты", "каст "], ["castes"]),
    (["путь", "пути", "путей"], ["paths"]),
    (["оружие", "оружия", "вооружен"], ["equipment", "weapons"]),
    (["броня", "брони", "броню", "доспех"], ["armor", "equipment"]),
    (["снаряжение", "инвентарь"], ["equipment"]),
    (["термин", "термины", "словарь", "глоссарий"], ["terminology", "glossary"]),
    (["флот", "флоты", "корабл", "судн"], ["hive_fleets", "space_fleet", "spacecraft"]),
    (["династи", "династия"], ["dynasties"]),
    (["демон"], ["daemons"]),
    (["легион"], ["chaos_legions", "space_marines"]),
]


def _query_file_hints(query_lower: str) -> list:
    hints = []
    for triggers, filenames in QUERY_TO_FILE_HINTS:
        for t in triggers:
            if t in query_lower:
                hints.extend(filenames)
                break
    return hints


class _ChunkCount:
    def __init__(self, n):
        self._n = n

    def __len__(self):
        return self._n


class KnowledgeBase:
    def __init__(self):
        self._ready = False
        self._collection = None
        self._model = None
        self._fallback_chunks = []

        try:
            client = chromadb.PersistentClient(path=CHROMA_DIR)
            self._collection = client.get_collection(name=COLLECTION_NAME)
            if self._collection.count() > 0:
                self._ready = True
        except Exception:
            self._ready = False

        if self._ready:
            self._model = SentenceTransformer(MODEL_NAME, device=DEVICE)
        else:
            self._fallback_chunks = self._load_fallback_chunks()

    @property
    def chunk_count(self):
        if self._ready and self._collection is not None:
            return self._collection.count()
        return len(self._fallback_chunks)

    @property
    def is_vector_mode(self):
        return self._ready

    @property
    def chunks(self):
        if self._ready and self._collection is not None:
            return _ChunkCount(self._collection.count())
        return self._fallback_chunks

    def _detect_factions(self, query):
        q = query.lower()
        found = set()
        for faction, kws in FACTION_KEYWORDS.items():
            for kw in kws:
                if kw in q:
                    found.add(faction)
                    break
        return found

    def search(self, query, top_k=4):
        if self._ready:
            return self._search_vector(query, top_k)
        return self._search_fallback(query, top_k)

    def _search_vector(self, query, top_k=4):
        query_lower = query.lower()
        query_factions = self._detect_factions(query)
        file_hints = _query_file_hints(query_lower)

        priority_chunks = []
        if file_hints:
            try:
                all_data = self._collection.get(include=["documents", "metadatas"])
                for doc, meta in zip(all_data["documents"], all_data["metadatas"]):
                    source = (meta.get("source", "") or "").lower()
                    faction = meta.get("faction", "general")
                    source_match = any(h in source for h in file_hints)
                    faction_ok = (not query_factions) or (faction in query_factions)
                    if source_match and faction_ok:
                        priority_chunks.append({
                            "text": doc,
                            "source": meta.get("source", ""),
                            "faction": faction,
                        })
            except Exception:
                pass

        try:
            query_emb = self._model.encode(
                [query], normalize_embeddings=True, device=DEVICE
            ).tolist()
            n_fetch = min(top_k * 8, max(self._collection.count(), top_k))
            res = self._collection.query(
                query_embeddings=query_emb,
                n_results=n_fetch,
            )
            docs = res.get("documents", [[]])[0]
            metas = res.get("metadatas", [[]])[0]
        except Exception:
            return (priority_chunks[:top_k] if priority_chunks
                    else self._search_fallback(query, top_k))

        top_priority, mid_priority, low_priority = [], [], []

        for doc, meta in zip(docs, metas):
            item = {
                "text": doc,
                "source": meta.get("source", ""),
                "faction": meta.get("faction", "general"),
            }
            source_lower = item["source"].lower()
            faction_match = bool(query_factions) and item["faction"] in query_factions
            source_match = bool(file_hints) and any(h in source_lower for h in file_hints)

            if faction_match and source_match:
                top_priority.append(item)
            elif faction_match or source_match:
                mid_priority.append(item)
            else:
                low_priority.append(item)

        combined = priority_chunks + top_priority + mid_priority + low_priority

        result = []
        seen_texts = set()
        for c in combined:
            key = c["text"][:100]
            if key in seen_texts:
                continue
            seen_texts.add(key)
            result.append(c)
            if len(result) >= top_k:
                break

        return result

    def _search_fallback(self, query, top_k=4):
        if not self._fallback_chunks:
            return []

        q_words = set(
            w.lower().strip(".,!?;:()[]\"'")
            for w in query.split() if len(w) > 2
        )
        if not q_words:
            return []

        query_factions = self._detect_factions(query)
        file_hints = _query_file_hints(query.lower())

        scored = []
        for chunk in self._fallback_chunks:
            text_words = set(
                w.lower().strip(".,!?;:()[]\"'")
                for w in chunk["text"].split()
            )
            overlap = len(q_words & text_words)
            if overlap < 3:
                continue
            score = overlap
            if query_factions and chunk["faction"] in query_factions:
                score *= 2
            if file_hints and any(h in chunk["source"].lower() for h in file_hints):
                score *= 3
            scored.append((score, chunk))

        scored.sort(key=lambda x: -x[0])
        return [c for _, c in scored[:top_k]]

    def format_context(self, query, top_k=4):
        chunks = self.search(query, top_k=top_k)
        if not chunks:
            return ""
        lines = ["=== СПРАВКА ИЗ БАЗЫ ЗНАНИЙ ==="]
        for c in chunks:
            lines.append(f"\n[{c['source']}]\n{c['text']}")
        lines.append("\n=== КОНЕЦ СПРАВКИ ===")
        return "\n".join(lines)

    def _load_fallback_chunks(self):
        chunks = []
        data_dir = "data"
        if not os.path.exists(data_dir):
            return chunks

        faction_map = {
            "eldar": "eldar", "imperium": "imperium", "chaos": "chaos",
            "orks": "orks", "tau": "tau", "necrons": "necrons",
            "tyranids": "tyranids", "general": "general",
            "glossary": "general", "imported": "general",
        }

        for root, dirs, files in os.walk(data_dir):
            dirs[:] = [d for d in dirs if not d.startswith("_") and d != "__pycache__"]
            for fname in files:
                if not fname.endswith(".txt"):
                    continue
                path = os.path.join(root, fname)
                rel = os.path.relpath(path, data_dir).replace("\\", "/")
                folder = rel.split("/")[0]
                faction = faction_map.get(folder, "general")
                try:
                    with open(path, encoding="utf-8") as f:
                        text = f.read()
                except Exception:
                    continue
                for para in text.split("\n\n"):
                    para = para.strip()
                    if len(para) < 80:
                        continue
                    chunks.append({"text": para, "source": rel, "faction": faction})
        return chunks