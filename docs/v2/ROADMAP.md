# Roadmap

Phased delivery plan from V1's current production state to a **fully self-hosted legal-AI platform**. Each phase leaves the system deployable — V1's endpoints keep serving throughout (`ARCHITECTURE.md`'s migration path), so this is an incremental cutover, not a rewrite-and-replace. Durations are rough sizing (in sprints, small dedicated team), not commitments.

## The through-line

Every phase moves inference *toward* the organization's own hardware and *away* from any external dependency:

```
V1:        100% Gemini, no fallback
Phase 1-4: Gemini for generation; local rules/classical-ML for structure
Phase 5:   Provider-agnostic Router; embeddings/rerank self-hosted ON A REAL TEI/GPU  ← WE ARE HERE
           deployment; Ollama (Qwen3-8B) serving generation; Gemini optional plugin
Phase 6:   Self-hosted LLM generation is the default (GPU big enough for the 32B class);
           Gemini removed from the default path
Phase 7:   On-prem + air-gapped builds; commercial-provider package excludable entirely
Phase 8+:  Portfolio intelligence, in-house trained models, research track — all on self-hosted infra
```

The old roadmap put "GPU Upgrade" *last*, as a quality top-up on a Gemini-based product. **That is inverted here.** Self-hosting is the spine. GPU acquisition (Phase 6) is the pivotal unlock — the point at which the strongest model for every task becomes one we run — not an optional epilogue.

## GPU requirement by phase

**One GPU acquisition (Phase 6) unlocks everything downstream — it is not an escalating requirement, and it can be rented rather than owned.**

| Phase | GPU on *our* side? | Notes |
|---|---|---|
| **0–5** | **No** (a GPU helps but isn't required) | CPU rules / classical ML / hashing embeddings; generation via an external plugin or a small served model. **Update:** the dev box now has an RTX A4000 (16 GB), so Phase 5's serving layer is real — Ollama Qwen3-8B + TEI bge-m3 / bge-reranker-v2-m3 on the GPU. The *architecture* stays GPU-free (Class-A fallbacks keep every path working with nothing served). |
| **6 — Self-hosted LLM generation** | **Yes — a bigger GPU than the current 16 GB** | The A4000 (16 GB) already serves the constrained profile (Qwen3-8B, 4-bit 14B) **and** every fine-tune in the plan (Legal-BERT, small-LLM LoRA via Unsloth). Serving the **32B-class default** via vLLM needs ~24 GB (one 3090/4090/A5000/A6000, or a rented GPU box). Until that, the Qwen3-8B serve + the Phase 5 interim stand. A **cloud/rented GPU** fully satisfies this phase. |
| **7 — On-prem / air-gapped deployment** | **No** | Packaging (Zarf/OpenTofu/Harbor/SBOM), collapsed data layer, durable execution, Memory Service, frontend SPA — all CPU/infra. A *customer* running air-gapped supplies their own GPU for self-hosted generation, or accepts the constrained-profile CPU small-model quality; that is their hardware, not the platform team's. |
| **8 — Portfolio intelligence & research** | **Partially — reuses the Phase 6 GPU** | CPU: Risk Scoring (LightGBM), Document Sensitivity (classical), the Simulation agent, portfolio-agent baselines, bitemporal graph, `NOVELTY.md` #2 and #5. Same GPU as Phase 6: the fine-tuned clause classifier, the Legal Clause Embedding contrastive fine-tune, and the training steps for `NOVELTY.md` #1 and #3. |
| **9 — Scale & enterprise hardening** | **No new need** | SOC 2, GDPR workflows, cost/latency tuning, multi-tenant scale. "GPU autoscaling" here means *operating* the Phase 6 pool, not acquiring more. |

## Phase mapping from the previous roadmap

| Previous phase | This roadmap |
|---|---|
| Phase 0 — V1 Hardening | Phase 0 (unchanged) |
| Phase 1 — Foundation Re-platform | Phase 1 (unchanged; Model Router re-scoped as the provider-agnostic seam) |
| Phase 2 — Core AI Pipeline Buildout | Phase 2 (unchanged) |
| Phase 3 — Knowledge Graph & GraphRAG | Phase 3 (unchanged) |
| Phase 4 — Agentic Orchestration MVP | Phase 4 (unchanged) |
| Phase 5 — Portfolio Intelligence & Research | **Phase 8** (moved later — it depends on self-hosted training infra) |
| Phase 6 — Scale, Memory, Enterprise Hardening | **Phase 9** |
| Phase 7 — GPU Upgrade | **Phase 6** (moved *earlier* and made the spine) |
| *(new)* | **Phase 5** — Provider Abstraction Hardening |
| *(new)* | **Phase 7** — Deployment Profiles: On-Prem & Air-Gapped |

Code docstrings and `LEARNING_LOG.md` entries that reference "Phase 7 (GPU Upgrade)" now correspond to **Phase 6** here. `LEARNING_LOG.md` is an append-only journal and is not rewritten; this table is the reconciliation.

---

## Phase 0 — V1 Hardening (prerequisite, ~2-4 sprints) — ✅ Complete

Complete the hardening scoped in `docs/v1/ROADMAP.md`/`TASKS.md` (tests, CORS fix, secrets hygiene, config correctness) before layering V2 on top.

**Exit criteria**: V1's P0/P1 tasks complete — CI running, CORS fixed, secrets rotated, config centralized. — **met.**

## Phase 1 — Foundation Re-platform (~4-6 sprints) — ✅ Complete (pragmatic slice)

Stand up the V2 data layer and service skeleton without changing user-facing behaviour. **Delivered**: Postgres + Redis (not the full 6-store polyglot stack — the rest deferred to when RAG/KG need them), org-scoped API-key auth default-off, **a Model Router pass-through wrapper** (`app/services/model_router.py`), and document persistence replacing the in-memory dict. **Not delivered**: OpenTelemetry/Langfuse/Prometheus, Kubernetes/OpenTofu/Helm, the monorepo restructure, an actual API Gateway service boundary — deliberately deferred.

**Re-scope note (this revision):** the Model Router shipped here is now understood as the **provider-agnostic seam** described in `AI_STACK.md`, not a "route everything to Gemini" shim. It currently has one provider (Gemini). Phase 5 turns it into the real thing. Nothing built here needs to be undone.

**Exit criteria**: V1 feature parity on the V2 data/service foundation, authenticated (off by default), observable via structured logging, zero in-memory-only state. — **met at reduced scope.**

## Phase 2 — Structured Understanding: CPU Pipeline (~6-10 sprints) — ✅ Complete (CPU slice; GPU items → Phase 6)

Build the pipelines that turn flat text into structured `Clause` objects. Re-planned mid-phase once hardware reality was checked — the dev machine has no discrete GPU, ruling out vLLM/VLMs/fine-tuning. Every stage was implemented as a genuine, tested, CPU-only equivalent; the GPU-dependent versions moved to Phase 6.

- **CV pipeline** (`COMPUTER_VISION.md`): OpenCV quality triage (blur/skew) and geometric redaction detection. Layout/table/signature analysis → Phase 6.
- **NLP pipeline** (`NLP.md`): segmentation, defined-term extraction (doubling as party/entity ID), cross-references, regex money/jurisdiction entities, rule-based deontic tagging with optional LLM escalation, `dateparser` temporal normalization, keyword-taxonomy clause classification, ambiguity detection, heuristic coref stand-in — all producing the canonical `ClauseObject`. Fine-tuned NER/classifier/deontic models and real coref → Phase 6.
- **Model Router**: no self-hosted model yet (needs Phase 5/6); generation still routes to Gemini.
- **Eval harness**: lightweight custom harness (not yet Ragas/Inspect AI) against a 15-example hand-curated gold set, wired as a CI gate.

**Exit criteria**: every uploaded document produces a structured `ClauseObject` graph, not just flat text — **met.** "At least one production task fully served by a self-hosted model" — **deferred to Phase 6.**

## Phase 3 — Knowledge Graph & Hybrid RAG (~6-8 sprints) — ✅ Complete (pragmatic slice)

Memgraph needs no GPU, so this phase's infrastructure is real. Scoped down: entity resolution via string similarity rather than embedding clustering; relation extraction derived from Phase 2's structured output rather than a separate model; dense embeddings via **Gemini's API** rather than self-hosted (self-hosting the embedding model → **Phase 5**).

- Knowledge Graph Service + Memgraph deployed; entity resolution (`difflib` context-similarity) and relation extraction running via idempotent `POST /api/kg/ingest`.
- Hybrid RAG (dense + sparse, RRF fusion) replaces V1's hardcoded 28-string knowledge base; a real cited statute/regulation corpus ingested, citations only where confidently verifiable.
- Contextualizer migrated onto hybrid RAG with `[N]`-style inline citations + a fabricated-citation validator.
- **Live bug fixed**: V1's `text-embedding-004` default had been silently 404ing against the current Gemini API; updated to `gemini-embedding-001`. Dense retrieval had effectively been BM25-only until this was caught.
- **Not yet done**: GraphRAG hits not fused into the Contextualizer's retrieval alongside BM25/dense; bitemporal graph versioning; self-hosted embeddings/reranker.

**Exit criteria**: Contextualizer answers cite real, retrievable sources — **met, verified live.** GraphRAG "what else references this term" query — **met** via `POST /api/kg/query`.

## Phase 4 — Agentic Orchestration MVP (~8-12 sprints) — ✅ Complete (backend MVP)

A fixed LangGraph pipeline wiring Phases 0-3 into one verified agent workflow.

- LangGraph orchestration deployed: Extraction → Risk & Compliance → Clause Research → Summary → Verifier as a fixed sequence. **Not done**: a dynamic Orchestrator/Planner agent; a durable-execution engine (runs synchronously in-request — acceptable at current runtimes, revisit in Phase 7).
- Verifier ships citation check + KG consistency check (both real); the NLI faithfulness check is an honestly-labelled lexical-overlap stand-in — real local NLI head → **Phase 6**.
- Memory Service — **not started** → Phase 7.
- Frontend Agent Trace Viewer — **not started**; the whole project is backend-only through Phase 4 → Phase 7.
- `agent_traces` persistence — **done**, one row per step, verified live.

**Exit criteria**: a full single-document analysis runs as an auditable agent workflow with every claim citation-checked before reaching the UI — **met at the backend level** (no UI yet — Phase 7).

---

## Phase 5 — Provider Abstraction Hardening (~4-6 sprints) — 🟢 Substantially complete

**This phase makes the architecture genuinely provider-agnostic and removes every external dependency *except* large-LLM generation quality.** The code core came first (no GPU needed); the serving layer landed once a GPU (RTX A4000, 16 GB) became available.

**Shipped (code):** the `ModelProvider` interface, the `providers-core` / `providers-external` packaging split (`google-genai` removed from `requirements.txt`), the import-linter contract (CI-gated), the declarative routing-policy engine (`app/policies/routing.yaml`) with Class A/B/C and Class-C gating, per-call routing-decision logging, and **removal of the Gemini embedding dependency from the RAG path**. Verified in a fresh venv with no `google-genai` (`LEARNING_LOG.md` #18).

**Shipped (serving + observability, `LEARNING_LOG.md` #19):** a `gpu` docker-compose profile + `scripts/bootstrap_selfhosted.sh` running **Ollama (Qwen3-8B)** for generation and **TEI on GPU** for **bge-m3** embeddings and **bge-reranker-v2-m3** reranking; a `local-rerank-remote` provider (`OpenAICompatProvider` rerank role) for TEI's `/rerank`; `GET /api/models/status`; `model_calls` routing-decision persistence + an OpenTelemetry scaffold (`app/observability.py`); and the eval seed — Inspect-AI suite (`app/eval/inspect_tasks.py`), CUAD / ContractNLI loaders, and the self-hosted-vs-external **delta report**. Full suite 110 pass + 1 skip, green with nothing served.

**Still open:** an actual observability collector wired to the OTel scaffold (a `docker-compose.observability.yml` — Langfuse / SigNoz / Grafana LGTM); promptfoo; ASR/TTS providers (deferred until a feature needs them).

**Model Router → the real provider interface** (`AI_STACK.md`)
- [x] Define the `ModelProvider` protocol (`generate`, `embed`, `rerank`, `describe`, `is_available`) and provider-neutral request/response schemas. `generate_structured`/`transcribe`/`synthesize`/`health` reserved, not yet needed.
- [x] Split providers into core (self-hosted adapters) / external (commercial); `-external` is an optional install (`requirements-external.txt`).
- [x] Add the **import-linter CI contract**: nothing outside the provider package may import a model SDK (`tests/test_provider_isolation.py` + `.importlinter`).
- [x] Build the **declarative routing-policy engine** (`app/policies/routing.yaml`): task × sensitivity × capability → ordered chain, self-hosted-only fallback chains, conditional Class C. `emergency_class_c` per-org opt-in: not built (no multi-tenant policy layer yet).
- [x] Log `{task, sensitivity, provider, model, reason, candidates}` on every routing decision (`router.py` + `model_router/telemetry.py` → `model_calls`). Join to `eval_runs`: deferred (no `eval_runs` table yet).
- [x] Re-express hosting as **Class A / B / C**, not vendor tiers, throughout config and code.

**Self-host everything that isn't a large LLM** (all CPU- or small-GPU-feasible)
- [x] Deploy **TEI** serving a self-hosted embedding model (**BGE-M3** on the GPU, `gpu` compose profile). **Gemini embedding dependency removed from the RAG path** — the phase's key deliverable.
- [x] Deploy a self-hosted reranker (**bge-reranker-v2-m3** on TEI) and wire it into RRF fusion (`local-rerank-remote` provider).
- [~] Fuse GraphRAG hits into hybrid retrieval — done for the Clause Research agent; the Contextualizer route wiring is a follow-up (needs org context threaded to `explainer`).
- [ ] Add **faster-whisper** (ASR) and **Kokoro/Piper** (TTS) providers — deferred until an audio feature exists.
- [x] Ship an **Ollama**-served small LLM (**Qwen3-8B**) as the local default (`scripts/bootstrap_selfhosted.sh`, `.env.example`).

**Eval harness upgrade**
- [~] Adopt **Inspect AI** as the suite backbone — seed task shipped (`app/eval/inspect_tasks.py`); keep the hand-curated gold set as the fast pre-merge check; **promptfoo** not yet added.
- [~] Point every eval judge at a self-hosted model — the delta report can use `local-llm`; a dedicated judge harness is future work.
- [x] Add the **self-hosted-vs-external delta report** (`app/eval/delta_report.py`): per task, measure what Class C would add. Gates future Class C decisions.

**Exit criteria**: the Model Router is provider-agnostic and passes the import-linter contract ✅; embeddings and reranking are self-hosted on a real TEI/GPU deployment ✅; ASR/TTS N/A; the *only* task routed to a commercial API by default is large-LLM text generation ✅; a contributor can run the entire product locally with zero credentials ✅. Remaining: an observability collector wired to the OTel scaffold; promptfoo.

**Can the product run after Phase 5 with no GPU and no external API?** Yes — end to end. Every task has a working model: structure/RAG/KG/agents are CPU-fine already (Phases 2–4), and embeddings/rerank/ASR/TTS become CPU-served here. LLM generation falls to a CPU-served small model (Qwen3-4B via Ollama/llama.cpp). The honest caveat is *quality and latency*, not capability: CPU-served 4B generation is noticeably weaker and slower than a GPU-served 32B or Gemini. So there are two ways to run between Phase 5 and Phase 6 — (a) keep Gemini as an opt-in Class C plugin for generation quality (cloud/hybrid profiles), or (b) accept the CPU small-model quality for a genuinely disconnected pilot. Nothing is *blocked*; Phase 6 is a quality/latency upgrade on the generative path, and the point at which the disconnected profile reaches production-grade generation.

## Phase 6 — Self-Hosted LLM Generation: the GPU unlock (~8-12 sprints)

**The pivotal phase.** GPU hardware becomes available and self-hosted generation becomes the default for every task. **Partly underway:** the dev box has an RTX A4000 (16 GB), which already runs the Phase 5 serving layer (Ollama Qwen3-8B + TEI bge-m3 / bge-reranker-v2-m3) — that covers the *constrained profile* and every fine-tune in the plan. The remaining Phase 6 hardware ask is a larger / rented GPU (1–2× 24–48 GB) to serve the **32 B default**. A quantized Qwen3-32B (AWQ/GPTQ 4-bit) fits ~24 GB.

**Model serving**
- [ ] Deploy **vLLM** (and evaluate **SGLang** for the agent prefix-cache workload) on the GPU pool.
- [~] Serve **Qwen3-32B** (quantized) as the default generation model — **Qwen3-8B is served now** via Ollama (constrained profile); the 32 B default and a reasoning model (**DeepSeek-R1-Distill-32B** / **QwQ-32B**) for flagged-hard tasks need the bigger GPU.
- [ ] Serve **Qwen2.5-VL-7B/32B** for scanned-document understanding.
- [x] Move the self-hosted embedding/reranker to GPU-served (**TEI on GPU**) for latency — landed in the Phase 5 bootstrap.

**Progressive task cutover — each A/B-gated against the Gemini baseline before it becomes default**
- [ ] Plain-English rewrite → Qwen3-8B/32B.
- [ ] Structure/timeline extraction → Qwen3-32B with grammar-constrained JSON (xgrammar).
- [ ] Q&A / chat → Qwen3-32B + RAG; reasoning model for multi-hop.
- [ ] Risk analysis AI pass → Qwen3-32B.
- [ ] Contextualizer advisory → Qwen3-32B + RAG.
- [ ] Deontic/clause-classifier LLM escalation → self-hosted.

**GPU-dependent CV/NLP models** (from Phase 2's deferral list)
- [ ] Replace OpenCV quality triage + "tables are text blocks" with **Docling** + **Qwen2.5-VL** + **Table Transformer** (or PaddleOCR PP-Structure) for real layout/table extraction; keep Tesseract/quality-triage as the clean-PDF fast path.
- [ ] Add **olmOCR / Qwen2.5-VL** as the confidence-gated OCR escalation (replaces the previously-planned commercial Document AI fallback as the *default*).
- [ ] Fine-tune **InLegalBERT/ModernBERT** NER for parties/dates/money/jurisdictions (via **Unsloth**); compare against the regex+defined-term baseline before making it primary.
- [ ] Integrate **GLiNER** for zero-shot entity types and **maverick-coref** for real coreference (replacing `app/services/nlp/coref.py`'s heuristic).
- [ ] Run the **weak-supervision-then-distill** pipeline for the deontic tagger — teacher is a self-hosted Qwen3-235B (or 32B) via **distilabel**, *not* a frontier API; student is a fast CPU tagger.
- [ ] Fine-tune the clause/contract-type classifier; eval against real **CUAD**; keep the rule base as a Tier-0 pre-filter.

**Verifier**
- [ ] Ship the real **NLI faithfulness head** (local DeBERTa/ModernBERT entailment model, Class A), replacing Phase 4's lexical-overlap stand-in.

**Eval**
- [ ] Integrate **LegalBench / CUAD / ContractNLI / MAUD** corpora into the Inspect AI suite; track the self-hosted default against them continuously.
- [ ] For every cutover: the self-hosted model must meet or beat the Gemini baseline on the task's eval before it becomes default. A fine-tuned/self-hosted model is not *assumed* better — this phase proves it.

**Exit criteria**: every core task (rewrite, extraction, Q&A, risk, contextualize, verify) is served by a **self-hosted model at or above the previous Gemini baseline**. Gemini is removed from the *default* routing policy entirely — it remains only as an optional Class C escalation an org can enable for `Public`/`Internal` documents, and the delta report shows what that escalation is worth. The product now runs end-to-end with no external API call.

## Phase 7 — Deployment Profiles: On-Prem & Air-Gapped (~10-14 sprints)

With generation self-hosted (Phase 6), the product can now ship disconnected. This phase makes on-prem and air-gapped *supported profiles*, not heroics.

**Build & supply chain**
- [ ] Produce on-prem/air-gapped builds with `legalai-providers-external` **excluded**; enforce with an **SBOM allowlist** that fails the build if a commercial-provider SDK is present.
- [ ] **Zarf** packaging of the full application (images + charts + manifests + model weights + seed corpus) into one installable artifact.
- [ ] Model weights as signed **KitOps ModelKit** OCI artifacts through **Harbor**; no `pip`/`huggingface-cli` on the target.
- [ ] **OpenTofu** (not Terraform) for all IaC; Helm + Kustomize overlays per profile; **k3s** single-node target for smaller on-prem racks.
- [ ] cosign signing + Syft SBOM + Trivy/Grype scanning for every image and model artifact.
- [ ] Egress proxy / network policy for the hybrid profile: deny all outbound except configured provider endpoints; log every byte (`audit_log.egress_target`).

**Collapsed data layer** (the "one fewer service to operate" profile)
- [ ] Support **pgvector + pgvectorscale** as a Qdrant substitute; **Apache AGE** or **KùzuDB** as a Memgraph substitute; **LanceDB** embedded for the laptop profile; filesystem object storage; Postgres-backed event queue.
- [ ] Profile-select the data layer via Helm values; the same application code runs against either.

**Durable execution & Memory Service** (deferred from Phase 4)
- [ ] Introduce a durable-execution engine — **DBOS** (library, Postgres-backed) as the default so no new cluster is needed; **Hatchet** for mid-scale; **Temporal** only for the large multi-tenant cloud profile. The `app/agents/graph.py` abstraction stays engine-agnostic.
- [ ] Build the Memory Service: session tier (Redis), episodic tier (Postgres + vector store), consolidation worker (session/episodic → semantic) with the privacy-tier gate.
- [ ] Dynamic Orchestrator/Planner agent (replacing the fixed Phase 4 sequence) once a durable engine makes multi-path workflows safe to run.

**Frontend SPA** (deferred from Phase 4 — a large workstream)
- [ ] Scaffold Next.js + TypeScript; generate the API client from the OpenAPI schema.
- [ ] Workspace + Document Analyzer (V1 parity), Agent Trace Viewer (real-time via session WebSocket), human-in-the-loop review queue UI.
- [ ] **Provider & Model admin**: an org admin sees which models serve which tasks, the eval scores behind the routing policy, and the delta report; toggles Class C per task/tier (where the build includes it).
- [ ] **Model status panel**: self-hosted model health, queue depth, latency — the operator's view of their own inference layer.
- [ ] Fully self-hosted frontend assets (fonts, analytics via Plausible) so a `Privileged` page has no third-party origin.
- [ ] Introduce `/api/v2/*` session/document-first endpoints; feature-flag per org.

**Exit criteria**: a genuine air-gapped install (Zarf artifact → disconnected k3s cluster → working product, verified with no network) validated with a pilot customer; a collapsed-data-layer on-prem install validated; the frontend SPA at V1 feature parity plus the Agent Trace Viewer.

## Phase 8 — Portfolio Intelligence & Research Features (~10-14 sprints, research-gated)

Now that self-hosted training and serving infra exists (Phase 6), the in-house models and research track become tractable.

**In-house models** (`DEEP_LEARNING.md`)
- [ ] Curate training data (org corpora with consent + CUAD/ContractNLI); **distilabel** weak-supervision pass with a **self-hosted teacher**; legal-expert review in **Argilla**.
- [ ] Train the **Risk Scoring Model** (LightGBM, CPU — blocked on labelled data, not hardware); integrate SHAP explainability.
- [ ] Finalize the fine-tuned **clause/contract-type classifier** and **NER head**; eval-gate promotion.
- [ ] **Document Sensitivity Classifier** — try classical (TF-IDF + linear) first; only fine-tune a transformer if that underperforms.
- [ ] **Legal Clause Embedding Model** — contrastive fine-tune (`NOVELTY.md` #3) with hard-negative mining.
- [ ] **MLflow** registry + **DVC** data versioning; eval-gated model promotion wired into CI/CD; **model cards** for every trained model.

**Portfolio agents** (`AGENTS.md`, `KNOWLEDGE_GRAPH.md`)
- [ ] **Cross-Document Consistency** agent (embedding-similarity baseline → learned `NOVELTY.md` #1).
- [ ] **Simulation** agent (deterministic discrete-event baseline → Monte-Carlo `NOVELTY.md` #2).
- [ ] **Negotiation/Drafting** agent — static org-configured preferences first; the learned playbook (`NOVELTY.md` #4) once redline history exists.
- [ ] **Bitemporal** graph versioning (valid time / transaction time) — the Phase 3 gap; needed for simulation.
- [ ] Negotiation Studio frontend (Yjs collaborative editing); Risk Dashboard spider chart (closes the V1 README promise).

**Research track** (`NOVELTY.md`) — each idea independently gated; prototype + benchmark + (if pursued) formal prior-art search
- [ ] Ideas #1–#5: literature review, architecture design, and CPU-only components proceed anytime; GPU training steps (GAT #1, contrastive embedding #3) use the Phase 6 infra.
- [ ] Target a benchmark contribution and/or a workshop paper (NLLP @ *ACL, JURIX, ICAIL) for any idea that validates — see `NOVELTY.md`'s publication strategy.

**Exit criteria**: portfolio-level contradiction detection and obligation-timeline simulation are live (established-technique versions first; novel-mechanism versions only after their research gate); at least one in-house trained model in production at or above its rule-based baseline; at least one `NOVELTY.md` idea has a validated prototype with benchmark results.

## Phase 9 — Scale, Memory Maturity & Enterprise Hardening (~ongoing)

- [ ] Semantic and procedural memory tiers completed; consolidation jobs live with privacy-tier gating enforced.
- [ ] Multi-tenant cloud scale: Qdrant sharding, per-org graph partitioning, GPU autoscale on queue depth, Postgres read replicas; **Temporal** adopted for the cloud profile if DBOS/Hatchet hit a ceiling.
- [ ] **SOC 2 Type II** readiness and **GDPR** data-subject workflows (export/delete per org) as a formal compliance program; air-gapped profile positioned for customers with data-residency / classified-handling mandates.
- [ ] Full cost/latency optimization pass across the routing policy using a quarter of production eval + cost data; right-size the self-hosted model fleet; quantization / speculative-decoding / batching tuning.
- [ ] V1's `/api/v1/*` deprecation timeline finalized once `/api/v2/*` has full parity plus the new capabilities.
- [ ] Quarterly drift-monitoring review of production eval scores against the gold benchmark.

**Exit criteria**: at least one production customer per deployment profile (cloud / hybrid / on-prem / air-gapped); compliance program formally underway; V1 API sunset scheduled; the routing policy is cost/latency-optimized on real data.

## Cross-cutting, all phases

- **Nothing merges without the eval gate** (from Phase 2 onward) — and, from Phase 5, that includes routing-policy and provider changes.
- **Every sensitive-tier code path change gets a security review**, with special attention to anything touching Class C egress.
- **Every phase preserves V1's live traffic** — this is an additive migration.
- **The import-linter contract** (from Phase 5) is a permanent CI gate: no vendor SDK outside the provider package, ever.
