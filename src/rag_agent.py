"""RAG agent: retrieve top-k chunks, apply defense, call LLM.

WEEK 0 STATUS: stub. Real Ollama call + real similarity search lands in week 1.
For now `answer()` returns a deterministic placeholder string, and the retrieval
returns the first k paragraphs of every doc (no embedding yet).
"""
from __future__ import annotations
import json
from pathlib import Path
from .defenses import DEFENSES


def retrieve(question: str, store_path: str = "chroma_db/store.json", k: int = 3) -> list[str]:
    """Return top-k chunks. Stub: returns first k paragraphs across all docs."""
    store = Path(store_path)
    if not store.exists():
        return []
    manifest = json.loads(store.read_text())
    chunks = []
    for doc in manifest["docs"]:
        chunks.extend(p.strip() for p in doc["content"].split("\n\n") if p.strip())
    return chunks[:k]


def answer(
    question: str,
    *,
    store_path: str = "chroma_db/store.json",
    model: str = "llama3.1:8b",
    defense: str = "none",
    k: int = 3,
) -> str:
    """Build prompt, call LLM, return text. Stub returns a synthetic string."""
    if defense not in DEFENSES:
        raise ValueError(f"unknown defense: {defense}")
    chunks = retrieve(question, store_path=store_path, k=k)
    chunks, _suffix = DEFENSES[defense](chunks, question)

    # TODO week 1: actually call Ollama. For now synthesize so the runner works end-to-end.
    return f"[STUB answer model={model} defense={defense} k={len(chunks)}] " \
           f"would answer: {question!r}"
