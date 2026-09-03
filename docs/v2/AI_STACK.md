# AI Stack: The Model Router, Provider Interface, and RAG

V1 hardcodes one model behind one client (`genai_client.py`, Gemini Developer API). V2 keeps the *discipline* — one centralized place that owns all model access — but turns it into a **provider-agnostic Model Router**: services ask for a capability, the Router resolves it to a `(provider, model)` binding from a declarative policy, and **the default binding is always a self-hosted open-weight model**. Commercial providers are optional plugins that an operator installs and an org opts into; they are never on any feature's critical path.

For the specific model and infrastructure recommendations this document refers to, see `MODEL_STACK.md`.

## Layered AI architecture

```
Layer 0  Ingestion:       CV pipeline (COMPUTER_VISION.md) → NLP pipeline (NLP.md)
Layer 1  Representation:  Clause objects, entities, deontic tags → Knowledge Graph (KNOWLEDGE_GRAPH.md)
Layer 2  Retrieval:       Hybrid dense + sparse + graph retrieval (this file)
Layer 3  Learned models:  Fine-tuned classifiers/embeddings/scorers (DEEP_LEARNING.md)
Layer 4  Generation:      Open-weight LLMs via the Model Router; commercial APIs optional (this file)
Layer 5  Orchestration:   Multi-agent graphs consuming layers 0-4 as tools (AGENTS.md)
Layer 6  Memory:          Session/episodic/semantic/procedural stores (AGENTS.md)
Layer 7  Evaluation:      Inspect AI / Ragas / LegalBench-based eval, tracing (ARCHITECTURE.md)
```

## The provider interface

Every model backend — self-hosted or commercial — implements the same interface. This is the contract that makes the rest of the system vendor-agnostic.

```python
class ModelProvider(Protocol):
    name: str                     # "vllm-local", "ollama", "tei", "gemini", "openai", ...
    hosting_class: HostingClass    # A_CPU | B_SELF_HOSTED | C_EXTERNAL

    def describe(self) -> ProviderCard:
        """Static capabilities: which methods are supported, which models are
        available, per-model context length, modalities, languages, licence,
        max throughput, cost model, and — critically — whether traffic leaves
        the deployment perimeter."""

    def health(self) -> HealthStatus: ...

    # Capability methods — a provider implements the subset it supports;
    # describe() advertises which.
    def generate(self, req: GenerateRequest) -> GenerateResponse: ...
    def generate_structured(self, req: StructuredRequest) -> StructuredResponse: ...
    def embed(self, req: EmbedRequest) -> EmbedResponse: ...
    def rerank(self, req: RerankRequest) -> RerankResponse: ...
    def transcribe(self, req: TranscribeRequest) -> TranscribeResponse: ...
    def synthesize(self, req: SynthesizeRequest) -> SynthesizeResponse: ...
    def tokenize(self, text: str, model: str) -> list[int]: ...
```

**Rules the codebase enforces:**

1. **No module outside `services/model_router/providers/` imports a provider SDK.** No `import google.genai`, `import openai`, `import anthropic`, `from vllm import ...` anywhere else. A lint rule / import-linter contract fails CI on violation. This is the mechanical guarantee behind "no vendor in the business logic".
2. **Services call the Router by capability, never by provider.** `router.generate(task="clause_rewrite", sensitivity=tier, text=...)` — not `router.generate(model="gemini-flash")`. The task name and sensitivity are the inputs; the model is the Router's decision.
3. **A provider is one file.** Adding OpenAI support = add `providers/openai.py` implementing `ModelProvider`, register it, add a policy rule. Removing a provider = delete the file and the rule. No service changes, no schema changes.
4. **Request/response schemas are provider-neutral.** `GenerateRequest` carries messages, tools, a JSON schema, sampling params, and a `max_cost` / `max_latency` budget — not provider-specific fields. Provider adapters translate to/from their native API.

### Provider packaging

