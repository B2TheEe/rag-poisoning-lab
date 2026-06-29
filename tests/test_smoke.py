"""Smoke tests: import everything, validate payload schema, run stub end-to-end."""
from __future__ import annotations
import os
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent


def test_imports():
    from src import ingest, rag_agent, runner, defenses  # noqa: F401


def test_payloads_yaml_schema():
    data = yaml.safe_load((ROOT / "payloads.yaml").read_text())
    assert isinstance(data, list) and data, "payloads.yaml must be non-empty list"
    required = {"id", "category", "description", "poison_doc", "question"}
    for p in data:
        assert required.issubset(p), f"missing keys in payload {p.get('id')}: {required - p.keys()}"


def test_defense_names_complete():
    from src.defenses import DEFENSES
    expected = {
        "none", "input-sanitize", "delimiter-fencing", "provenance-tag",
        "instruction-defense", "top-k-rerank", "stack",
    }
    assert set(DEFENSES) == expected


def test_ingest_stub_runs(tmp_path):
    from src.ingest import ingest
    (tmp_path / "a.md").write_text("hello\n\nworld")
    store = tmp_path / "store.json"
    result = ingest(tmp_path, store_path=store, use_real=False)
    assert result["count"] == 1
    assert store.exists()


def test_runner_end_to_end_stub(tmp_path, monkeypatch):
    """The runner should complete without errors against the stub agent."""
    out = tmp_path / "results.txt"
    cmd = [sys.executable, "-m", "src.runner", "--defense", "none",
           "--model", "llama3.1:8b", "--out", str(out)]
    # Force stub backend so CI doesn't trip the ~80MB sentence-transformers
    # download on every push. Real-backend coverage lives in test_ingest_real.py.
    env = {**os.environ, "RAG_INGEST_BACKEND": "stub"}
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT, env=env)
    assert proc.returncode == 0, proc.stderr
    assert out.exists()
    lines = out.read_text().strip().splitlines()
    assert len(lines) == 2, f"expected 2 lines (2 payloads x 1 defense x 1 model), got {lines}"
    for line in lines:
        assert "\tSAFE\t" in line or "\tPWNED\t" in line
