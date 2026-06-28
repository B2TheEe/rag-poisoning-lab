# rag-poisoning-lab

![status](https://img.shields.io/badge/status-week%200%20scaffold-blue)
![tests](https://img.shields.io/badge/tests-5%2F5%20passing-brightgreen)
![owasp](https://img.shields.io/badge/OWASP-LLM01%20%C2%B7%20LLM03%20%C2%B7%20LLM08-orange)

Intentionally vulnerable RAG (retrieval-augmented generation) testbed. Goal: measure
how indirect prompt injection — instructions embedded in retrieved documents —
defeats LLM agents, and which defense layers actually work.

**Status:** scaffold (week 0). Skeleton end-to-end, pytest green, real ingest +
Ollama integration lands in week 1.

Sister lab: [vulnerable-ai-agent-lab](https://github.com/B2TheEe/vulnerable-ai-agent-lab) — direct prompt injection. This repo covers the indirect variant.

## OWASP LLM categories covered
- LLM01 indirect prompt injection
- LLM03 training-data / RAG poisoning
- LLM08 vector & embedding weaknesses

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
pip install -r requirements.txt           # not needed yet for stub phase
pytest                                    # smoke tests
python -m src.runner --defense none --model llama3.1:8b   # baseline (stub)
```

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
- [ ] Week 1: real ingest (chromadb + sentence-transformers), basic agent, baseline 8/8 PWNED
- [ ] Week 2: 4 simple defenses, matrix 8x5x2 = 80 runs
- [ ] Week 3: rerank + stack defenses, embedding-collision payloads, 8x7x2 = 112 runs
- [ ] Week 4: cross-lab analysis (direct vs indirect injection)
