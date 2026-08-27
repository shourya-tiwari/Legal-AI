# Tasks

Actionable, checkbox-level backlog for `ROADMAP.md`. Grouped by phase, then by architecture layer. This is a planning checklist, not a sprint-committed schedule — sizing and sequencing within a phase is left to the team executing it.

## Phase 0 — V1 Hardening (prerequisite)

- [x] Complete all P0 items in `docs/v1/TASKS.md` (secrets rotation, CORS fix, malformed HTML, dead code, model-default consistency)
- [x] Complete P1 testing/CI items in `docs/v1/TASKS.md` (pytest suite, GitHub Actions, structured logging, config centralization)

## Phase 1 — Foundation Re-platform

**Data layer**
- [x] Stand up Postgres with the core schema sketch in `ARCHITECTURE.md` (`organizations`, `api_keys`, `documents`, `audit_log` — `users`/`sessions` tables deferred, see Backend notes below)
- [ ] Stand up Qdrant, Memgraph, Redis, MinIO, Redpanda (docker-compose for local dev, Helm charts for cloud) — **scoped down**: only Postgres + Redis stood up (approved pragmatic-slice decision); Qdrant/Memgraph/Redpanda/MinIO deferred to Phase 3 when RAG/KG actually need them
- [x] Migrate V1's `document_storage` in-memory dict usage to Postgres-backed document records

