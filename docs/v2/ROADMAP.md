# Roadmap

Phased delivery plan from V1's current production state to the full V2 vision. Each phase leaves the system deployable — V1's endpoints keep serving throughout (`ARCHITECTURE.md`'s migration path), so this is an incremental cutover, not a rewrite-and-replace. Durations are rough sizing (in sprints, assuming a small dedicated team), not commitments.

## Phase 0 — V1 Hardening (prerequisite, ~2-4 sprints)
Complete the hardening work already scoped in `docs/v1/ROADMAP.md`/`TASKS.md` (tests, CORS fix, secrets hygiene, config correctness) before layering V2 on top. Building agents and a knowledge graph on top of an untested, unauthenticated, in-memory-storage backend would compound risk rather than reduce it.

**Exit criteria**: V1's P0/P1 tasks (docs/v1/TASKS.md) are complete: CI running, CORS fixed, secrets rotated, config centralized.

## Phase 1 — Foundation Re-platform (~4-6 sprints)
Stand up the V2 data layer and service skeleton without changing user-facing behavior yet.
- Polyglot persistence stood up (Postgres, Qdrant, Memgraph, Redis, MinIO, Redpanda) per `ARCHITECTURE.md`.
- API Gateway restructured into the service-oriented shape (`BACKEND.md`), with `/api/v1/*` continuing to serve V1's exact contract, now backed by the new persistence layer instead of in-memory storage.
- Auth Service introduced; all endpoints require authentication (closing V1's biggest security gap).
- Model Router introduced as a drop-in generalization of `genai_client.py`, initially routing 100% of traffic to the existing Gemini integration (no behavior change, just the new indirection layer in place).
- Observability stack (OpenTelemetry, Langfuse, Prometheus/Grafana) wired to every new service from day one.

**Exit criteria**: V1 feature parity, now running on the V2 data/service foundation, authenticated, observable, with zero in-memory-only state.

## Phase 2 — Core AI Pipeline Buildout (~6-10 sprints)
Build the pipelines that turn flat text into structured understanding.
- CV pipeline (`COMPUTER_VISION.md`): layout analysis, table extraction, quality triage — extending, not replacing, PyMuPDF/python-docx.
- NLP pipeline (`NLP.md`): segmentation, NER, coreference, deontic tagging, clause classification — producing the canonical `ClauseObject`.
- First open-weight models deployed via vLLM (Tier 1); Model Router begins routing rewrite/Q&A tasks to open-weight models per the task table in `AI_STACK.md`, with Gemini as Tier 2 fallback.
- Eval harness stood up (Ragas + CUAD/ContractNLI-based suite); CI eval-gating begins for any prompt/model change from this point forward.

**Exit criteria**: every uploaded document produces a structured `ClauseObject` graph, not just flat text; at least one production task fully served by an open-weight model with eval scores at or above the prior Gemini-only baseline.

## Phase 3 — Knowledge Graph & GraphRAG (~6-8 sprints)
- Knowledge Graph Service and Memgraph deployed (`KNOWLEDGE_GRAPH.md`); entity resolution and relation extraction pipelines running on newly ingested documents.
- Hybrid RAG (dense + sparse + graph) replaces V1's hardcoded 28-string knowledge base (`AI_STACK.md`); real, cited statute/regulation corpus ingested for the jurisdictions currently hinted at in V1.
- Contextualizer feature migrated onto real RAG with citations.
- Backfill: existing documents in the system re-processed to populate the graph retroactively.

**Exit criteria**: Contextualizer answers cite real, retrievable sources; a GraphRAG query can answer "what else in this portfolio references this defined term."

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

## Cross-cutting, all phases
- **Nothing merges without the eval gate** (from Phase 2 onward) and, for anything touching a sensitive-tier code path, a security review.
- **Every phase preserves V1's live traffic** — this is an additive migration, not a cutover-and-hope plan.
