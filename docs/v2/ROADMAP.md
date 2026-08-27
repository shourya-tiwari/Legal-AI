# Roadmap

Phased delivery plan from V1's current production state to the full V2 vision. Each phase leaves the system deployable — V1's endpoints keep serving throughout (`ARCHITECTURE.md`'s migration path), so this is an incremental cutover, not a rewrite-and-replace. Durations are rough sizing (in sprints, assuming a small dedicated team), not commitments.

## Phase 0 — V1 Hardening (prerequisite, ~2-4 sprints) — ✅ Complete
Complete the hardening work already scoped in `docs/v1/ROADMAP.md`/`TASKS.md` (tests, CORS fix, secrets hygiene, config correctness) before layering V2 on top. Building agents and a knowledge graph on top of an untested, unauthenticated, in-memory-storage backend would compound risk rather than reduce it.

**Exit criteria**: V1's P0/P1 tasks (docs/v1/TASKS.md) are complete: CI running, CORS fixed, secrets rotated, config centralized. — met.

## Phase 1 — Foundation Re-platform (~4-6 sprints) — ✅ Complete (pragmatic slice)
Stand up the V2 data layer and service skeleton without changing user-facing behavior yet. **Delivered scope** (approved via an explicit scoping decision — see `docs/v2/TASKS.md` for the item-by-item breakdown): Postgres + Redis (not the full 6-store polyglot stack — Qdrant/Memgraph/Redpanda/MinIO deferred to Phase 3 when RAG/KG need them), org-scoped API-key auth default-off (not full user/role/session auth — no login UI exists yet), a Model Router pass-through wrapper, and document persistence replacing the in-memory dict. **Not delivered**: OpenTelemetry/Langfuse/Prometheus/Grafana, Kubernetes/Terraform/Helm, the monorepo restructure, and an actual API Gateway service boundary (still one FastAPI process) — all deliberately deferred, not abandoned.

**Exit criteria**: V1 feature parity, now running on the V2 data/service foundation, authenticated (capability exists, off by default), observable via structured logging (not yet full tracing), with zero in-memory-only state. — met at the reduced scope above.

## Phase 2 — Core AI Pipeline Buildout (~6-10 sprints) — ✅ Complete (CPU-only slice; GPU-dependent items moved to new Phase 7)
Build the pipelines that turn flat text into structured understanding. **Scope note**: this was re-planned mid-phase once hardware reality was checked — the dev machine has no discrete GPU (Intel integrated graphics, ~7.75GB RAM), which rules out vLLM, LayoutLMv3, Donut, Table Transformer, YOLOv8, and any fine-tuning. Rather than skip Phase 2, every stage was implemented as a genuine, tested, CPU-only equivalent, and the originally-scoped GPU versions became **Phase 7 (GPU Upgrade)**, targeting an RTX 4050 (6GB VRAM) — confirmed sufficient for everything except full-precision 8B+ LLM serving.
- CV pipeline (`COMPUTER_VISION.md`): quality triage (OpenCV blur/skew, not a trained model) and redaction detection (geometric heuristic, not a trained model) — layout analysis/table extraction/signature detection deferred to Phase 7.
- NLP pipeline (`NLP.md`): segmentation, defined-term extraction (doing double duty as party/entity identification), cross-references, regex-based money/jurisdiction entities, rule-based deontic tagging with optional Gemini escalation, dateparser-based temporal normalization, keyword-taxonomy clause classification with optional Gemini escalation, ambiguity detection, and a heuristic (explicitly-not-real) coreference stand-in — all producing the canonical `ClauseObject`. Fine-tuned NER/classifier/deontic models and real coreference (fastcoref) deferred to Phase 7.
- Model Router: no open-weight model deployed yet (needs Phase 7's GPU); all traffic still routes to Gemini as before.
- Eval harness: a lightweight custom harness (not Ragas) against a 15-example hand-curated gold set, wired as a CI-gating pytest test — real Ragas + CUAD/ContractNLI integration is separate future work.

**Exit criteria**: every uploaded document produces a structured `ClauseObject` graph, not just flat text — met. "At least one production task fully served by an open-weight model" — deferred to Phase 7 (no open-weight model runs on this hardware yet; the rule-based/Gemini-escalation split is the interim answer to the same underlying goal of not paying for a frontier model call on every task).

## Phase 3 — Knowledge Graph & GraphRAG (~6-8 sprints) — ✅ Complete (pragmatic slice)
Unlike Phase 2, Memgraph itself needs no GPU — this phase's infrastructure is real, not a CPU stand-in. What's scoped down instead: entity resolution via string similarity rather than embedding clustering, relation extraction derived directly from Phase 2's already-structured output rather than a separate model, and dense embeddings via Gemini's API rather than self-hosted BGE-M3 (that part *is* deferred to Phase 7, alongside the reranker and SPLADE).
- Knowledge Graph Service and Memgraph deployed (`KNOWLEDGE_GRAPH.md`); entity resolution (`difflib` context-similarity) and relation extraction (derived from Phase 2's `ClauseObject`) running via `POST /api/kg/ingest`, which is idempotent and doubles as the backfill mechanism for any existing document.
- Hybrid RAG (dense + sparse, not yet + graph — see below) replaces V1's hardcoded 28-string knowledge base (`AI_STACK.md`); a real, cited statute/regulation corpus ingested for the jurisdictions V1 already hinted at, with citations only where confidently verifiable (most entries remain deliberately uncited general principles).
- Contextualizer feature migrated onto real hybrid RAG with `[N]`-style inline citations and a citation validator that flags fabricated citation numbers.
- **Found and fixed a live bug while verifying this phase end-to-end**: V1's embedding model default (`text-embedding-004`) had been silently 404ing against the current Gemini API; updated to `gemini-embedding-001` — dense retrieval had effectively been BM25-only (via graceful RRF degradation) until this was caught.
- **Not yet done**: GraphRAG hits (from `/api/kg/query`) are exposed as their own endpoints but not yet fused into the Contextualizer's hybrid retrieval alongside BM25/dense — a real remaining gap, not a scope simplification; bitemporal graph versioning is also not implemented.

**Exit criteria**: Contextualizer answers cite real, retrievable sources — met, verified live against real Gemini. "A GraphRAG query can answer 'what else in this portfolio references this defined term'" — met via `POST /api/kg/query`, verified live against real Memgraph (including cross-document portfolio-linked results via `SAME_AS`), though not yet fused into the Contextualizer's own retrieval path.

## Phase 4 — Agentic Orchestration MVP (~8-12 sprints)
- LangGraph + Temporal orchestration layer deployed (`AGENTS.md`); Orchestrator, Extraction, Risk & Compliance, Clause Research, and Verifier agents implemented first (the core loop needed for a single-document analysis with citation-checked output).
- Memory Service (session + episodic tiers first; semantic/procedural deferred to Phase 6) deployed.
- Frontend Agent Trace Viewer shipped (`FRONTEND.md`) so agent behavior is inspectable from day one, not bolted on later.
- `/api/v2/*` endpoints introduced (session/document-first model); frontend begins dual-running against v1 and v2 APIs behind a feature flag.
- Human-in-the-loop review queue live for low-confidence/`Privileged`-tier outputs.

**Exit criteria**: a full single-document analysis (extract → risk → research → verify) runs as an auditable agent workflow, with every claim citation-checked before reaching the UI.

## Phase 5 — Portfolio Intelligence & Research Features (~10-14 sprints, research-gated)
- Cross-Document Consistency and Simulation agents implemented, drawing on the Knowledge Graph's portfolio-linking (Phase 3) and bitemporal modeling.
- Deep-learning models trained and promoted per `DEEP_LEARNING.md` (Risk Scoring Model, Clause Type Classifier, Deontic Tagger distillation, Redline Acceptance Predictor).
- **Research spikes** for `NOVELTY.md` ideas begin here, each gated independently: a research spike produces a working prototype + benchmark results + (if pursued further) a formal prior-art search commissioned before any patent-related decision or public disclosure. No novelty-track item ships as a customer-facing feature until it has passed the same eval-gating bar as any other model (`ARCHITECTURE.md`).
- Negotiation Studio (frontend) and the Negotiation/Drafting agent ship, initially without the learned playbook (idea #4), using static org-configured preferences; the learned version follows once sufficient redline history exists and the research spike validates the approach.

**Exit criteria**: portfolio-level contradiction detection and obligation-timeline simulation are live features (established-technique versions first; novel-mechanism versions only after their research gate passes); at least one `NOVELTY.md` idea has a validated prototype with benchmark results.

## Phase 6 — Scale, Memory Maturity & Enterprise Hardening (~ongoing)
- Semantic and procedural memory tiers completed (`AGENTS.md`); memory consolidation jobs live with privacy-tier gating enforced.
- Full deployment-profile support: hybrid VPC and on-prem/air-gapped profiles (`ARCHITECTURE.md`) validated with a real customer in each category.
- SOC 2 Type II readiness and GDPR data-subject workflows completed as a formal compliance program.
- Cost/latency optimization pass across the Model Router based on a full quarter of production eval + cost data.
- V1's `/api/v1/*` deprecation timeline finalized and communicated, once `/api/v2/*` has full parity plus the new capabilities.

**Exit criteria**: at least one production customer running each deployment profile; compliance program formally underway; V1 API sunset scheduled.

## Phase 7 — GPU Upgrade (runs once GPU hardware is available)
Replaces the CPU-only stand-ins from Phase 2 with their originally-scoped, GPU-dependent versions. This is explicitly the **last** phase in this roadmap by design (not because the work is low-priority, but because every capability it upgrades already has a working, tested, production CPU-only equivalent from Phase 2 — nothing is *blocked* waiting on this phase, it's a quality/capability upgrade, not an unblock). Target hardware: RTX 4050 (6GB VRAM), confirmed sufficient for LayoutLMv3, Donut, Table Transformer, YOLOv8, and fine-tuning BERT-scale models (InLegalBERT/LegalBERT); a full-precision 8B+ LLM needs ~16GB+ VRAM, so self-hosted LLM serving here means either a 4-bit-quantized 8B model or a smaller model (Llama 3.2 3B / Phi-3-mini) at full precision, both of which fit the 6GB budget.

- Computer vision: LayoutLMv3 (layout analysis), Donut (OCR-free scan understanding), Table Transformer (real table structure), a trained signature/stamp detector (YOLOv8 — needs labeled data collection, not just GPU access), and a trained redaction detector to replace/validate against the geometric heuristic.
- NLP: fine-tuned InLegalBERT/LegalBERT NER, GLiNER for zero-shot entity types, fastcoref for real coreference resolution (replacing `app/services/nlp/coref.py`'s heuristic), the weak-supervision-then-distill pipeline for the deontic tagger, and a fine-tuned clause/contract-type classifier evaluated against real CUAD.
- Model serving: vLLM deployed serving a quantized/smaller open-weight model; Model Router begins routing rewrite/Q&A tasks to it, A/B tested against the Gemini-only baseline already in production — this is the same milestone Phase 2 originally targeted, just reached with real hardware instead of skipped.
- Eval harness: real Ragas + CUAD/ContractNLI integration, extending (not replacing) the hand-curated gold set from Phase 2, which stays as a fast pre-merge smoke check.
- Explicit re-evaluation step for each upgraded component: compare the new model's eval score against the CPU-only baseline it replaces before making it the default — a fine-tuned model is not automatically better for this domain than a well-tuned rule base, and this phase should prove it, not assume it.

**Exit criteria**: at least one task is served by a self-hosted open-weight model in production with eval scores at or above the Gemini baseline (closing Phase 2's original, deferred exit criterion); LayoutLMv3/Donut/Table Transformer integrated and measurably improving extraction quality on scanned/complex documents versus the Phase 2 CV heuristics.

## Cross-cutting, all phases
- **Nothing merges without the eval gate** (from Phase 2 onward) and, for anything touching a sensitive-tier code path, a security review.
- **Every phase preserves V1's live traffic** — this is an additive migration, not a cutover-and-hope plan.
