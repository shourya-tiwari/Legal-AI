# AI Stack: Model Selection, Routing, and RAG Architecture

V1 hardcodes one model behind one client (`genai_client.py`, Gemini Developer API). V2 keeps the *discipline* — one centralized place that owns all model access — but turns it into a **Model Router** that chooses among multiple open-weight and commercial models based on task, data sensitivity, latency budget, and cost, and adds a real retrieval layer in front of generation.

## Layered AI architecture

```
Layer 0  Ingestion:        CV pipeline (COMPUTER_VISION.md) → NLP pipeline (NLP.md)
Layer 1  Representation:   Clause objects, entities, deontic tags → Knowledge Graph (KNOWLEDGE_GRAPH.md)
Layer 2  Retrieval:        Hybrid dense + sparse + graph retrieval (this file)
Layer 3  Learned models:   Fine-tuned classifiers/embeddings/scorers (DEEP_LEARNING.md)
Layer 4  Generation:       Open-weight + frontier LLMs via the Model Router (this file)
Layer 5  Orchestration:    Multi-agent graphs consuming layers 0-4 as tools (AGENTS.md)
Layer 6  Memory:           Session/episodic/semantic/procedural stores (AGENTS.md)
Layer 7  Evaluation:       Ragas / CUAD-based eval, tracing (ARCHITECTURE.md)
```

## Model Router

The Model Router is the single point through which every service calls a model — no service is permitted to instantiate a model client directly, exactly mirroring the discipline V1 already established with `genai_client.py`.

**Routing inputs**: task type, document sensitivity tier (`Public`/`Internal`/`Confidential`/`Privileged`, `ARCHITECTURE.md`), org policy (`model_tier_default`), latency budget, and (for fine-tuned tasks) confidence from a cheaper model that determines whether escalation is warranted.

**Tiers**:

| Tier | Where it runs | Allowed for | Examples |
|---|---|---|---|
| **Tier 0 — Local specialist** | Self-hosted, small, task-specific | All sensitivity levels, including air-gapped | Fine-tuned classifiers/taggers (`DEEP_LEARNING.md`), NER models, deontic tagger |
| **Tier 1 — Self-hosted open-weight LLM** | vLLM, on the platform's or customer's own infrastructure | All sensitivity levels including `Privileged` | Llama 3.3 70B / Llama 3.1 8B, Qwen2.5-72B-Instruct, Mixtral 8x22B |
| **Tier 2 — Commercial frontier (opt-in)** | Vendor API, leaves the deployment perimeter | `Public`/`Internal` by default; `Confidential`/`Privileged` only with explicit org opt-in per document | Gemini (kept from V1), optionally Claude/GPT-class models |

A document tagged `Privileged` never reaches Tier 2 unless an org admin explicitly overrides it per-document — enforced server-side in the Model Router, not just as a UI affordance (`ARCHITECTURE.md` security section).

### Model selection by task

| Task | Default (Tier 0/1, open-weight) | Escalation (Tier 2) | Rationale |
|---|---|---|---|
| Plain-English rewrite | Llama 3.1 8B-Instruct (fast, cheap, sufficient for style transfer) | Gemini / frontier for very long or unusually dense documents | Rewrite is a well-bounded style-transfer task; small open models handle it well |
| Structure/timeline extraction | Qwen2.5-72B-Instruct (strong structured-output/JSON reliability) | Frontier if JSON validation fails twice | Extraction quality is JSON-schema-adherence-sensitive; Qwen2.5 is a documented strength here among open weights |
| Risk analysis (AI pass) | Llama 3.3 70B | Frontier for portfolio-level cross-document risk (higher reasoning load) | Single-clause risk flagging is within reach of a strong open 70B model |
| Q&A / chat | Llama 3.3 70B, RAG-grounded | Frontier for multi-hop questions across a large portfolio | Grounding via RAG reduces reliance on raw model scale |
| Contextualizer / advisory explanation | Llama 3.3 70B + RAG | Frontier opt-in for `exec`/`lawyer` tone on high-stakes documents | Matches V1's existing guardrail-heavy prompt design, now with real retrieved sources instead of a static list |
| Negotiation/drafting suggestions | Qwen2.5-72B-Instruct or Mixtral 8x22B | Frontier for final-draft polish, opt-in | Drafting benefits from strong instruction-following; open weights are competitive |
| Embeddings | **BGE-M3** (BAAI, open source; dense + sparse + ColBERT-style multi-vector in one model) | — (no commercial escalation needed) | Multilingual, strong retrieval benchmarks, single model covers dense+sparse |
| Reranking | **bge-reranker-v2-m3** (open source cross-encoder) | — | Standard open-source reranker, no commercial dependency justified |
| OCR / layout | Tesseract + LayoutLMv3 + Donut (`COMPUTER_VISION.md`) | Commercial Document AI API, only as a confidence-triggered fallback | Commercial OCR only earns its cost on genuinely low-confidence scans |
| NER | Fine-tuned InLegalBERT/LegalBERT + GLiNER for zero-shot types (`NLP.md`) | — | Domain-specific, no reason to route to a general LLM for structured extraction |

