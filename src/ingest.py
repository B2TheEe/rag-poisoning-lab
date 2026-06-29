"""Ingest pipeline: corpus → vectorstore.

WEEK 1 STATUS: real chromadb + sentence-transformers integration.

The stub-API (returns dict with 'docs' and 'count') is preserved so the
runner and the week-0 smoke tests keep working. Under the hood we now
chunk each document, embed with sentence-transformers/all-MiniLM-L6-v2,
and upsert into a persistent ChromaDB collection.

Backend selection:
- Default: real chromadb + sentence-transformers (downloads model on first run).
- Fixture mode (env RAG_INGEST_BACKEND=stub or use_real=False): JSON manifest,
  matches the week-0 stub. Used by CI and the offline smoke test so we don't
  pay the ~80MB model download on every git push.

CLI:
    python -m src.ingest                    # real backend, default corpus/
    python -m src.ingest corpus --stub      # force fixture backend
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Iterable

DEFAULT_STORE = "chroma_db"
DEFAULT_EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_COLLECTION = "rag-poison-lab"
DEFAULT_CHUNK_CHARS = 500     # ~120 tokens on average — good for MiniLM
DEFAULT_CHUNK_OVERLAP = 80    # avoid splitting mid-instruction


# ─────────────────────────────────────────────────────────────
# Chunking — pure function, no deps
# ─────────────────────────────────────────────────────────────

_PARAGRAPH_SPLIT = re.compile(r"\n\s*\n")


def _chunk_doc(text: str, max_chars: int, overlap: int) -> list[str]:
    """Greedy paragraph-aware chunker.

    Splits on blank lines (markdown paragraphs), then packs paragraphs
    into chunks ≤ max_chars. Overlap is applied as a tail-prefix between
    consecutive chunks so an injection straddling a chunk boundary still
    appears whole in at least one chunk (relevant for the poisoning
    challenge — see docs/week1-design.md if you write one).
    """
    paragraphs = [p.strip() for p in _PARAGRAPH_SPLIT.split(text) if p.strip()]
    if not paragraphs:
        return []

    chunks: list[str] = []
    buf = ""
    for para in paragraphs:
        candidate = f"{buf}\n\n{para}" if buf else para
        if len(candidate) <= max_chars:
            buf = candidate
            continue
        # flush current buffer; start new one with overlap from old tail
        if buf:
            chunks.append(buf)
            tail = buf[-overlap:] if overlap and len(buf) > overlap else ""
            buf = f"{tail}\n\n{para}" if tail else para
        else:
            # single paragraph already exceeds max_chars — hard split
            for i in range(0, len(para), max_chars - overlap):
                chunks.append(para[i : i + max_chars])
            buf = ""
    if buf:
        chunks.append(buf)
    return chunks


# ─────────────────────────────────────────────────────────────
# Stub backend (preserves week-0 contract, no deps, fast)
# ─────────────────────────────────────────────────────────────

def _ingest_stub(corpus_dir: Path, store_path: Path) -> dict:
    store_path.parent.mkdir(parents=True, exist_ok=True)
    docs = []
    for md in sorted(corpus_dir.rglob("*.md")):
        docs.append({"path": str(md.relative_to(corpus_dir)), "content": md.read_text()})
    manifest = {"docs": docs, "count": len(docs), "backend": "stub"}
    # Stub keeps writing the legacy single-file path for back-compat with the
    # week-0 retrieve() stub. Real backend writes into a directory.
    json_path = store_path if store_path.suffix == ".json" else store_path / "store.json"
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(manifest, indent=2))
    return manifest


# ─────────────────────────────────────────────────────────────
# Real backend (chromadb + sentence-transformers)
# ─────────────────────────────────────────────────────────────

def _ingest_real(
    corpus_dir: Path,
    store_path: Path,
    collection_name: str,
    embed_model: str,
    chunk_chars: int,
    chunk_overlap: int,
) -> dict:
    # Imports are lazy so 'stub' backend never pays the import cost
    # (chromadb + transformers pulls in torch — ~700MB-ish RAM).
    import chromadb
    from chromadb.config import Settings
    from sentence_transformers import SentenceTransformer

    # If a legacy stub artifact (store.json file) sits at store_path, refuse
    # to silently delete user data — point at the cleanup instead.
    if store_path.is_file():
        raise FileExistsError(
            f"store_path {store_path} is a file (legacy stub artifact). "
            f"Remove it before running the real backend:  rm {store_path}"
        )
    # Same trap one level down (week-0 default wrote chroma_db/store.json).
    legacy_inside = store_path / "store.json"
    if store_path.is_dir() and legacy_inside.exists():
        legacy_inside.unlink()  # safe — stub manifest is regenerable from corpus

    store_path.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(
        path=str(store_path),
        settings=Settings(anonymized_telemetry=False, allow_reset=True),
    )

    # Reset is intentional — week-1 corpus is small, idempotent re-ingest
    # avoids "duplicate id" errors and matches the stub semantics.
    try:
        client.delete_collection(collection_name)
    except (ValueError, Exception):  # noqa: BLE001 — chroma raises different types per version
        pass
    collection = client.get_or_create_collection(name=collection_name)

    encoder = SentenceTransformer(embed_model)

    all_chunks: list[str] = []
    all_metadatas: list[dict] = []
    all_ids: list[str] = []
    docs_out: list[dict] = []

    for md in sorted(corpus_dir.rglob("*.md")):
        rel = str(md.relative_to(corpus_dir))
        content = md.read_text()
        docs_out.append({"path": rel, "content": content})

        chunks = _chunk_doc(content, max_chars=chunk_chars, overlap=chunk_overlap)
        for i, chunk in enumerate(chunks):
            all_chunks.append(chunk)
            all_metadatas.append({
                "source": rel,
                "chunk_index": i,
                "category": "malicious" if rel.startswith("malicious/") else "benign",
            })
            all_ids.append(f"{rel}::{i}")

    if all_chunks:
        # Embed in one batch — corpus is small. For larger corpora batch by 64.
        embeddings = encoder.encode(all_chunks, show_progress_bar=False).tolist()
        collection.add(
            ids=all_ids,
            documents=all_chunks,
            embeddings=embeddings,
            metadatas=all_metadatas,
        )

    return {
        "docs": docs_out,
        "count": len(docs_out),
        "chunks": len(all_chunks),
        "backend": "chromadb",
        "embed_model": embed_model,
        "collection": collection_name,
        "store": str(store_path),
    }


# ─────────────────────────────────────────────────────────────
# Public API — preserves week-0 signature
# ─────────────────────────────────────────────────────────────

def ingest(
    corpus_dir: str | Path,
    store_path: str | Path = DEFAULT_STORE,
    *,
    use_real: bool | None = None,
    collection_name: str = DEFAULT_COLLECTION,
    embed_model: str = DEFAULT_EMBED_MODEL,
    chunk_chars: int = DEFAULT_CHUNK_CHARS,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> dict:
    """Walk corpus_dir, ingest into store. Returns manifest dict.

    use_real:
      - None  (default): env RAG_INGEST_BACKEND=stub forces stub, else real.
      - True            : force real chromadb backend.
      - False           : force stub backend (CI / smoke-test).

    Stub returns {'docs', 'count', 'backend': 'stub'}.
    Real returns {'docs', 'count', 'chunks', 'backend': 'chromadb', ...}.
    """
    corpus_dir = Path(corpus_dir)
    store_path = Path(store_path)
    if not corpus_dir.exists():
        raise FileNotFoundError(f"corpus directory does not exist: {corpus_dir}")

    if use_real is None:
        use_real = os.environ.get("RAG_INGEST_BACKEND", "real").lower() != "stub"

    if not use_real:
        return _ingest_stub(corpus_dir, store_path)
    return _ingest_real(
        corpus_dir,
        store_path,
        collection_name=collection_name,
        embed_model=embed_model,
        chunk_chars=chunk_chars,
        chunk_overlap=chunk_overlap,
    )


if __name__ == "__main__":
    import sys
    args = sys.argv[1:]
    use_real: bool | None = None
    if "--stub" in args:
        use_real = False
        args.remove("--stub")
    if "--real" in args:
        use_real = True
        args.remove("--real")
    target = args[0] if args else "corpus"
    result = ingest(target, use_real=use_real)
    if result["backend"] == "chromadb":
        print(
            f"[ingest real] {result['count']} doc(s) → {result['chunks']} chunk(s) "
            f"into '{result['collection']}' at {result['store']}"
        )
    else:
        print(f"[ingest stub] {result['count']} doc(s) indexed from {target}")
