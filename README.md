# rag-poisoning-lab

![status](https://img.shields.io/badge/status-week%201%20step%20A%20%E2%80%94%20real%20ingest-blue)
![tests](https://img.shields.io/badge/tests-12%2F12%20passing-brightgreen)
![owasp](https://img.shields.io/badge/OWASP-LLM01%20%C2%B7%20LLM03%20%C2%B7%20LLM08-orange)

Intentionally vulnerable RAG (retrieval-augmented generation) testbed. Goal: measure
how indirect prompt injection — instructions embedded in retrieved documents —
defeats LLM agents, and which defense layers actually work.

**Status:** week 1 step A — real ChromaDB ingest + sentence-transformers
embedding live. Ollama LLM call still stubbed (step B).

Sister lab: [vulnerable-ai-agent-lab](https://github.com/B2TheEe/vulnerable-ai-agent-lab) — direct prompt injection. This repo covers the indirect variant.

## OWASP LLM categories covered

Snelle blik: zie [`docs/owasp-coverage.md`](docs/owasp-coverage.md) voor
de volledige tabel + cross-lab kompas.

- LLM01 indirect prompt injection
- LLM04 data and model poisoning (hoofdscope)
- LLM08 vector and embedding weaknesses

## Architecture
```
attacker --[upload doc with injection]--> corpus/malicious/
                                                |
                                                v
                                       src/ingest.py
                                          - chunk
                                          - embed (sentence-transformers)
                                          - store in ChromaDB
                                                |
                                                v
user --[question]--> src/rag_agent.py --[retrieve top-k]--+
                            |
                            v
                  prompt = system + retrieved + question
                            |
                            v
                      Ollama (llama3.1:8b / qwen2.5:7b)
                            |
                            v
                       response (maybe PWNED)
```

## Quickstart
```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
pytest                                    # 5 smoke tests, real-ingest skipped

# Real ingest (first run downloads ~80MB sentence-transformers model)
python -m src.ingest                      # corpus/ → chroma_db/
python -m src.ingest --stub               # force JSON manifest backend

# Opt in to real-backend tests (7 extra cases, ~25s)
RAG_TEST_REAL_INGEST=1 pytest tests/test_ingest_real.py -v

# Baseline matrix (still stub LLM until week 1 step B)
python -m src.runner --defense none --model llama3.1:8b
```

## Backends
- **stub** (default in CI / smoke tests): JSON manifest, no deps beyond pyyaml.
  Used by `test_runner_end_to_end_stub` to keep CI cheap.
- **real** (default at CLI): ChromaDB persistent store +
  sentence-transformers/all-MiniLM-L6-v2 embeddings. Selectable via
  `use_real=True/False` or env `RAG_INGEST_BACKEND=stub|real`.

## Layout
```
docs/week1-design.md   full design doc
src/ingest.py          corpus -> vectorstore (stub)
src/rag_agent.py       retrieve + prompt + LLM call (stub)
src/runner.py          matrix runner: payloads x defenses x models
src/defenses.py        defense layers
payloads.yaml          attack payloads (analogous to vulnerable-ai-agent-lab)
corpus/benign/         legitimate docs
corpus/malicious/      attacker-controlled docs (poisoned)
tests/                 pytest smoke + structural tests
```

## Roadmap
- [x] Week 0: scaffold, design doc, smoke tests
- [x] Week 1 step A: real ingest (chromadb + sentence-transformers/MiniLM-L6-v2),
      paragraph-aware chunker with overlap, vector retrieval, 7 opt-in pytest cases
- [ ] Week 1 step B: real Ollama call in rag_agent.answer(), baseline 8/8 PWNED
- [ ] Week 2: 4 simple defenses, matrix 8x5x2 = 80 runs
- [ ] Week 3: rerank + stack defenses, embedding-collision payloads, 8x7x2 = 112 runs
- [ ] Week 4: cross-lab analysis (direct vs indirect injection)