This table is a starting point, not a permanent commitment — the eval harness (`ARCHITECTURE.md`) is what actually decides whether a given open-weight model meets the bar for a task; any change to this table must be justified by an eval run, not by preference.

## RAG architecture

V1's RAG (`services/contextualizer/rag.py`) is a single hardcoded 28-string list embedded once into an in-memory FAISS index, rebuilt from scratch on every process start, used only by the Contextualizer feature. V2 generalizes retrieval into a shared service used by every agent that needs grounding.

### Corpus composition

| Source | Content | Update cadence |
|---|---|---|
| User document corpus | The org's own uploaded contracts, versioned | Real-time on upload |
| Statutes & regulations | Curated, jurisdiction-tagged statutory text (starting with the jurisdictions V1's hardcoded hints already covered: CA landlord/tenant, employment, general contract law — now sourced and cited, not asserted) | Periodic ingestion pipeline, source-tracked |
| Case law (where licensed) | Precedent excerpts relevant to common clause types | Periodic, license-dependent |
| Public legal ML datasets | **CUAD** (Contract Understanding Atticus Dataset), **ContractNLI** | Used primarily for eval (`ARCHITECTURE.md`), secondarily as bootstrapping retrieval content |

Every corpus entry carries a **source citation** (statute section, case name, or document+clause ID) — the RAG Service refuses to return an uncited passage, closing the exact gap flagged in V1's `FEATURES.md` (hardcoded hints with no cited authority).

### Chunking

Hierarchical, clause-aware chunking, unifying and extending V1's two divergent implementations (`rewriter.py`'s naive char-window split vs. `timeline.py`'s better paragraph/sentence splitter — see `docs/v1/ARCHITECTURE.md`): the canonical chunk boundary is the **Clause object** produced by the NLP pipeline (`NLP.md`), not an arbitrary character window. Clauses are further grouped into section-level and document-level summaries for coarse-to-fine retrieval.

### Hybrid retrieval

1. **Dense retrieval** — BGE-M3 embeddings in Qdrant, cosine similarity over clause-level and section-level vectors.
2. **Sparse retrieval** — BM25 (or SPLADE for learned sparse vectors) over the same corpus, catching exact-term/defined-term matches dense retrieval can miss (critical in legal text, where a specific defined term or statute citation matters more than semantic paraphrase).
3. **Graph-grounded retrieval (GraphRAG)** — traversal of the Knowledge Graph (`KNOWLEDGE_GRAPH.md`) from entities mentioned in the query to connected clauses/obligations/statutes, surfacing results plain vector/keyword search would miss (e.g., "what else references this defined term across the portfolio").
4. **Fusion + reranking** — candidates from all three retrievers are merged (reciprocal rank fusion) and reranked with **bge-reranker-v2-m3** before being passed to generation.
5. **Citation-grounded generation** — the generation prompt requires every factual claim to reference a retrieved chunk's citation ID; the Verifier agent (`AGENTS.md`) checks this post-hoc via the NLI faithfulness checker.

This directly replaces V1's fallback behavior (`get_rag_hints()` silently falling back to a static per-contract-type dict when retrieval "fails") with a retrieval pipeline that has three independent retrieval strategies to fall back across before resorting to an explicit "not enough grounded information — verify locally" response, which the UI must surface honestly rather than papering over.

## Prompt and version governance

- Prompts live as versioned templates in `packages/prompts`, not as string literals scattered across service files (V1's pattern in `rewriter.py`, `chatbot.py`, `timeline.py`, `detector.py`, `templates.py`).
- Every generation call logs which prompt version + model version produced it, joined to `eval_runs` (`ARCHITECTURE.md`) so a quality regression can be traced to a specific change.
- No prompt or model swap ships without a passing eval run against the Ragas/CUAD-based regression suite.

## Cost and latency governance

- Tier 0/1 (self-hosted) calls are the default for all sensitivity levels and the large majority of task volume; Tier 2 (commercial) is reserved for tasks where eval data shows a material quality gap, keeping per-request cost predictable and bounded by infrastructure the platform controls.
- Org-level budgets and per-request cost logging (`BACKEND.md` rate limiting) prevent runaway spend on the commercial tier.
