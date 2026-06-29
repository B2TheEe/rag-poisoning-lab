# OWASP LLM Top 10 Coverage — rag-poisoning-lab

Mapping van de geplande challenges in dit lab op OWASP LLM Top 10 (v2025).

> **Reading guide:** Symbool-betekenis in de Coverage-kolom.
> - 🟢 **Cijfermatig gedekt** — eigen meetdata.
> - 🟡 **Narratief gedekt** — geraakt in writeup/payloads, geen aparte metric.
> - 🔵 **Gepland** — in design-doc, nog niet gemeten.
> - ⚪ **Niet gedekt** — buiten scope (zie 'See instead').

| ID    | Categorie (v2025)                  | Coverage | Bewijs in repo                                                          | See instead                              |
|-------|------------------------------------|:--------:|-------------------------------------------------------------------------|------------------------------------------|
| LLM01 | Prompt Injection (indirect)        | 🔵       | Week 2 design: 8 payloads × 4 defenses × 2 modellen = 80 runs gepland.   | Voor *direct* variant: **[vulnerable-ai-agent-lab](https://github.com/B2TheEe/vulnerable-ai-agent-lab)**. |
| LLM02 | Sensitive Information Disclosure   | ⚪       | n.v.t. — geen secrets in corpus.                                         | vulnerable-ai-agent-lab wk2 LFI.         |
| LLM03 | Supply Chain                       | 🟡       | Threat model: aanvaller kan documenten in `corpus/malicious/` plaatsen — supply-chain aanval op kennisbase. Geen aparte metric. | Aparte 'compromised-document-source' challenge mogelijk in week 4+. |
| LLM04 | **Data and Model Poisoning**       | 🔵       | **Hoofdscope** — RAG-corpus poisoning is de centrale dreiging. Week 1 stap A (real ingest) ✓, week 1 stap B + week 2 in design. | — |
| LLM05 | Improper Output Handling           | ⚪       | n.v.t. — geen tools, geen downstream-uitvoer.                            | vulnerable-ai-agent-lab wk4.             |
| LLM06 | Excessive Agency                   | ⚪       | n.v.t. — RAG-agent heeft alleen "read corpus" capability, geen tools.    | vulnerable-ai-agent-lab wk3 (hoofdvondst). |
| LLM07 | System Prompt Leakage              | 🟡       | Persona-hijack payload (CISO-memo frame) raakt dit. Geen aparte metric.  | Aparte challenge mogelijk later.         |
| LLM08 | **Vector and Embedding Weaknesses**| 🔵       | Week 3 in design — `embedding-collision-01` payload + `top-k-rerank` defense moet hier op meten. | — |
| LLM09 | Misinformation                     | 🟡       | Implicit — gepoisoned corpus leidt tot fout antwoord. Geen apart cijfer ("hallucination vs misleading retrieval" splitsing). | — |
| LLM10 | Unbounded Consumption              | ⚪       | n.v.t. — lab draait offline, geen rate-limit-vraagstuk.                  | —                                        |

## Hoofdthese die deze repo cijfermatig hard wil maken

**Trust-laag bepaalt defense-set.** Per-tool defenses (vulnerable-ai-agent-lab
wk3-thema) doen niets tegen indirect injection via gepoisonde retrieval.
Chunk-laag defenses (input-sanitize, delimiter-fencing, provenance-tag)
plus system-prompt defense (instruction-defense) zijn de complementaire
stack. Cross-lab tabel hieronder na week 2 invullen.

## Cross-lab kompas

Beide repos samen dekken alle drie de injection-trust-lagen:

| Trust-laag                         | Lab dat het dekt                  | Defense-categorie               |
|------------------------------------|-----------------------------------|---------------------------------|
| user-prompt                        | vulnerable-ai-agent-lab           | input-regex, input-judge        |
| tool-args                          | vulnerable-ai-agent-lab           | per-tool allowlist              |
| tool-output (fetched content)      | vulnerable-ai-agent-lab wk4       | output-sanitizer, output-judge  |
| **retrieved content (RAG)**        | **rag-poisoning-lab**             | **chunk-sanitize, fencing, provenance, instruction-defense** |
| **embedding-space**                | **rag-poisoning-lab** wk3         | **rerank, score-threshold**     |

## Wat dit lab **niet** dekt (eerlijk)

LLM02, LLM05, LLM06, LLM10 zijn buiten scope. Voor LLM02/05/06 dekt
zuster-repo `vulnerable-ai-agent-lab` het complementaire vlak.