| Package | Contents | Installed |
|---|---|---|
| `legalai-providers-core` | vLLM/SGLang adapter, Ollama/llama.cpp adapter, TEI/Infinity (embed/rerank) adapter, faster-whisper adapter, Kokoro/Piper adapter, and a deterministic "Class A" adapter for rule/classical-ML models | **Always.** This is the product's inference layer. |
| `legalai-providers-external` | Gemini, OpenAI, Anthropic, Bedrock, Vertex, Azure OpenAI adapters (may wrap **LiteLLM** internally — `MODEL_STACK.md`) | **Optional.** An operator opts in. **Excluded from on-prem/air-gapped builds by the SBOM allowlist** (`ARCHITECTURE.md`), so it is not merely disabled but physically absent. |

A deployment with only `-core` installed is fully functional: every feature works, every task has a model. The eval harness reports the quality delta, if any, that `-external` would add for each task — so the decision to install it is data-driven, not assumed.

## Hosting classes (these replace V1's vendor tiers)

There is no "Tier 2 — commercial frontier" any more. Models are classified by **where they run**, not by who sells them:

| Class | Where it runs | Leaves perimeter? | Allowed for | Role |
|---|---|---|---|---|
| **A — Deterministic / CPU** | In-process or a CPU sidecar | No | All sensitivity tiers, air-gapped, edge | Rules, regex, classical ML, small CPU models (deontic Tier-0, clause-type rules, GLiNER, coref). Fast, free, exact. |
| **B — Self-hosted neural** | The deployment's own GPU/CPU (vLLM, SGLang, TEI, faster-whisper, …) | No | **All sensitivity tiers, including `Privileged`. Air-gapped.** | **The default and primary path for every generative and semantic task**: LLM generation, VLM document understanding, embeddings, reranking, ASR, TTS. |
| **C — External provider** | A third party's API | Yes | `Public` / `Internal` only by default; `Confidential` / `Privileged` **only** with explicit per-document org-admin override, enforced in the Router | Optional. Used where an org opts in *and* the eval harness shows a material, task-specific quality/latency gap that self-hosted models don't yet close. Absent entirely in air-gapped builds. |

A document tagged `Privileged` can never be routed to Class C. This is enforced in the Router before a request is dispatched, not as a UI hint (`ARCHITECTURE.md` security section). In an air-gapped build there is no Class C provider to route to at all.

## The routing policy engine

The Router's decision is driven by a **declarative policy**, hot-reloadable, versioned in git (`packages/policies/routing.yaml`), and logged with every call so any routing decision is reproducible.

**Inputs to a routing decision:**

| Input | Source |
|---|---|
| Task type | The calling service (`clause_rewrite`, `timeline_extract`, `risk_analysis`, `qa`, `contextualize`, `entity_resolve`, `verify_nli`, `embed_clause`, `rerank`, `transcribe`, …) |
| Sensitivity tier | The document's ingestion classification (`Public`/`Internal`/`Confidential`/`Privileged`) |
| Required capabilities | e.g. `structured_output`, `vision`, `context>=32k`, `language=de` |
| Latency budget | Interactive (chat) vs. batch (ingestion, eval, training-data labeling) |
| Cost ceiling | Per-request and per-org budget (`BACKEND.md`) |
| Org policy | `model_tier_default`, allowed providers, "never send category X to a third party" |
| Provider health | Live health/queue-depth from `provider.health()` |
| Escalation signal | Confidence/consistency of a cheaper first pass (see below) |

**Policy shape (illustrative):**

```yaml
tasks:
  clause_rewrite:
    default: { class: B, model: "qwen3-8b" }
    escalate_when: "self_consistency < 0.7 or length_tokens > 6000"
    escalate_to:   { class: B, model: "qwen3-32b" }
    class_c_allowed_for: [Public, Internal]     # only if -external installed AND org opted in

  timeline_extract:
    default: { class: B, model: "qwen3-32b", require: [structured_output] }
    on_schema_fail: retry_once_then { class: B, model: "qwen3-235b-a22b" }

  verify_nli:
    default: { class: A, model: "deberta-nli-legal" }   # fully local, no LLM

  qa:
    default: { class: B, model: "qwen3-32b", rag: true }
    escalate_when: "multi_hop or portfolio_scope"
    escalate_to:   { class: B, model: "deepseek-r1-distill-32b" }

fallback_chain: [B, A]     # if the B provider is unhealthy, degrade; never auto-fallthrough to C
```

**Key policy invariants:**

