"""RAG agent: retrieve top-k chunks, apply defense, call LLM.

WEEK 1 STATUS:
- retrieve() now uses real ChromaDB vector search by default.
- answer() still returns a deterministic stub string — real Ollama call
  lands in week 1 step B.

The retrieve() function auto-detects which backend was used for ingest:
  - directory with chroma_db files → real backend (vector similarity)
  - JSON manifest path             → stub backend (paragraph slice, week-0)
Override with use_real= or env RAG_INGEST_BACKEND=stub.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
from .defenses import DEFENSES

DEFAULT_STORE = "chroma_db"
DEFAULT_EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_COLLECTION = "rag-poison-lab"


def _store_kind(store_path: Path) -> str:
    """Return 'chroma', 'json', or 'missing'."""
    if not store_path.exists():
        return "missing"
    if store_path.is_file() and store_path.suffix == ".json":
        return "json"
    # Chroma persistent client writes chroma.sqlite3 + binaries
    if store_path.is_dir() and (store_path / "chroma.sqlite3").exists():
        return "chroma"
    # Fallback: dir with store.json inside (legacy stub layout)
    if store_path.is_dir() and (store_path / "store.json").exists():
        return "json"
    return "missing"


def _retrieve_stub(question: str, store_path: Path, k: int) -> list[str]:
    """Week-0 stub: first k paragraphs across all docs (no embedding)."""
    if store_path.is_dir():
        store_path = store_path / "store.json"
    if not store_path.exists():
        return []
    manifest = json.loads(store_path.read_text())
    chunks: list[str] = []
    for doc in manifest["docs"]:
        chunks.extend(p.strip() for p in doc["content"].split("\n\n") if p.strip())
    return chunks[:k]


def _retrieve_chroma(
    question: str,
    store_path: Path,
    k: int,
    collection_name: str,
    embed_model: str,
) -> list[str]:
    import chromadb
    from chromadb.config import Settings
    from sentence_transformers import SentenceTransformer

    client = chromadb.PersistentClient(
        path=str(store_path),
        settings=Settings(anonymized_telemetry=False, allow_reset=True),
    )
    collection = client.get_collection(name=collection_name)
    encoder = SentenceTransformer(embed_model)
    q_embed = encoder.encode([question]).tolist()
    res = collection.query(query_embeddings=q_embed, n_results=k)
    # res["documents"] is list-of-lists (one per query); we sent one query.
    return list(res.get("documents", [[]])[0])


def retrieve(
    question: str,
    store_path: str | Path = DEFAULT_STORE,
    k: int = 3,
    *,
    use_real: bool | None = None,
    collection_name: str = DEFAULT_COLLECTION,
    embed_model: str = DEFAULT_EMBED_MODEL,
) -> list[str]:
    """Return top-k chunks. Backend auto-detected from store_path layout."""
    sp = Path(store_path)

    if use_real is None:
        env = os.environ.get("RAG_INGEST_BACKEND", "").lower()
        if env == "stub":
            use_real = False
        elif env == "real":
            use_real = True
        else:
            use_real = _store_kind(sp) == "chroma"

    if not use_real:
        return _retrieve_stub(question, sp, k)
    return _retrieve_chroma(question, sp, k, collection_name, embed_model)


def answer(
    question: str,
    *,
    store_path: str = DEFAULT_STORE,
    model: str = "llama3.1:8b",
    defense: str = "none",
    k: int = 3,
) -> str:
    """Build prompt, call LLM, return text. Stub returns a synthetic string."""
    if defense not in DEFENSES:
        raise ValueError(f"unknown defense: {defense}")
    chunks = retrieve(question, store_path=store_path, k=k)
    chunks, _suffix = DEFENSES[defense](chunks, question)

    # TODO week 1 step B: actually call Ollama with prompt = chunks + question.
    # For now synthesize so the runner works end-to-end.
    return (
        f"[STUB answer model={model} defense={defense} k={len(chunks)}] "
        f"would answer: {question!r}"
    )
