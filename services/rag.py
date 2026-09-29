# PATCH_17
"""services/rag.py — RAG-поиск по базе знаний WH40K.

Исправления PATCH_17:
  - faction-фильтр через where (не перезаписывается внутри цикла);
  - порог релевантности MAX_DIST для отсечения мусора;
  - priority chunks грузятся только по разрешённым фракциям.
"""
from __future__ import annotations

import os
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]

MODEL_NAME = "intfloat/multilingual-e5-small"
CHROMA_DIR = str(_ROOT / "chroma_db")
COLLECTION_NAME = "knowledge"

MAX_DIST = 1.1

FOLDER_TO_FACTION = {
    "imperium": "imperium", "chaos": "chaos", "eldar": "eldar",
    "necrons": "necrons", "orks": "orks", "tau": "tau",
    "tyranids": "tyranids", "general": "general",
    "glossary": "general",
}

FACTION_KEYWORDS = {
    "eldar": ["эльдар", "аэльдари", "асуриани", "друкхари", "арлекин",
              "экзодит", "иннари", "крафтворлд", "сюрикен", "провидец",
              "костопевец", "баньши", "скорпион", "аспект", "кхейн",
              "цегорах", "слаанеш"],
    "imperium": ["империум", "космодесантник", "астартес", "гвардия",
                 "инквизиц", "механикус", "сороритас", "экклезиарх",
                 "комиссар", "терра", "император", "болтер", "лазган",
                 "адептус"],
    "chaos": ["хаос", "кхорн", "тзинч", "нургл", "слаанеш",
              "космодесантник хаоса", "демон", "варп", "ересь хоруса",
              "абаддон", "несущие слово", "тысяча сынов",
              "гвардия смерти", "пожиратели миров"],
    "orks": ["орк", "орки", "ваагх", "гофф", "смертельный череп",
             "гретчин", "мекбой", "чоппа", "шута", "слагга",
             "свободный орк", "клан", "змеиные клыки", "багровые клыки",
             "кровавые топоры", "злые солнца"],
    "tau": ["тау", "каста огня", "каста воды", "каста земли",
            "каста воздуха", "эфирн", "крут", "веспид", "импульсн",
            "боевой костюм", "септ", "фарсайт", "воин огня"],
    "necrons": ["некрон", "некронт", "гробниц", "династи",
                "к'тан", "гаусс", "проклят", "сарек", "молчаливый",
                "имотех", "тразин", "некродермис"],
    "tyranids": ["тиранид", "генокрад", "флот-улей", "сверхразум",
                 "биоморф", "термигант", "хормагант", "карнифекс",
                 "ликтор", "воин улья", "тень в варпе"],
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
    chunks: list[dict] = []
    data_dir = _ROOT / "data"
    if not data_dir.is_dir():
        return chunks
    for faction_dir in sorted(data_dir.iterdir()):
        if not faction_dir.is_dir():
            continue
        if faction_dir.name in ("users", "accounts", "_replacements"):
            continue
        faction = FOLDER_TO_FACTION.get(faction_dir.name, faction_dir.name)
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

    def search(self, query: str, top_k: int = 4,
               faction: str | None = None) -> list[dict]:
        if self._ready:
            return self._search_vector(query, top_k, faction=faction)
        return self._search_fallback(query, top_k, faction=faction)

    def _search_vector(self, query: str, top_k: int = 4,
                       faction: str | None = None) -> list[dict]:
        # PATCH_17: без перезаписи faction, где-фильтр, порог дистанции
        query_lower = query.lower()
        query_factions = self._detect_factions(query)
        file_hints = _query_file_hints(query_lower)

        if faction:
            allowed_factions = {faction, "general"}
        elif query_factions:
            allowed_factions = set(query_factions) | {"general"}
        else:
            allowed_factions = None

        priority_chunks: list[dict] = []
        if file_hints and allowed_factions:
            try:
                where = {"faction": {"$in": list(allowed_factions)}}
                subset = self._collection.get(
                    where=where, include=["documents", "metadatas"],
                )
                for doc, meta in zip(subset["documents"], subset["metadatas"]):
                    src = (meta.get("source", "") or "").lower()
                    if any(h in src for h in file_hints):
                        priority_chunks.append({
                            "text": doc,
                            "source": meta.get("source", ""),
                            "faction": meta.get("faction", "general"),
                        })
            except Exception as e:
                print("[rag] priority get fail: " + str(e))

        try:
            query_emb = self._model.encode(
                [query], normalize_embeddings=True, device=self._device
            ).tolist()
            n_fetch = min(top_k * 8, max(self._collection.count(), top_k))
            query_kwargs = {"query_embeddings": query_emb, "n_results": n_fetch}
            if allowed_factions:
                query_kwargs["where"] = {"faction": {"$in": list(allowed_factions)}}
            res = self._collection.query(**query_kwargs)
            docs = res.get("documents", [[]])[0]
            metas = res.get("metadatas", [[]])[0]
            dists = res.get("distances", [[]])[0] if res.get("distances") else [None] * len(docs)
        except Exception as e:
            print("[rag] vector query fail: " + str(e))
            return priority_chunks[:top_k]

        top_priority, mid_priority, low_priority = [], [], []
        for doc, meta, dist in zip(docs, metas, dists):
            if dist is not None and dist > MAX_DIST:
                continue
            item = {
                "text": doc,
                "source": meta.get("source", ""),
                "faction": meta.get("faction", "general"),
            }
            src_low = item["source"].lower()
            fac_match = bool(query_factions) and item["faction"] in query_factions
            src_match = bool(file_hints) and any(h in src_low for h in file_hints)
            if fac_match and src_match:
                top_priority.append(item)
            elif fac_match or src_match:
                mid_priority.append(item)
            else:
                low_priority.append(item)

        combined = priority_chunks + top_priority + mid_priority + low_priority
        result: list[dict] = []
        seen: set[str] = set()
        for c in combined:
            key = c["text"][:120]
            if key in seen:
                continue
            seen.add(key)
            result.append(c)
            if len(result) >= top_k:
                break
        return result

    def _search_fallback(self, query: str, top_k: int = 4,
                         faction: str | None = None) -> list[dict]:
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
        if faction:
            allowed = {faction, "general"}
            scored = [(s, c) for s, c in scored
                      if c.get("faction", "general") in allowed]
        scored.sort(key=lambda x: -x[0])
        return [c for _, c in scored[:top_k]]

    def format_context(self, query: str, top_k: int = 4,
                       faction: str | None = None) -> str:
        chunks = self.search(query, top_k=top_k, faction=faction)
        if not chunks:
            return ""
        lines = ["=== СПРАВКА ИЗ БАЗЫ ЗНАНИЙ ==="]
        for c in chunks:
            lines.append("\n[" + c["source"] + "]\n" + c["text"])
        lines.append("\n=== КОНЕЦ СПРАВКИ ===")
        return "".join(lines)


_INSTANCE: KnowledgeBase | None = None


def get_kb() -> KnowledgeBase:
    global _INSTANCE
    if _INSTANCE is None:
        _INSTANCE = KnowledgeBase()
    return _INSTANCE