- **The default for every task is Class A or B.** A policy file with no Class C rules is valid and complete.
- **Class C is never in a `fallback_chain`.** A self-hosted provider outage degrades to a smaller self-hosted model or a Class A approximation with a surfaced confidence warning — it does not silently ship data to a third party. Failing over to C requires an explicit, separately-configured `emergency_class_c` opt-in per org.
- **Escalation is task-quality-driven, not vendor-driven.** "Escalate" almost always means "use a bigger *self-hosted* model". Escalating to Class C is a distinct, rarer, opt-in branch.
- **Every routing decision logs** `{task, sensitivity, chosen_provider, chosen_model, policy_version, reason}` to the trace store, joined to `eval_runs`.

### Model selection by task (default policy)

| Task | Default (Class A/B) | Escalation (still Class B unless noted) | Rationale |
|---|---|---|---|
| Plain-English rewrite | Qwen3-8B | Qwen3-32B for long/dense docs | Bounded style-transfer; a small self-hosted model is sufficient |
| Structure/timeline extraction | Qwen3-32B w/ enforced JSON grammar | Qwen3-235B-A22B if schema validation fails twice | Extraction is schema-adherence-sensitive; grammar-constrained decoding (`MODEL_STACK.md`) removes most failures |
| Risk analysis (AI pass) | Qwen3-32B | DeepSeek-R1-Distill-32B for portfolio-level cross-doc risk | Single-clause risk flagging is within a strong 32 B model's reach |
| Q&A / chat | Qwen3-32B, RAG-grounded | DeepSeek-R1-Distill-32B / QwQ-32B for multi-hop portfolio questions | Grounding via RAG reduces reliance on raw model scale |
| Contextualizer / advisory explanation | Qwen3-32B + RAG | Larger self-hosted model for high-stakes `exec`/`lawyer` tone | Matches V1's guardrail-heavy prompt design, now with real retrieved sources |
| Negotiation/drafting suggestions | Qwen3-32B or Devstral-Small | Qwen3-235B-A22B for final-draft polish | Strong instruction-following; open weights are competitive |
| Scanned-document understanding | Qwen2.5-VL-7B | Qwen2.5-VL-32B for degraded scans / complex layout | See `COMPUTER_VISION.md` |
| Embeddings | Qwen3-Embedding-8B (0.6B constrained) | — | Single model covers the retrieval need; no external option needed or better |
| Reranking | Qwen3-Reranker-4B | — | Standard open cross-encoder; no commercial dependency justified |
| NLI faithfulness (Verifier) | Local DeBERTa/ModernBERT NLI head (Class A) | — | This must be local and deterministic — it is a safety gate, not a generation task |
| NER / entity resolution | GLiNER + Legal-BERT head (Class A) | Qwen3-8B for ambiguous entity disambiguation only | Structured extraction doesn't need a general LLM |
| ASR | faster-whisper large-v3-turbo | Parakeet (English throughput) | Self-hosted, no exceptions |
| TTS | Kokoro-82M (Piper air-gapped) | — | Self-hosted, no exceptions |

This table is a starting point. **The eval harness decides whether a model meets the bar for a task** — any change is justified by an eval run (`ARCHITECTURE.md`), not by preference or a vendor benchmark.

### Escalation without a bigger vendor

V1 escalated to Gemini. V2's default escalation ladder is entirely self-hosted:

1. **Class A rule/model** produces an answer + a confidence signal.
2. If low-confidence → **small Class B model** (Qwen3-8B).
3. If still low-confidence, or the task is flagged hard (multi-hop, long, portfolio-scope) → **large Class B model** (Qwen3-32B → 235B-A22B → reasoning model).
4. **Only if** (a) `-external` is installed, (b) the org opted in, (c) the doc is `Public`/`Internal`, and (d) the policy's `class_c_allowed_for` permits it → **Class C**.

Steps 1–3 are the whole product for the on-prem and air-gapped profiles.

## RAG architecture

V1's RAG (`services/contextualizer/rag.py`) is a single hardcoded 28-string list embedded once into an in-memory FAISS index, rebuilt on every process start, used only by the Contextualizer. V2 generalizes retrieval into a shared service used by every agent that needs grounding.

### Corpus composition

