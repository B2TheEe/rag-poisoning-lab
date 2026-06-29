"""Week-1 step-A tests: real chromadb + sentence-transformers ingest + retrieve.

These tests are SKIPPED by default to keep CI cheap (sentence-transformers
downloads ~80MB on first run). Opt in by setting RAG_TEST_REAL_INGEST=1.

Run manually after the first model download is cached:
    RAG_TEST_REAL_INGEST=1 pytest tests/test_ingest_real.py -v
"""
from __future__ import annotations
import os
from pathlib import Path

import pytest

REAL_OPT_IN = os.environ.get("RAG_TEST_REAL_INGEST", "").lower() in ("1", "true", "yes")
pytestmark = pytest.mark.skipif(
    not REAL_OPT_IN,
    reason="real ingest tests opt-in via RAG_TEST_REAL_INGEST=1 (avoid ~80MB download in CI)",
)


# ─────────────────────────────────────────────────────────────
# Chunker — pure function, doesn't need the download, but ride the same flag
# so the whole file skips together when CI runs.
# ─────────────────────────────────────────────────────────────


class TestChunkDoc:
    def test_short_doc_is_one_chunk(self):
        from src.ingest import _chunk_doc
        chunks = _chunk_doc("short text", max_chars=500, overlap=50)
        assert chunks == ["short text"]

    def test_packs_paragraphs_under_limit(self):
        from src.ingest import _chunk_doc
        text = "para one.\n\npara two.\n\npara three."
        chunks = _chunk_doc(text, max_chars=500, overlap=50)
        assert len(chunks) == 1
        assert "one" in chunks[0] and "three" in chunks[0]

    def test_splits_when_over_limit(self):
        from src.ingest import _chunk_doc
        # max_chars=20, each paragraph ~20 chars → forces splits
        text = "paragraph one is long.\n\nparagraph two is long.\n\nthree."
        chunks = _chunk_doc(text, max_chars=25, overlap=5)
        assert len(chunks) >= 2

    def test_overlap_preserves_boundary_text(self):
        from src.ingest import _chunk_doc
        text = "AAAA BBBB CCCC.\n\nDDDD EEEE FFFF."
        chunks = _chunk_doc(text, max_chars=20, overlap=8)
        assert len(chunks) >= 2
        # the tail of chunk N appears at the start of chunk N+1 (modulo trim)
        tail = chunks[0][-5:]
        assert tail in chunks[1]


# ─────────────────────────────────────────────────────────────
# Real ingest — needs chromadb + sentence-transformers installed.
# ─────────────────────────────────────────────────────────────


class TestRealIngest:
    def test_ingest_real_writes_chroma_store(self, tmp_path):
        from src.ingest import ingest

        # Tiny corpus to keep wallclock down
        (tmp_path / "corpus").mkdir()
        (tmp_path / "corpus" / "a.md").write_text(
            "# A\n\nFirst paragraph about cats.\n\nSecond paragraph about dogs."
        )
        (tmp_path / "corpus" / "b.md").write_text(
            "# B\n\nFinance Q3 results.\n\nRevenue grew 18%."
        )

        store = tmp_path / "store"
        result = ingest(tmp_path / "corpus", store_path=store, use_real=True)

        assert result["backend"] == "chromadb"
        assert result["count"] == 2
        assert result["chunks"] >= 2
        assert (store / "chroma.sqlite3").exists()

    def test_retrieve_real_returns_relevant_chunk(self, tmp_path):
        from src.ingest import ingest
        from src.rag_agent import retrieve

        (tmp_path / "corpus").mkdir()
        (tmp_path / "corpus" / "pets.md").write_text(
            "# Pets\n\nCats are independent felines that nap a lot."
        )
        (tmp_path / "corpus" / "finance.md").write_text(
            "# Finance\n\nQuarterly earnings exceeded analyst expectations."
        )

        store = tmp_path / "store"
        ingest(tmp_path / "corpus", store_path=store, use_real=True)

        # Vector search should rank the cats paragraph above the finance one
        # for an animal-related query.
        results = retrieve("tell me about cats", store_path=store, k=2, use_real=True)
        assert results, "retrieve returned no chunks"
        assert "cat" in results[0].lower() or "felin" in results[0].lower()

    def test_retrieve_excludes_unrelated_chunks_when_k_small(self, tmp_path):
        from src.ingest import ingest
        from src.rag_agent import retrieve

        (tmp_path / "corpus").mkdir()
        (tmp_path / "corpus" / "a.md").write_text(
            "Python is a programming language used for data science."
        )
        (tmp_path / "corpus" / "b.md").write_text(
            "The mango is a tropical fruit native to South Asia."
        )

        store = tmp_path / "store"
        ingest(tmp_path / "corpus", store_path=store, use_real=True)

        top = retrieve("what fruit grows in Asia?", store_path=store, k=1, use_real=True)
        assert len(top) == 1
        assert "mango" in top[0].lower() or "fruit" in top[0].lower()