**Backend**
- [ ] Introduce API Gateway service boundary; move routing/auth concerns out of the monolithic `main.py` pattern — not done; still one FastAPI process (cross-cutting concerns centralized via `app/guard.py` instead, which is the right amount of separation before an actual microservice split is justified)
- [x] Build Auth Service (users, orgs, roles, API keys, session tokens) — **scoped down**: org-scoped API keys only (`app/auth.py`); no per-user login/roles/session tokens yet since there's no login UI
- [x] Require authentication on every endpoint (close V1's open-access gap) — enforced via `app/guard.py`'s `api_guard` dependency; **default OFF** (`AUTH_REQUIRED=false`) by deliberate choice so the live public frontend keeps working until keys are issued
- [x] Build the Model Router as a generalization of `genai_client.py`; route 100% of traffic to Gemini initially (no behavior change) — `app/services/model_router.py`
- [ ] Re-implement `/api/v1/*` endpoints on top of the new persistence/auth layer, preserving exact V1 response contracts — persistence/auth layer is live under the existing unversioned `/api/*` paths; the `/api/v1/*` prefix itself hasn't been introduced (no `/api/v2/*` exists yet to need versioning against)

**Observability** — not started; deferred by approved scope decision (no OpenTelemetry/Langfuse/Prometheus/Grafana yet, structured `logging` from Phase 0 only)
- [ ] Wire OpenTelemetry tracing into every new service
- [ ] Deploy Langfuse for LLM-call tracing
- [ ] Deploy Prometheus + Grafana dashboards (latency, error rate, cost)

**Developer workflow**
- [ ] Set up monorepo structure (`apps/frontend`, `services/*`, `packages/schemas`, `packages/prompts`, `infra/`) — not done, still the original `backend/`+`frontend/` split
- [ ] Terraform + Helm skeletons for dev/staging/prod environments — not done, deferred (still deploying to Render)
- [x] `docker-compose` local-dev profile — **scoped down**: Postgres + Redis only (`docker-compose.yml`), not the full data layer or an open-weight model (no GPU on this dev machine — see the new GPU Upgrade phase at the end of this file)

## Phase 2 — Core AI Pipeline Buildout

**Scope note**: this dev machine has no discrete GPU (Intel integrated graphics only, ~7.75GB RAM) and cannot run vLLM/LayoutLMv3/Donut/Table Transformer/YOLOv8 or any fine-tuning. By approved decision, everything GPU-dependent below is **deferred to the new GPU Upgrade phase** at the end of this file (target: RTX 4050, 6GB VRAM), and every other Phase 2 item was implemented as a genuine, tested, CPU-only equivalent instead of a stub — see `LEARNING_LOG.md` entry for this phase for the full reasoning.

**Computer vision (`COMPUTER_VISION.md`)**
- [x] Document quality triage (blur/skew/resolution scoring) — **delivered via OpenCV, not a trained model**: Laplacian-variance blur score + Hough-line skew estimate (`app/services/cv/quality.py`), wired into `extractor.py`'s PDF path and surfaced additively in `/api/upload`'s response
- [ ] Integrate LayoutLMv3 for layout analysis → **GPU Upgrade phase**
- [ ] Integrate Donut for OCR-free scan understanding; wire confidence-gated commercial OCR fallback → **GPU Upgrade phase**
- [ ] Integrate Table Transformer for table extraction → **GPU Upgrade phase**
- [ ] Train/integrate signature & stamp detector (YOLOv8-family) → **GPU Upgrade phase** (also needs labeled training data, not just a GPU)
- [x] Redaction-region detection — **delivered as a geometric heuristic, not a trained model**: solid-black-rectangle contour detection (`app/services/cv/redaction.py`); real learned redaction detection is still a GPU Upgrade phase item

**NLP (`NLP.md`)**
- [x] Clause/sentence segmentation using CV layout hints — paragraph + sentence-boundary regex (`app/services/nlp/segmentation.py`); "CV layout hints" specifically not used since LayoutLMv3 is deferred
- [x] Defined-term extraction & resolution — regex-based (`app/services/nlp/defined_terms.py`); also does double duty as party/entity identification (see NER note below)
- [x] Cross-reference resolution — regex-based (`app/services/nlp/cross_references.py`)
- [ ] Fine-tune NER model (InLegalBERT/LegalBERT base) for parties/dates/money/jurisdictions → **GPU Upgrade phase** for the fine-tuned model. Functional substitute shipped now: parties via defined-term extraction, money/jurisdiction via regex (`app/services/nlp/entities.py`) — genuinely reliable for this domain, not just a placeholder (see `defined_terms.py`'s docstring for why)
- [ ] Integrate GLiNER for zero-shot entity types → **GPU Upgrade phase**
- [ ] Integrate coreference resolution (fastcoref, with LLM fallback) → **GPU Upgrade phase** for the real resolver. A clearly-labeled heuristic stand-in shipped now (`app/services/nlp/coref.py` — explicitly documented as NOT real coreference resolution)
- [x] Weak-supervise + distill the deontic modality tagger — **scoped down**: modal-verb regex tagger (Tier 0) shipped and eval-gated (100% recall on the gold set); optional Gemini escalation for clauses no rule matches (`app/services/nlp/deontic.py`). The weak-supervision-then-distill *training pipeline* itself (`DEEP_LEARNING.md`) is separate future work requiring labeled data collection
- [x] Temporal expression normalization — `dateparser` for absolute dates; durations ("30 days") deliberately left unresolved rather than misresolved against wall-clock "now" (`app/services/nlp/temporal.py`)
- [ ] Fine-tune clause/contract type classifier (eval against CUAD) → **GPU Upgrade phase** for the fine-tuned model + real CUAD eval. Functional substitute shipped now: keyword-taxonomy rule base + optional Gemini escalation (`app/services/nlp/clause_classifier.py`), eval-gated against a hand-curated gold set (see AI stack notes below)
- [x] Ambiguity/vagueness detection scoring — extends V1's vague-term list (`app/services/nlp/ambiguity.py`)
- [x] Define and ship the canonical `ClauseObject` schema — `app/services/nlp/schema.py` (not a separate `packages/schemas` package yet — still one FastAPI app, not a monorepo)

**Model Router / AI stack (`AI_STACK.md`)**
- [ ] Deploy vLLM serving for at least one open-weight model (Llama 3.1 8B to start) → **GPU Upgrade phase**
- [ ] Route plain-English rewrite task to open-weight Tier 1 model; A/B against Gemini baseline → **GPU Upgrade phase**
- [ ] Route structure/timeline extraction to Qwen2.5-72B-Instruct; validate JSON-schema adherence rate → **GPU Upgrade phase**
- [x] Stand up eval harness: Ragas integration + CUAD/ContractNLI-based gold set — **scoped down**: lightweight custom harness instead of Ragas (`app/eval/run_eval.py`) against a 15-example hand-curated gold set (`app/eval/gold_set.py`), reporting clause-type accuracy + deontic recall. Real Ragas + CUAD/ContractNLI integration is separate future work (downloading/curating an external dataset is real effort, not a config change)
- [x] Wire CI eval-gating for any prompt/model/config change — **scoped to what's real today**: `tests/test_eval_gate.py` fails the (already-CI-wired) pytest suite if clause-type accuracy or deontic recall drops below the current gold-set baseline; full model/prompt-version-aware gating from `ARCHITECTURE.md` is future work once there's more than one model tier to gate between

## Phase 3 — Knowledge Graph & GraphRAG

**Knowledge graph (`KNOWLEDGE_GRAPH.md`)**
- [ ] Deploy Memgraph; implement schema (node/edge types)
- [ ] Build entity resolution pipeline (embedding clustering + LLM-assisted disambiguation)
- [ ] Build relation extraction pipeline (classifier + LLM-assisted low-confidence fallback)
- [ ] Implement schema validation + deontic consistency checks on graph write
- [ ] Implement portfolio-linking on ingestion
- [ ] Implement bitemporal versioning (valid time / transaction time)
- [ ] Backfill: re-process existing documents into the graph

**RAG (`AI_STACK.md`)**
- [ ] Deploy BGE-M3 for dense embeddings; deploy bge-reranker-v2-m3
- [ ] Build BM25/SPLADE sparse index
- [ ] Implement GraphRAG traversal tool over Memgraph
- [ ] Implement reciprocal rank fusion across dense/sparse/graph retrievers
- [ ] Ingest and cite a real statute/regulation corpus (start with jurisdictions V1 already hinted at)
- [ ] Migrate Contextualizer feature to real hybrid RAG with citations; remove the hardcoded 28-string list
- [ ] Implement citation-grounded generation prompt contract + citation validator

## Phase 4 — Agentic Orchestration MVP

**Agents (`AGENTS.md`)**
- [ ] Deploy LangGraph + Temporal orchestration runtime
- [ ] Define the shared `CaseState` schema
- [ ] Implement Orchestrator/Planner agent
- [ ] Implement Extraction agent (wraps CV/NLP pipeline outputs)
- [ ] Implement Risk & Compliance agent
- [ ] Implement Clause Research agent (hybrid RAG)
- [ ] Implement Verifier/Critic agent (citation check + NLI faithfulness check + KG consistency check)
- [ ] Implement typed tool interfaces (KG query, vector search, statute lookup, date math, clause diff, human-approval request)
- [ ] Persist full agent trace to `agent_traces`

**Memory (`AGENTS.md`)**
- [ ] Implement Memory Service: session tier (Redis)
- [ ] Implement episodic tier (Postgres + Qdrant)
- [ ] Implement memory consolidation worker (session/episodic → semantic, with privacy-tier gating)

**Frontend (`FRONTEND.md`)**
- [ ] Scaffold Next.js + TypeScript app; generate API client from OpenAPI schema
- [ ] Build Workspace and Document Analyzer modules (V1 parity)
- [ ] Build Agent Trace Viewer (real-time via session WebSocket)
- [ ] Build human-in-the-loop review queue UI
- [ ] Feature-flag `/api/v2` usage per org for staged rollout

**Backend**
- [ ] Introduce `/api/v2/*` session/document-first endpoints
- [ ] Implement Notification/Webhook Service for async job completion

## Phase 5 — Portfolio Intelligence & Research Features

**Deep learning (`DEEP_LEARNING.md`)**
- [ ] Curate training data (org corpora with consent + CUAD/ContractNLI)
- [ ] Weak-supervision labeling pass (batch, offline frontier-model use)
- [ ] Human legal-expert review of weak labels
- [ ] Train Risk Scoring Model (LightGBM); integrate SHAP explainability
- [ ] Train/finalize Clause/Contract Type Classifier
- [ ] Train Document Sensitivity Classifier
- [ ] Set up MLflow model registry + DVC data versioning
- [ ] Wire eval-gated model promotion into CI/CD

**Portfolio agents (`AGENTS.md`, `KNOWLEDGE_GRAPH.md`)**
- [ ] Implement Cross-Document Consistency agent (rule-based/embedding-similarity baseline first)
- [ ] Implement Simulation agent (deterministic discrete-event baseline first)
- [ ] Implement Negotiation/Drafting agent with static, org-configured preferences (no learned playbook yet)
- [ ] Ship Negotiation Studio frontend module with Yjs-based collaborative editing
- [ ] Ship Risk Dashboard spider/radar chart (closes the V1 README promise gap)

**Research track (`NOVELTY.md`) — each item independently gated**
- [ ] Idea #1 (Deontic GAT conflict detection): literature/patent search → prototype → benchmark vs. rule-based baseline
- [ ] Idea #2 (Temporal obligation simulation): prototype auto-constructed simulation from extracted conditional logic → validate against manually-modeled scenarios
- [ ] Idea #3 (Legal-semantic fingerprinting): construct hard-negative training set → train contrastive model → benchmark contradiction-detection precision/recall vs. generic embeddings
- [ ] Idea #4 (Adaptive negotiation playbook): prototype counterfactual fingerprint-delta attribution → validate against a held-out redline history set
- [ ] Idea #5 (Deontic-structure-aware ablation): implement deontic-parse-based perturbation → compare attribution quality vs. token-level SHAP baseline (human evaluation of "meaningfulness")
- [ ] For any idea advancing past prototype: commission formal prior-art search via qualified patent counsel before further investment or disclosure

## Phase 6 — Scale, Memory Maturity & Enterprise Hardening

- [ ] Implement semantic memory tier (cross-document, per-org) with privacy-tier gating
- [ ] Implement procedural memory tier (Redline Acceptance Predictor productionized)
- [ ] Validate hybrid VPC deployment profile with a pilot customer
- [ ] Validate on-prem/air-gapped deployment profile with a pilot customer
- [ ] Begin SOC 2 Type II readiness program
- [ ] Implement GDPR data-subject export/delete workflows
- [ ] Full cost/latency review of Model Router tier allocation using a quarter of production data
- [ ] Publish `/api/v1` deprecation timeline

## Phase 7 — GPU Upgrade (replace CPU-only stand-ins with their originally-scoped versions)

Runs once GPU hardware is available (target: RTX 4050, 6GB VRAM — confirmed sufficient for everything in this phase except full-precision 8B+ LLM serving, which needs quantization or a smaller model; see `LEARNING_LOG.md`'s Phase 2 entry for the sizing breakdown). Every item here has a working CPU-only equivalent already shipped and in production use (Phase 2) — this phase upgrades quality/capability, it does not unblock anything that's currently missing entirely.

**Computer vision**
- [ ] Replace OpenCV heuristic quality triage with LayoutLMv3-based layout analysis (reading order, section/table region detection) — `docs/v2/COMPUTER_VISION.md`
- [ ] Integrate Donut for OCR-free understanding of degraded scans; keep the existing Tesseract/quality-triage path as the fallback for clean digital PDFs, not a replacement
- [ ] Integrate Table Transformer for real table structure extraction (rows/columns), replacing the current "tables are just text blocks" behavior
- [ ] Collect/label a signature & stamp training set; train a YOLOv8-family detector (replaces: nothing currently — this capability doesn't exist yet even as a stand-in)
- [ ] Replace the solid-black-rectangle redaction heuristic (`app/services/cv/redaction.py`) with a trained redaction detector, or validate the heuristic's precision/recall well enough to justify keeping it

**NLP / deep learning**
- [ ] Fine-tune InLegalBERT/LegalBERT for NER (parties/dates/money/jurisdictions), replacing/augmenting the regex + defined-term approach in `app/services/nlp/entities.py` and `defined_terms.py` — compare against the current approach's accuracy before assuming the fine-tuned model is strictly better for this domain
- [ ] Integrate GLiNER for zero-shot entity types not covered by the fine-tuned NER model's label set
- [ ] Integrate fastcoref for real coreference resolution, replacing the heuristic in `app/services/nlp/coref.py`
- [ ] Run the weak-supervision-then-distill pipeline for the deontic tagger (`app/services/nlp/deontic.py`'s rule-based Tier 0 becomes the bootstrap/comparison baseline, not a throwaway)
- [ ] Fine-tune the clause/contract type classifier and eval it against real CUAD, replacing the keyword-taxonomy rule base in `app/services/nlp/clause_classifier.py` as the primary classifier (keep the rule base as a fast Tier-0 pre-filter)
- [ ] Train the Risk Scoring Model (LightGBM) and Document Sensitivity Classifier per `DEEP_LEARNING.md`

**Model serving**
- [ ] Deploy vLLM; serve a quantized Llama 3.1 8B (or a smaller open-weight model, e.g. Llama 3.2 3B/Phi-3-mini, at full precision) within the 6GB VRAM budget
- [ ] Route rewrite/Q&A tasks to the self-hosted model via the Model Router; A/B against the current Gemini-only baseline before making it the default
- [ ] Re-evaluate whether GLiNER/fastcoref/the fine-tuned classifiers above are worth the added serving complexity vs. staying on their CPU equivalents, using real eval numbers, not assumption

**Eval harness**
- [ ] Integrate real Ragas + CUAD/ContractNLI, replacing/extending the hand-curated 15-example gold set (`app/eval/gold_set.py`) — keep the hand-curated set too, as a fast pre-merge smoke check before the fuller suite runs

## Continuous / cross-cutting (all phases)

- [ ] Every prompt/model/config change passes the eval gate before merge (from Phase 2 onward)
- [ ] Every sensitive-tier code path change gets a security review before merge
- [ ] Model cards maintained for every trained model (`DEEP_LEARNING.md`)
- [ ] Quarterly drift-monitoring review of production eval scores against the gold benchmark