| Source | Content | Update cadence |
|---|---|---|
| User document corpus | The org's own uploaded contracts, versioned | Real-time on upload |
| Statutes & regulations | Curated, jurisdiction-tagged statutory text (starting with the jurisdictions V1's hardcoded hints covered: CA landlord/tenant, employment, general contract law — now sourced and cited) | Periodic ingestion pipeline, source-tracked |
| Case law (where licensed) | Precedent excerpts relevant to common clause types | Periodic, license-dependent |
| Public legal ML datasets | **CUAD**, **ContractNLI**, **LegalBench** tasks | Primarily eval (`ARCHITECTURE.md`); secondarily bootstrapping retrieval content |

Every corpus entry carries a **source citation** (statute section, case name, or document+clause ID). The RAG Service refuses to return an uncited passage — closing the gap flagged in V1's `FEATURES.md` (hardcoded hints with no cited authority). Where no confident citation exists, the entry is tagged as a general principle and the generation prompt is told so, rather than a citation being invented.

### Chunking

Hierarchical, clause-aware chunking. The canonical chunk boundary is the **`Clause` object** produced by the NLP pipeline (`NLP.md`), not an arbitrary character window — unifying V1's two divergent implementations (`rewriter.py`'s naive char-window split vs. `timeline.py`'s paragraph/sentence splitter). Clauses are grouped into section-level and document-level summaries for coarse-to-fine retrieval.

### Hybrid retrieval

1. **Dense** — self-hosted embeddings (Qwen3-Embedding / BGE-M3, served by TEI) in Qdrant; cosine similarity over clause- and section-level vectors.
2. **Sparse** — BM25 (shipped in Phase 3), with SPLADE (learned sparse) as a Class-B upgrade — catches exact defined-term / statute-citation matches dense retrieval misses.
3. **Graph-grounded (GraphRAG)** — traversal of the Knowledge Graph (`KNOWLEDGE_GRAPH.md`) from query entities to connected clauses/obligations/statutes.
4. **Fusion + reranking** — candidates merged via reciprocal rank fusion (RRF, k=60), then reranked with a self-hosted cross-encoder (Qwen3-Reranker / bge-reranker-v2-m3, served by TEI).
5. **Citation-grounded generation** — the prompt requires every factual claim to reference a retrieved chunk's citation ID; the Verifier agent (`AGENTS.md`) checks this via the local NLI faithfulness head.

This replaces V1's fallback behaviour (`get_rag_hints()` silently falling back to a static per-contract-type dict) with three independent retrieval strategies to fall back across before an explicit "not enough grounded information — verify locally" response, which the UI surfaces honestly.

**Current state (Phase 5):** dense (self-hosted — TEI/`bge-m3` on the GPU when the `gpu` compose profile is up, else in-process `sentence-transformers`, else the Class-A hashing embedder) + sparse (BM25) + GraphRAG hits fused via RRF, then reranked (TEI/`bge-reranker-v2-m3` → in-process cross-encoder → Class-A lexical). GraphRAG fusion is wired into the Clause Research agent; the Contextualizer route wiring is a follow-up. The Verifier's faithfulness step is still the honestly-labelled lexical-overlap stand-in — the real local NLI head is Phase 6. Qdrant is not yet used (the corpus is small; FAISS in-process). See `ROADMAP.md`.

## Prompt and version governance

- Prompts live as versioned templates in `packages/prompts`, not string literals scattered across service files.
- Every generation call logs prompt version + provider + model version, joined to `eval_runs` so a quality regression traces to a specific change.
- **No prompt, model, or provider swap ships without a passing eval run** against the regression suite (`ARCHITECTURE.md`).
- The routing policy (`packages/policies/routing.yaml`) is versioned and eval-gated the same way — changing which model serves a task is a reviewed, tested change.

## Cost and latency governance

- Class A/B (self-hosted) is the default for **all** sensitivity levels and the entire task volume. Per-request cost is bounded by infrastructure the platform controls, not a metered API.
- Class C, where enabled at all, is metered per-org with a hard configurable cap (`BACKEND.md` rate limiting), and every Class C call is itemized in the audit log with the reason the policy chose it.
- The observability stack (`MODEL_STACK.md`) reports cost-per-request by hosting class and by task, so the (small, by design) Class C spend is always visible and attributable.
