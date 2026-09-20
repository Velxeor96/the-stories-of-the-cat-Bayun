"""services/rag.py — RAG-поиск по базе знаний WH40K.

Два режима:
  1. Векторный (ChromaDB + sentence-transformers) — если chroma_db/ собрана.
  2. Fallback (word-overlap по data/**/*.txt) — если база недоступна.

torch и sentence-transformers импортируются ЛЕНИВО (важно для Streamlit Cloud).
"""
from __future__ import annotations

import os
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]

MODEL_NAME = "intfloat/multilingual-e5-small"
CHROMA_DIR = str(_ROOT / "chroma_db")
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


def _query_file_hints(query_lower: str) -> list[str]:
    hints: list[str] = []
    for triggers, filenames in QUERY_TO_FILE_HINTS:
        for t in triggers:
            if t in query_lower:
                hints.extend(filenames)
                break
    return hints


def _load_fallback_chunks() -> list[dict]:
    """Читает data/**/*.txt и режет на чанки по ~600 символов."""
    chunks: list[dict] = []
    data_dir = _ROOT / "data"
    if not data_dir.is_dir():
        return chunks

    for faction_dir in sorted(data_dir.iterdir()):
        if not faction_dir.is_dir():
            continue
        faction = faction_dir.name
        if faction in ("users", "accounts", "_replacements"):
            continue
        for txt in faction_dir.glob("*.txt"):
            try:
                text = txt.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            source = txt.name
            buf = ""
            for para in text.split("\n\n"):
                para = para.strip()
                if not para:
                    continue
                if len(buf) + len(para) > 600 and buf:
                    chunks.append({"text": buf.strip(), "source": source, "faction": faction})
                    buf = para
                else:
                    buf = (buf + "\n\n" + para).strip() if buf else para
            if buf:
                chunks.append({"text": buf.strip(), "source": source, "faction": faction})
    return chunks


class _ChunkCount:
    def __init__(self, n: int):
        self._n = n

    def __len__(self) -> int:
        return self._n


class KnowledgeBase:
    def __init__(self) -> None:
        self._ready = False
        self._collection = None
        self._model = None
        self._device = None
        self._fallback_chunks: list[dict] = []

        self._try_init_vector_mode()

        if not self._ready:
            self._fallback_chunks = _load_fallback_chunks()

    def _try_init_vector_mode(self) -> None:
        try:
            if not os.path.isdir(CHROMA_DIR):
                return

            import chromadb
            client = chromadb.PersistentClient(path=CHROMA_DIR)
            collection = client.get_collection(name=COLLECTION_NAME)
            if collection.count() == 0:
                return

            import torch
            from sentence_transformers import SentenceTransformer

            device = "cuda" if torch.cuda.is_available() else "cpu"
            model = SentenceTransformer(MODEL_NAME, device=device)

            self._collection = collection
            self._model = model
            self._device = device
            self._ready = True
        except Exception:
            self._ready = False
            self._collection = None
            self._model = None
            self._device = None

    @property
    def chunk_count(self) -> int:
        if self._ready and self._collection is not None:
            return self._collection.count()
        return len(self._fallback_chunks)

    @property
    def is_vector_mode(self) -> bool:
        return self._ready

    @property
    def chunks(self):
        if self._ready and self._collection is not None:
            return _ChunkCount(self._collection.count())
        return self._fallback_chunks

    def _detect_factions(self, query: str) -> set[str]:
        q = query.lower()
        found: set[str] = set()
        for faction, kws in FACTION_KEYWORDS.items():
            for kw in kws:
                if kw in q:
                    found.add(faction)
                    break
        return found

    def search(self, query: str, top_k: int = 4) -> list[dict]:
        if self._ready:
            return self._search_vector(query, top_k)
        return self._search_fallback(query, top_k)

    def _search_vector(self, query: str, top_k: int = 4) -> list[dict]:
        query_lower = query.lower()
        query_factions = self._detect_factions(query)
        file_hints = _query_file_hints(query_lower)

        priority_chunks: list[dict] = []
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
                [query], normalize_embeddings=True, device=self._device
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

        result: list[dict] = []
        seen_texts: set[str] = set()
        for c in combined:
            key = c["text"][:100]
            if key in seen_texts:
                continue
            seen_texts.add(key)
            result.append(c)
            if len(result) >= top_k:
                break

        return result

    def _search_fallback(self, query: str, top_k: int = 4) -> list[dict]:
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

        scored: list[tuple[int, dict]] = []
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

    def format_context(self, query: str, top_k: int = 4) -> str:
        chunks = self.search(query, top_k=top_k)
        if not chunks:
            return ""
        lines = ["=== СПРАВКА ИЗ БАЗЫ ЗНАНИЙ ==="]
        for c in chunks:
            lines.append(f"\n[{c['source']}]\n{c['text']}")
        lines.append("\n=== КОНЕЦ СПРАВКИ ===")
        return "".join(lines)


# ---------- модульный singleton для удобства ----------
_INSTANCE: KnowledgeBase | None = None


def get_kb() -> KnowledgeBase:
    """Вернуть единственный экземпляр KnowledgeBase (ленивая инициализация)."""
    global _INSTANCE
    if _INSTANCE is None:
        _INSTANCE = KnowledgeBase()
    return _INSTANCE
