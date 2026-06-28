"""Ingest pipeline: corpus -> vectorstore.

WEEK 0 STATUS: stub. Real chromadb + sentence-transformers integration lands in
week 1. For now we just enumerate files and write a JSON manifest so the runner
and tests have something to talk to.
"""
from __future__ import annotations
import json
from pathlib import Path


def ingest(corpus_dir: str | Path, store_path: str | Path = "chroma_db/store.json") -> dict:
    """Walk corpus_dir, list every .md file, write a manifest.

    Returns a dict with keys: 'docs' (list of {path, content}), 'count'.

    Replaces with real chromadb persistence in week 1.
    """
    corpus = Path(corpus_dir)
    store = Path(store_path)
    store.parent.mkdir(parents=True, exist_ok=True)

    docs = []
    for md in sorted(corpus.rglob("*.md")):
        docs.append({"path": str(md.relative_to(corpus)), "content": md.read_text()})

    manifest = {"docs": docs, "count": len(docs)}
    store.write_text(json.dumps(manifest, indent=2))
    return manifest


if __name__ == "__main__":
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else "corpus"
    result = ingest(target)
    print(f"[ingest stub] {result['count']} doc(s) indexed from {target}")
