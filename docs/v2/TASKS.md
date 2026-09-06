# Tasks

Actionable, checkbox-level backlog for `ROADMAP.md`. Grouped by phase, then by architecture layer. A planning checklist, not a sprint-committed schedule.

**Status legend**: `[x]` done · `[~]` partially done (annotation says what) · `[ ]` not started · `⛔` blocked (annotation says on what).

## Reality check (current codebase)

**Running now, no external anything**: FastAPI backend with 12 route modules; org-scoped auth (default-off) + rate limiting + audit log; Postgres/SQLite persistence with an interim column-migration shim; provider-agnostic **Model Router** (`generate`/`embed`/`rerank`/`entail`/`ner` capabilities, declarative policy, Class-A offline fallbacks for every task, import-linter contract); the full **NLP pipeline** (rule-based) + **CV triage** (now persisted, not just returned once); **Knowledge Graph** + **hybrid RAG** (dense+sparse+graph, RRF, rerank) + a **Cross-Document Consistency** embedding-similarity baseline (catches what the KG's exact-term match can't); a **planner-driven agent pipeline** (extraction → planner → dispatch → verifier) with a **real Class-A NLI faithfulness head**, its `needs_human_review` outcome now **persisted** (`CaseAnalysis`) and listable via a real review queue; a **Simulation** agent (deterministic discrete-event baseline over resolved clause dates); **GLiNER** zero-shot NER; **document sensitivity tiering** enforced end-to-end (confidential/privileged never leave the perimeter); a **graded eval harness** (LegalBench/MNLI) + **cutover gate with curated gold sets for `qa`/`clause_rewrite`/`timeline_extract`/`risk_analysis`** + `model_calls`/`eval_runs` telemetry (now surfaced via `GET /api/models/eval-runs`, not just written); the **`/api/v2` document-first API**; a **fine-tuning scaffold** (not run); a **Next.js frontend** (`frontend-v2/`, zero third-party font/asset origin) covering V1-parity document actions, the agent-analysis panel with a post-hoc trace viewer, structured-NLP/KG/Model-Router-status views, a review queue, and eval-scores admin. Test suite: **213 pass + 1 skip**.

**Hardware ceiling (project decision)**: the only GPU is **one RTX A4000 (16 GB)**, often borrowed; the owner's own machine is CPU-only (Core i5 + 4 GB integrated). **No 24 GB+ card, owned or rented, is planned.** So the self-hosted generation target is **Qwen3-8B** (+ 14B-AWQ escalation), not 32B. Qwen3-32B / reasoning models / 7B VLM are moved to future scope (Phase 6 "Deferred — beyond the hardware ceiling").

**Configured but not stood up** (ops, not code): Docker Compose + Ollama + TEI — the `gpu` compose profile and `scripts/bootstrap_selfhosted.sh` exist; run them to serve Qwen3-8B + bge-m3 + bge-reranker.

**Blocked**: the LLM task cutovers (need a served `local-llm` — expect 8B/14B to pass on easy tasks, lose to Gemini on hard reasoning); real coreference (the original torch-<2.6 CVE guard is resolved on a current stack, but `fastcoref`'s unmaintained model code now breaks against transformers ≥ 5's internals instead); the clause/deontic fine-tune *runs* (real train/val data now curated — see below — the remaining blocker is purely GPU time, minutes on the A4000).

**⛔ Blocked on infrastructure this environment doesn't have** (not a priority choice — no k8s cluster, container registry, or air-gapped network segment exists here to build or validate against): on-prem packaging (Zarf/SBOM/Harbor), the collapsed data layer, durable execution engine choice, the Memory Service, the real-time (session-WebSocket) Agent Trace Viewer.

**Not started, no infra blocker** (a scope/priority choice, buildable whenever picked up): Provider & Model admin's Class C toggles + delta-report view, per-user RBAC, the PII redaction gate, Phase 8's remaining items (fine-tuned models, learned upgrades to the Consistency/Simulation baselines, Negotiation/Drafting agent, Negotiation Studio, Risk Dashboard, KG Explorer frontend), and every `NOVELTY.md` research idea (none have a prototype yet — they're research proposals, not built features).

**Roadmap renumbering**: previous "Phase 7 — GPU Upgrade" → **Phase 6**; previous "Phase 5 — Portfolio Intelligence" → **Phase 8**; previous "Phase 6 — Scale/Hardening" → **Phase 9**. New **Phase 5** (Provider Abstraction) + **Phase 7** (Deployment Profiles) inserted. See `ROADMAP.md`.

---

## Phase 0 — V1 Hardening (prerequisite) — ✅ Complete

- [x] Complete all P0 items in `docs/v1/TASKS.md` (secrets rotation, CORS fix, malformed HTML, dead code, model-default consistency)
- [x] Complete P1 testing/CI items in `docs/v1/TASKS.md` (pytest suite, GitHub Actions, structured logging, config centralization)

## Phase 1 — Foundation Re-platform — ✅ Complete (pragmatic slice)

**Data layer**
- [x] Stand up Postgres with the core schema sketch (`organizations`, `api_keys`, `documents`, `audit_log`; `users`/`sessions` deferred)
- [~] Stand up the polyglot data layer — **Postgres + Redis only**; Qdrant/Memgraph/Redpanda/MinIO deferred to the phases that need them (Memgraph landed in Phase 3)
- [x] Migrate V1's `document_storage` in-memory dict to Postgres-backed document records

**Backend**
- [~] Introduce API Gateway service boundary — not done; still one FastAPI process, cross-cutting concerns centralized via `app/guard.py` (the right amount of separation before a real service split is justified)
- [x] Build Auth Service — **scoped down**: org-scoped API keys only (`app/auth.py`); no per-user login/roles/session tokens (no login UI yet)
- [x] Require authentication on every endpoint — `app/guard.py`'s `api_guard`; **default OFF** (`AUTH_REQUIRED=false`) so the live public frontend keeps working
- [x] Build the Model Router as a generalization of `genai_client.py` — `app/services/model_router.py`. **Re-scoped**: this is the provider-agnostic seam (`AI_STACK.md`), currently with one provider (Gemini). Phase 5 makes it real.
- [~] Re-implement `/api/v1/*` endpoints on the new persistence/auth layer — persistence/auth is live under the existing unversioned `/api/*`; the `/api/v1/*` prefix itself not introduced (nothing needs versioning against yet)

**Observability** — [ ] not started; deferred (structured `logging` from Phase 0 only). OpenTelemetry / Langfuse / Prometheus / Grafana → Phase 5+.

**Developer workflow**
- [ ] Monorepo restructure (`apps/`, `services/*`, `packages/*`, `infra/`) — not done; still `backend/` + `frontend/`
- [ ] OpenTofu + Helm skeletons — not done (still deploying to Render)
- [x] `docker-compose` local-dev profile — **scoped down**: Postgres + Redis (+ Memgraph from Phase 3), not the full data layer or a served model

## Phase 2 — Structured Understanding: CPU Pipeline — ✅ Complete (CPU slice; GPU items → Phase 6)

**Computer vision (`COMPUTER_VISION.md`)**
- [x] Document quality triage — OpenCV Laplacian-variance blur + Hough-line skew (`app/services/cv/quality.py`), not a trained model
- [ ] Layout analysis (Docling / LayoutLMv3 / Qwen2.5-VL) → **Phase 6**
- [ ] OCR-free scan understanding (olmOCR / Qwen2.5-VL) + confidence-gated escalation → **Phase 6**
- [ ] Table extraction (Table Transformer / PP-Structure) → **Phase 6**
- [ ] Signature & stamp detector (YOLOv8-family) → **Phase 6** (also needs labelled data)
- [x] Redaction-region detection — geometric solid-black-rectangle contour heuristic (`app/services/cv/redaction.py`), not a trained model

**NLP (`NLP.md`)**
- [x] Clause/sentence segmentation — paragraph + sentence-boundary regex (`app/services/nlp/segmentation.py`); CV layout hints not used (LayoutLMv3 deferred)
- [x] Defined-term extraction & resolution — regex (`app/services/nlp/defined_terms.py`); doubles as party/entity ID
- [x] Cross-reference resolution — regex (`app/services/nlp/cross_references.py`)
- [ ] Fine-tuned NER (InLegalBERT/ModernBERT base) → **Phase 6**. CPU substitute shipped: parties via defined-term extraction, money/jurisdiction via regex (`app/services/nlp/entities.py`)
- [ ] GLiNER zero-shot entity types → **Phase 6**
- [ ] Real coreference (maverick-coref / fastcoref, LLM fallback) → **Phase 6**. Clearly-labelled heuristic stand-in shipped (`app/services/nlp/coref.py`)
- [x] Deontic modality tagger — **scoped down**: modal-verb regex Tier-0, eval-gated (100% gold-set recall), optional LLM escalation (`app/services/nlp/deontic.py`). The weak-supervise-then-distill *training pipeline* → Phase 6/8
- [x] Temporal expression normalization — `dateparser` for absolute dates; durations left unresolved deliberately (`app/services/nlp/temporal.py`)
- [ ] Fine-tuned clause/contract-type classifier + real CUAD eval → **Phase 6**. CPU substitute shipped: keyword-taxonomy rule base + optional LLM escalation (`app/services/nlp/clause_classifier.py`), eval-gated against a hand-curated gold set
- [x] Ambiguity/vagueness detection — extends V1's vague-term list (`app/services/nlp/ambiguity.py`)
- [x] Canonical `ClauseObject` schema — `app/services/nlp/schema.py` (not a `packages/schemas` package yet)

**Model Router / AI stack (`AI_STACK.md`)**
- [ ] Deploy vLLM serving an open-weight model → **Phase 6**
- [ ] Route rewrite / extraction tasks to self-hosted models → **Phase 6**
- [x] Stand up eval harness — **scoped down**: lightweight custom harness (`app/eval/run_eval.py`) against a 15-example gold set (`app/eval/gold_set.py`); Ragas/Inspect AI/CUAD integration → Phase 5/6
- [x] CI eval-gating for prompt/model/config changes — `tests/test_eval_gate.py` fails the suite on clause-type-accuracy or deontic-recall regression; full provider/policy-aware gating → Phase 5

## Phase 3 — Knowledge Graph & Hybrid RAG — ✅ Complete (pragmatic slice)

**Knowledge graph**
- [x] Deploy Memgraph; implement schema — `docker-compose.yml` + `app/services/kg/schema.py`. Nodes: `Document`/`Clause`/`DefinedTerm`/`CrossReferenceTarget`; edges: `PART_OF`/`DEFINES`/`USES_TERM`/`REFERENCES`/`SAME_AS`. Narrower than the full vision (no `Obligation`/`Statute`/`Jurisdiction` nodes yet) — scoped to what Phase 2's output supports
- [x] Entity resolution pipeline — **scoped down**: `difflib.SequenceMatcher` context-similarity (`should_link_terms` in `builder.py`), not embedding clustering + LLM disambiguation
- [x] Relation extraction pipeline — **scoped down**: derived directly from Phase 2's `ClauseObject` fields, not a separate classifier
- [~] Schema validation + deontic consistency checks — `find_potential_conflicts` flags candidate cross-document obligation/prohibition pairs sharing a term; explicitly "candidate for review", not confirmed (no actor/action resolution yet)
- [x] Portfolio-linking on ingestion — `link_portfolio_terms` in `builder.py`, `POST /api/kg/ingest`
- [ ] Bitemporal versioning (valid time / transaction time) — not done → **Phase 8** (needed for simulation)
- [x] Backfill existing documents into the graph — `POST /api/kg/ingest` is idempotent (MERGE throughout), doubles as backfill

**RAG**
- [ ] Deploy self-hosted embeddings + reranker → **Phase 5** (embeddings, CPU-feasible) / **Phase 6** (GPU-served). Dense retrieval today uses Gemini's embedding API. **Bug fixed during this phase**: `text-embedding-004` was silently 404ing; updated to `gemini-embedding-001`
- [x] Sparse index — **BM25 only** (`app/services/rag/bm25.py`); SPLADE (learned sparse) → Phase 6. BM25 is a legitimate permanent choice, not a placeholder
- [x] GraphRAG traversal tool over Memgraph — `find_clauses_using_term`/`find_potential_conflicts` in `app/services/kg/queries.py`; exposed via `/api/kg/query`, `/api/kg/conflicts`
- [~] RRF fusion across dense/sparse/graph — **dense + sparse only** (`app/services/rag/hybrid.py`, k=60); graph fusion → **Phase 5**
- [x] Ingest & cite a real statute/regulation corpus — **modest and judicious**: `app/services/rag/corpus.py` with a `citation` field populated only where confidently verifiable (Cal. Civ. Code § 1950.5, FLSA § 207, GDPR, CCPA); most entries `citation=None` (general principles) rather than inventing citations
- [x] Migrate Contextualizer to hybrid RAG with citations; remove the hardcoded 28-string list — `explainer.py` now calls `hybrid_search`
- [x] Citation-grounded generation prompt + citation validator — `templates.py` asks for `[N]` citations; `citation_validator.py` flags fabricated citation numbers (does NOT verify entailment — that's the NLI head, Phase 6)

## Phase 4 — Agentic Orchestration MVP — ✅ Complete (backend MVP)

**Agents (`AGENTS.md`)**
- [~] Deploy LangGraph + durable-execution runtime — **LangGraph done** (`app/agents/graph.py`); **durable engine not done**, runs synchronously in-request → **Phase 7**
- [x] Define the shared `CaseState` schema — `app/agents/state.py`, scoped to what the fixed pipeline needs (no `memory_refs`/`sensitivity_tier` yet)
- [x] Orchestrator/Planner agent — **done in Phase 7** (`app/agents/{planner,registry,graph}.py`): a `planner` node picks which middle agents run; rule-based default + optional LLM (`task="agent_plan"`, offline-safe fallback); `analysis_mode` presets `full`/`quick`/`risk_only`/`extract_only`. The dynamic *tool-choosing* planner of the full vision is still ahead.
- [x] Extraction agent — `app/agents/extraction.py`, wraps Phase 2's `build_clause_objects`
- [x] Risk & Compliance agent — `app/agents/risk_compliance.py`: keyword flags (`risk_radar/rules.py`) + KG candidate-conflict lookup. AI risk pass not invoked here (Tier-0 keyword sweep only)
- [x] Clause Research agent — `app/agents/research.py`; only runs on already-flagged clauses
- [~] Verifier/Critic agent — citation check (real, reuses `citation_validator.py`) + KG consistency check (real — a KG conflict forces `needs_human_review`) ship now; **NLI faithfulness check is a lexical-overlap stand-in** (`_lexical_overlap_faithfulness`), honestly labelled → real cross-encoder **Phase 6**
- [ ] Typed tool interfaces (KG query, vector search, statute lookup, date math, clause diff, human-approval) — **not built as a formal typed-tool-calling layer**; agents call services as plain Python functions → **Phase 7** (when a real planner needs to choose tools)
- [x] Persist full agent trace to `agent_traces` — new table in `db_models.py`; one row per step, verified live against Postgres

**Memory (`AGENTS.md`)** → all **Phase 7**
- [ ] Memory Service: session tier (Redis)
- [ ] Episodic tier (Postgres + vector store)
- [ ] Memory consolidation worker (session/episodic → semantic, privacy-tier gated)

**Frontend (`FRONTEND.md`)** → all **Phase 7**
- [x] Scaffold Next.js + TypeScript; generate API client from OpenAPI — `frontend-v2/` (Next.js App Router + TS + Tailwind + TanStack Query), `npm run codegen` dumps `app.main.app.openapi()` and runs `openapi-typescript` over it (`src/lib/api-types.ts`, committed; `openapi.json` regenerated, gitignored). V1's `frontend/` untouched, still deployed.
- [x] Workspace + Document Analyzer modules (V1 parity) — upload → `/documents/[id]` workspace: per-clause actions (rewrite/risk-scan/contextualize via `block_id`, something V1's UI structurally couldn't do) + whole-document rewrite/timeline/risk-scan/ask, a sensitivity badge, and a bonus full-agent-analysis panel (`plan`/`trace`/`risk_findings`/`kg_conflicts`/faithfulness — zero backend work, the endpoint already returned everything). Verified against the real backend via curl (Gemini was intermittently 503-ing during the session; every endpoint succeeded on retry with the exact request/response shapes the client expects) plus a clean `next build`/`lint`; no browser extension was connected this session to click through it live — that's still open.
- [ ] Agent Trace Viewer (real-time via session WebSocket)
- [ ] Human-in-the-loop review queue UI
- [ ] Feature-flag `/api/v2` usage per org

**Backend** → **Phase 7**
- [~] `/api/v2/*` document-first endpoints — **first slice done** (`app/routes/v2.py`): `GET /api/v2/documents/{id}` + `POST .../{analyze,rewrite,map,ask,risk-scan,contextualize}` by `document_id`, reusing the V1 services (optional `block_id`). Session objects + per-org feature-flagging still to do.
- [ ] Notification/Webhook Service for async job completion

---

## Phase 5 — Provider Abstraction Hardening — 🟢 Complete (in code)

**Scope note**: the provider interface, packaging split, policy engine, import-linter contract, and Gemini's removal from the RAG path shipped first (`LEARNING_LOG.md` #18). Then the **self-hosted serving layer** was written (`#19`): a `gpu` docker-compose profile + `scripts/bootstrap_selfhosted.sh` for Ollama (Qwen3-8B) + TEI (bge-m3, bge-reranker-v2-m3); a `local-rerank-remote` provider; `GET /api/models/status`; `model_calls` persistence + an OpenTelemetry scaffold; the Inspect-AI / LegalBench / delta-report eval seed. Everything that's left is **operational** (actually run the compose stack), not code — see the Reality check above.

**Model Router → the real provider interface (`AI_STACK.md`)**
- [x] Define the `ModelProvider` interface + provider-neutral request/response types — `app/services/model_router/{base,types}.py` (`generate`, `embed`, `rerank`, `describe`, `is_available`). `generate_structured`/`transcribe`/`synthesize` reserved in the design, not needed by any current feature
- [x] Split providers into an always-installed core (`local.py` hashing/lexical, `openai_compat.py`) and an optional external adapter (`gemini.py`); `requirements.txt` (core, **no `google-genai`**) / `requirements-external.txt` / `requirements-local.txt`
- [x] **import-linter contract** — `tests/test_provider_isolation.py` (AST scan, CI-gated, zero new deps) + `.importlinter` config; no provider SDK imported outside `app/services/model_router/providers/`
- [x] Declarative routing-policy engine — `app/policies/routing.yaml` + `app/services/model_router/policy.py`: `task × sensitivity × capability` → ordered candidate chain; Class-A/B-only chains; Class C appended only when `EXTERNAL_PROVIDERS_ENABLED` and the tier is in `class_c_allowed_tiers`; `STRICT_LOCAL_ONLY` hard-off switch. `emergency_class_c` per-org opt-in: **not built** (no multi-tenant policy layer yet)
- [x] Log `{task, sensitivity, provider, model, reason, candidates}` on every routing decision (`router.py`); a Class C route logs at WARNING. Join to `eval_runs`: **deferred** (no `eval_runs` table yet)
- [x] Re-express hosting as **Class A / B / C** in config, code, and the policy (retired "Tier 2")
- [x] Move Gemini behind the optional external package + a Class C policy rule; **verified the product runs with `google-genai` uninstalled** (fresh-venv full-suite run) — the phase's acceptance test

**Self-host everything that isn't a large LLM**
- [x] Self-hosted embeddings — TEI serving **BAAI/bge-m3** on the GPU (`docker-compose.yml` `gpu` profile, `:8080`), reached via `local-embed-remote` (`OpenAICompatProvider` embed role, `EMBEDDING_BASE_URL`). Chain: TEI server → in-process `SentenceTransformerProvider` (`requirements-local.txt`) → `HashingEmbeddingProvider` (Class A offline floor)
- [x] **Removed the Gemini embedding dependency from the RAG path** — `contextualizer/rag.py` no longer hardcodes `gemini-embedding-001`; `embed_content()` routes via the policy (`embed_query`/`embed_corpus` tasks) to a self-hosted provider. This was the single most important deliverable
- [x] Self-hosted reranker + wired into RRF fusion — `rag/hybrid.py`'s rerank step (behind `RERANKER_ENABLED`) now routes to `local-rerank-remote` (TEI serving **BAAI/bge-reranker-v2-m3** on the GPU, `:8081`, native `/rerank`) → in-process cross-encoder → `LexicalReranker` (Class A). New `OpenAICompatProvider` `role="rerank"`
- [x] Fuse GraphRAG hits into hybrid retrieval — `rag/graph_retrieval.py` + `hybrid_search(..., graph_hits=...)`; wired into the Clause Research agent (`agents/research.py`), fail-soft when Memgraph is down. Contextualizer route wiring: follow-up (needs org context threaded to `explainer`)
- [ ] faster-whisper (ASR) / Kokoro-Piper (TTS) providers → **deferred**: no ASR/TTS feature exists in the product yet; premature to add the providers
- [x] Ollama-served small LLM as the local default — `ollama` service in `docker-compose.yml` (`gpu` profile) + `scripts/bootstrap_selfhosted.sh` pulls **qwen3:8b**. `.env.example` wires `LLM_BASE_URL`/`LLM_MODEL`. Qwen3-8B (with 14 B-AWQ as the `hard=` escalation) is **the self-hosted generation target for this project** — see the Phase 6 hardware-ceiling note.

**Observability & eval** — 🟡 initial setup shipped, backends still to stand up:
- [~] OpenTelemetry scaffold — `app/observability.py` (`OTEL_ENABLED` + `OTEL_EXPORTER_OTLP_ENDPOINT`, fail-soft) + `model_calls` routing-decision persistence (`app/db_models.py`, `model_router/telemetry.py`). Langfuse / Phoenix / Grafana LGTM / SigNoz as the actual collector: follow-up (a `docker-compose.observability.yml`)
- [~] Inspect AI + delta report — `app/eval/inspect_tasks.py` (Inspect suite seed over the gold set), `app/eval/datasets.py` (CUAD / ContractNLI loaders), `app/eval/delta_report.py` (self-hosted `local-llm` vs `gemini` on a fixed fixture, proxy metrics). `requirements-eval.txt`. promptfoo + a self-hosted judge: follow-up
- [x] Extend the CI eval gate to cover provider/policy — partially: `test_model_router.py` + `test_provider_isolation.py` + `test_models_status.py` are CI-gated and fail on a policy/interface/status regression; the full `eval_runs`-joined gate is future work
- [x] Second CI job (`core-only-smoke`) installs `requirements.txt` alone and proves the product runs with no external SDK

**Exit criteria**: Router is provider-agnostic and passes the import-linter contract ✅; embeddings/rerank self-hosted by default — **now on a real TEI/GPU deployment**, not just the interface ✅; ASR/TTS N/A; the only task routed to a commercial API by default is large-LLM generation ✅; the product runs end-to-end with no credentials and no `google-genai` ✅. Remaining: an actual observability collector wired to the OTel scaffold; promptfoo.

## Phase 6 — Self-Hosted Generation on one 16 GB card (Qwen3-8B target) — 🟡 In progress

**Hardware ceiling (project decision)**: the only GPU available is **one RTX A4000 (16 GB)** — often borrowed, sometimes not present at all (the owner's machine is a Core-i5 + 4 GB integrated GPU, i.e. CPU-only). **No 24 GB+ card, owned or rented, is planned.** So Phase 6's self-hosted generation target is **Qwen3-8B** (default) + **Qwen3-14B-AWQ** (the `hard=` escalation), *not* the 32 B / reasoning models the original roadmap assumed. Everything needing more than 16 GB is moved to "Deferred — beyond the hardware ceiling" below and to future scope.

This is a coherent choice: the docs' own thesis is that legal-domain quality comes from **RAG + KG + fine-tuned heads + the NLI verifier**, not raw model scale (`MODEL_STACK.md` "Legal-domain note"). An 8-14 B model + strong retrieval + fine-tuned classifiers is the product; Gemini (Class C) stays available for `public`/`internal` documents in the cloud profile where it measurably wins.

**Shipped (non-LLM Phase 6, `LEARNING_LOG.md` #21, #25)**: the real **NLI faithfulness head** (Verifier), **GLiNER** zero-shot NER, the **graded eval harness + cutover gate + `eval_runs`**, curated gold sets for `clause_rewrite`/`timeline_extract`/`risk_analysis` (`REWRITE_GOLD`/`TIMELINE_GOLD`/`RISK_GOLD` in `app/eval/gold_set.py`) closing the "only `qa` is graded" gap, the **8B→14B escalation ladder** (now with test coverage on both call sites, `tests/test_escalation_ladder.py`), the **fine-tuning scaffold** (`backend/training/`).

**Model serving (fits 16 GB, together: 8B ~6 GB + bge-m3 ~2.3 + bge-reranker ~2.3 + NLI ~1 GB)**
- [~] Self-hosted generation — **Ollama serving Qwen3-8B** is configured (`gpu` compose profile + `scripts/bootstrap_selfhosted.sh`); **not yet actually run** (Docker Compose + Ollama aren't installed — an ops step, not code).
- [ ] Evaluate **vLLM** serving Qwen3-8B or 14B-AWQ instead of Ollama (higher throughput, grammar-constrained JSON via xgrammar) — fits 16 GB, worth doing while the A4000 is available.
- [x] Self-hosted embeddings/reranker via **TEI** (bge-m3, bge-reranker-v2-m3) — configured in the Phase 5 bootstrap.
- [~] NLI head + GLiNER — coded as in-process providers; run on the A4000 or (slowly) on CPU.

**Progressive task cutover — each A/B-gated against the Gemini baseline before becoming default**
- [x] The gate — `app/eval/cutover_gate.py`: baseline-vs-candidate on a task's graded eval, PASS ⇒ cut over, writes `eval_runs`.
- [x] The 8B→14B escalation ladder — `hard=True` → policy `escalate_to: [local-llm-large]`; wired into `rewriter.py` (long chunks) + `chatbot.py` (multi-hop questions), both now with dedicated tests (`tests/test_escalation_ladder.py`) so a call site silently dropping `hard=` would fail CI, not just the router-level policy logic.
- [x] Curate gold sets for `clause_rewrite` / `timeline_extract` / `risk_analysis` so the gate covers them — `REWRITE_GOLD` (fact-retention + jargon-removal), `TIMELINE_GOLD` (per-event token-F1 through the real production JSON parser), `RISK_GOLD` (recall over expected risk phrases), all in `app/eval/gold_set.py` with `run_*_gold` scorers in `app/eval/tasks.py` and matching `Candidate`s in `cutover_gate.py`. `contextualize`/`agent_summary` still have no gold set — open-ended generation with citations has no clean automatic reference; `delta_report.py` remains their qualitative view.
- [ ] Actually run the cutovers once Ollama/vLLM is up. **Expected outcome, stated honestly**: Qwen3-8B/14B likely *passes* on rewrite, structure/timeline extraction (with grammar constraints), and simple grounded Q&A; likely *fails* Gemini on multi-hop reasoning and nuanced risk analysis. The resulting policy: self-hosted default for the tasks that pass; Gemini-preferred (where the tier allows) for the rest; human review otherwise. Document the per-task delta — don't pretend an 8B ties a 32B.

**CV / NLP models — on the A4000 while it's available**
- [x] GLiNER zero-shot NER — `providers/gliner_local.py`, merged with the regex floor, fail-soft.
- [ ] **Run the fine-tunes** (`backend/training/`): the clause/contract-type classifier and the deontic tagger, QLoRA on ModernBERT/Legal-BERT — **minutes each on the A4000**, then the resulting small head serves on CPU forever. This is the highest-value GPU task; do it while the card is here. **Data curated** (`LEARNING_LOG.md` #26): `training/data/clause_{train,val}.jsonl` (419/73 rows, LegalBench cuad_* + gold set) and `training/data/deontic_{train,val}.jsonl` (17/3 rows — only the seed fallback; a real `--corpus` of unlabeled contract text would meaningfully grow this and is the next data-curation step, not yet sourced). Purely a GPU-time blocker now.
- [ ] Fine-tune an InLegalBERT/ModernBERT NER head (same story).
- [ ] **maverick-coref** — the torch bump happened (torch 2.14 here) and the original CVE guard is gone (`biu-nlp/f-coref` now loads a real `.safetensors` checkpoint fine), but `fastcoref`'s own model class is unmaintained and breaks on transformers ≥ 5's `PreTrainedModel` internals (`AttributeError: ... 'all_tied_weights_keys'`). Still blocked, now on library maintenance rather than the CVE — needs a maintained coref checkpoint or a transformers-4.x pin scoped to this one dependency (untested, and would need checking against everything else that now assumes transformers 5).
- [ ] Docling / PaddleOCR layout + table extraction — mostly CPU; the clean-PDF fast path (Tesseract + quality triage) stays.

**Deferred — beyond the 16 GB hardware ceiling → future scope**
- ⛔ Qwen3-32B / Qwen3-235B-A22B as the generation default (needs 24 GB+).
- ⛔ A dedicated reasoning model (DeepSeek-R1-Distill-32B / QwQ-32B) for multi-hop — 14B does its best, else Class C / human review.
- ⛔ Qwen2.5-VL-7B/32B + olmOCR for scanned-document understanding (7B VLM is ~16 GB fp16 — tight even alone; 32B out).
- ⛔ Multi-LoRA serving (vLLM / LoRAX) — deprioritised; per-task adapters can be merged into a single served base instead.
- Revisit all of the above only if a bigger card or a rented cloud GPU box actually appears.

**Verifier**
- [x] Ship the real NLI faithfulness head — `providers/nli_local.py` (`local-nli`/`verify_nli`, Class A, in-process DeBERTa-v3-MNLI). `verifier.py` entailment-checks each summary claim; `_lexical_overlap_faithfulness` kept as the labelled fallback. 0.91 MNLI acc, 8/8 on `FAITHFULNESS_GOLD` vs lexical 6/8

**Eval**
- [x] Graded harness — `app/eval/{datasets,metrics,tasks,cutover_gate,eval_store}.py` over **LegalBench** (cuad_*/contract_nli_*) + **MNLI**; `eval_runs` table; Inspect-AI wrappers. (Script-based CUAD/ContractNLI/MAUD are dead on `datasets`≥3 — LegalBench is the path)
- [x] Enforce meet/beat-baseline before default — `cutover_gate.py`; never a false PASS on a missing provider
- [x] Per-component re-eval — `tests/test_nli_faithfulness.py` gates "NLI head beats the lexical stand-in"; `test_eval_metrics.py` locks the scorers

**Exit criteria (revised for the 16 GB ceiling)**: Qwen3-8B/14B is served and cut over for every task where the gate shows it meets or beats the Gemini baseline; for the tasks where it doesn't, the routing policy documents the delta and routes to Gemini (tier-permitting) or human review. The **air-gapped profile** runs end-to-end with no external call at the 8-14 B quality level — the honest caveat is quality on hard reasoning, not capability. The fine-tuned clause/deontic heads are trained (on the A4000) and eval-gate-promoted.

## Phase 7 — Deployment Profiles: On-Prem & Air-Gapped — 🟡 every item buildable/testable in this environment is done; infra items explicitly ⛔ blocked

**Done so far** (none needed the deployment machinery): the **dynamic Orchestrator/Planner** (`app/agents/planner.py`), the **`/api/v2` document-first API** (`app/routes/v2.py`, now including `consistency`/`simulate`), **document sensitivity tiering enforced end-to-end**, the **frontend SPA**'s four shipped slices (V1 parity, NLP/CV/KG/Model-Router exposure, post-hoc Agent Trace Viewer, and this session's human-in-the-loop review queue + eval-scores admin view + self-hosted fonts). What's left in this phase — packaging, collapsed data layer, durable execution, Memory Service, per-user RBAC, the PII redaction gate — is **explicitly blocked on infrastructure this environment doesn't have** (a Kubernetes cluster, a container registry, an air-gapped network segment), not deferred by choice. Writing that config without a target to validate it against would produce unverified artifacts.

**Security & sensitivity** (moved up from the ARCHITECTURE.md security section — it's the enforcement half of the egress boundary)
- [x] Sensitivity classification at ingestion — `app/services/sensitivity/` (rule-based Tier-0: privilege / confidentiality-phrase / PII-density / SEC-marker → tier; `internal` default). Persisted on `documents.sensitivity_tier`; eval-gated (≥90% on `SENSITIVITY_GOLD`). Classical/transformer model → `DEEP_LEARNING.md` once labelled data exists
- [x] Tier propagated through every model call — service fns take `sensitivity=`, `/api/v2` reads the persisted tier, V1 routes classify on the fly, agents carry `CaseState.sensitivity_tier`
- [x] Router enforces the tier — `policy.candidates()` drops Class C for a disallowed tier; `router._pick_and_call` fails closed (raises + ERROR log) as the last line
- [x] Org-admin override — `GET/PUT /api/v2/documents/{id}/sensitivity`, audit-logged (`audit_log.detail`); no per-user RBAC yet
- [ ] Per-user RBAC (Admin/Editor/Viewer) so "override" is a privileged action, not any org caller
- [ ] PII/PHI redaction gate before any Class C call (`ARCHITECTURE.md` §3)

**Build & supply chain** — ⛔ blocked on infra (no container registry / target cluster here to validate against)
- [ ] Produce on-prem/air-gapped builds with `legalai-providers-external` excluded; enforce with an SBOM allowlist that fails the build on any commercial-provider SDK (or outbound-calling transitive dependency)
- [ ] Zarf packaging of the full application (images + charts + manifests + model weights + seed corpus) into one installable artifact
- [ ] Model weights as signed KitOps ModelKit OCI artifacts via Harbor; no `pip` / `huggingface-cli` on the target
- [ ] OpenTofu for all IaC (migrate off any Terraform); Helm + Kustomize overlays per profile; k3s single-node target
- [ ] cosign signing + Syft SBOM + Trivy/Grype scanning for every image and model artifact
- [ ] Egress proxy / network policy for the hybrid profile: deny all outbound except configured provider endpoints; log every byte (`audit_log.egress_target`, payload hash, task, policy version, opt-in reference)

**Collapsed data layer** — ⛔ blocked on infra (needs a real deployment profile to validate "runs against either")
- [ ] Support pgvector + pgvectorscale as a Qdrant substitute (Helm-value-selected)
- [ ] Support Apache AGE or KùzuDB as a Memgraph substitute
- [ ] Support LanceDB embedded + filesystem object storage + Postgres-backed event queue for the laptop profile
- [ ] Verify the same application code runs against either data-layer profile

**Durable execution & Memory Service** — engine choice ⛔ blocked on infra (a wrong pick without a real target is expensive to unwind); Planner shipped
- [ ] Introduce a durable-execution engine — DBOS (library, Postgres-backed) default; Hatchet mid-scale; Temporal only for large multi-tenant cloud. Keep `app/agents/graph.py` engine-agnostic
- [ ] Memory Service: session tier (Redis), episodic tier (Postgres + vector store), consolidation worker with the privacy-tier gate
- [x] Dynamic Orchestrator/Planner agent, replacing the fixed Phase 4 sequence — `app/agents/{planner,registry,graph}.py` (rule-based + optional LLM + `analysis_mode` presets). Done without a durable engine (a per-doc run is seconds).
- [ ] Formalize typed tool interfaces (JSON-schema-validated) — the planner picks *agents* from a registry, not arbitrary tools yet

**Frontend SPA**
- [x] Scaffold Next.js + TypeScript; generate the API client from the OpenAPI schema — `frontend-v2/` (`LEARNING_LOG.md` #27): App Router + TS + Tailwind + TanStack Query, `npm run codegen` (`app.main.app.openapi()` → `openapi-typescript`). Not adopted this slice: shadcn/ui, Zustand (no cross-page shared state or complex primitives needed yet — plain Tailwind + hand-rolled ARIA instead).
- [x] Workspace + Document Analyzer (V1 parity) — upload → `/documents/[id]`: per-clause rewrite/risk-scan/contextualize (`block_id` — V1's UI structurally couldn't do this), whole-document rewrite/timeline/risk-scan/ask, a sensitivity badge, and a full-agent-analysis panel.
- [x] **NLP/CV/KG/Model-Router exposure** (`LEARNING_LOG.md` #28) — closed the gap between "built on the backend" and "visible anywhere": a **Structured NLP analysis** panel (`POST /api/nlp/analyze`: clause type, deontic modality, entities, defined terms, cross-refs, ambiguity flags per clause), a **Knowledge Graph** panel (`POST /api/kg/{ingest,query,conflicts}`, including an honest "Memgraph unreachable" fail-soft state), and a `/models` status page (`GET /api/models/status`). Paired backend change: `Document.quality` (CV blur/skew triage) is now persisted (`app/db.py` `_ensure_columns()`) instead of only appearing in the one-shot upload response, and shown as a low-quality-page banner in the workspace.
- [~] Provider & Model admin: which models serve which tasks, the eval scores behind the policy, the delta report, per-task/tier Class C toggles — the eval-scores half now ships (`GET /api/models/eval-runs`, most recent `eval_runs` row per task/provider, table on `/models`, confirmed live returning a real historical row from the Phase 6 A4000 session). Per-task/tier Class C toggles and the delta-report view still not built.
- [~] Model status panel: `/models` shows hosting class, capabilities, and live availability per provider; queue depth/latency aren't tracked anywhere in the backend yet, so that half is still open
- [x] Fully self-hosted frontend assets (fonts) — `frontend-v2` no longer imports `next/font/google`; `font-sans`/`font-mono` use Tailwind v4's own system-font stack. Zero files to vendor, zero third-party origin. Confirmed no `Geist`/`fonts.googleapis`/`fonts.gstatic` trace in the production build output. Plausible analytics / strict CSP / sandboxed PDF.js preview: still not done (no analytics need yet; no PDF rendering built yet to sandbox).
- [x] Sensitivity-aware rendering: a persistent tier badge on every document, sourced from `GET /api/v2/documents/{id}/sensitivity`'s real `external_providers_permitted` (not a client-side guess). No Class-C toggle exists in the UI yet to disable — nothing to enforce against there yet.
- [~] Introduce `/api/v2/*` document-first endpoints — first slice done (`app/routes/v2.py`, see Phase 4 backend note; now also `/consistency` and `/simulate`); per-org feature-flagging still to do
- [ ] Notification/Webhook Service for async job completion
- [x] **Agent Trace Viewer + human-in-the-loop review queue** — post-hoc trace viewer shipped (`AgentTraceViewer`, `LEARNING_LOG.md` #29): `AgentAnalyzeResponse.trace` already carried every step, just had no UI; now a collapsible timeline in the analysis panel. **Review queue now real** (`LEARNING_LOG.md` #32): `needs_human_review` was computed every analyze() call but never persisted — new `CaseAnalysis` table + `GET/POST /api/review-queue` + `/review` page; verified live end-to-end (insert → list → resolve → confirmed dropped from the unresolved view). ⛔ The *real-time* (session-WebSocket) trace streaming still blocked on infra (needs the Memory Service's session layer, not built).

**Exit criteria**: an air-gapped install (Zarf → disconnected k3s → working product, verified offline) validated with a pilot; a collapsed-data-layer on-prem install validated; the SPA at V1 parity plus the Agent Trace Viewer. The SPA/API/security half is done; the air-gapped-install half is blocked on infra this environment doesn't have.

## Phase 8 — Portfolio Intelligence & Research Features

**In-house models (`DEEP_LEARNING.md`)**
- [ ] Curate training data (org corpora with consent + CUAD/ContractNLI)
- [ ] Weak-supervision labelling pass via distilabel with a **self-hosted teacher** (batch/offline)
- [ ] Legal-expert review of weak labels in Argilla
- [ ] Train the Risk Scoring Model (LightGBM, CPU — blocked on labelled data, not hardware); integrate SHAP
- [ ] Finalize the fine-tuned clause/contract-type classifier and NER head; eval-gate promotion
- [ ] Document Sensitivity Classifier — classical (TF-IDF + linear) first; fine-tune a transformer only if that underperforms
- [ ] Legal Clause Embedding Model — contrastive fine-tune (`NOVELTY.md` #3) with hard-negative mining (GPU training step uses Phase 6 infra)
- [ ] Redline Acceptance Predictor — per-org, DPO/classifier over redline history (opt-in, org-scoped, never pooled)
- [ ] MLflow registry + DVC data versioning; eval-gated model promotion in CI/CD
- [ ] Model cards for every trained model (intended use, data provenance, jurisdictions/contract types covered, eval scores, limitations)

**Portfolio agents (`AGENTS.md`, `KNOWLEDGE_GRAPH.md`)**
- [ ] Bitemporal graph versioning (valid time / transaction time) — the Phase 3 gap
- [x] Cross-Document Consistency agent (embedding-similarity baseline → learned `NOVELTY.md` #1) — `app/services/consistency.py` + `POST /api/v2/documents/{id}/consistency` + `ConsistencyPanel` (`LEARNING_LOG.md` #30). 5 new service tests + 2 route tests (200 pass total). Caught a real cross-document match live that the KG's exact-term check can't see.
- [x] Simulation agent (deterministic discrete-event baseline → Monte-Carlo `NOVELTY.md` #2) — `app/services/simulation.py` + `POST /api/v2/documents/{id}/simulate` + `SimulationPanel` (`LEARNING_LOG.md` #31). Only resolved absolute dates become events (bare durations stay honestly unresolved, matching `temporal.py`'s existing design). Portfolio-scope `TRIGGERED_BY`-graph + Monte-Carlo version deferred — needs KG schema growth (`Obligation`/`TRIGGERED_BY` nodes) that doesn't exist yet. 5 new service tests + 2 route tests (207 pass total).
- [ ] Negotiation/Drafting agent — static org-configured preferences first; learned playbook (`NOVELTY.md` #4) once redline history exists
- [ ] Negotiation Studio frontend (Yjs collaborative editing)
- [ ] Risk Dashboard spider/radar chart (closes the V1 README promise)
- [ ] Knowledge Graph Explorer frontend (Cytoscape.js)

**Research track (`NOVELTY.md`) — each item independently gated**
- [ ] Idea #1 (Deontic GAT conflict detection): literature/patent search + architecture design (CPU); GNN training uses Phase 6 GPU
- [ ] Idea #2 (Temporal obligation simulation): CPU-only — prototype auto-constructed simulation, validate against manually-modelled scenarios
- [ ] Idea #3 (Legal-semantic fingerprinting): hard-negative pair construction (CPU); contrastive training uses Phase 6 GPU
- [ ] Idea #4 (Adaptive negotiation playbook): counterfactual fingerprint-delta attribution (CPU); Redline Acceptance Predictor — classical model first
- [ ] Idea #5 (Deontic-structure-aware ablation): CPU-only — runs against the existing LightGBM risk model
- [ ] For any idea advancing past prototype: commission a formal prior-art search via qualified patent counsel before further investment or disclosure
- [ ] For any idea that validates: target a benchmark contribution and/or a workshop paper (NLLP @ *ACL, JURIX, ICAIL) — see `NOVELTY.md`'s publication strategy

**Exit criteria**: portfolio-level contradiction detection and obligation simulation live (established-technique first, novel-mechanism after its gate); ≥1 in-house model in production at/above its baseline; ≥1 `NOVELTY.md` idea with a validated benchmarked prototype.

## Phase 9 — Scale, Memory Maturity & Enterprise Hardening

- [ ] Semantic memory tier (cross-document, per-org) with privacy-tier gating
- [ ] Procedural memory tier (Redline Acceptance Predictor productionized, per-org isolation)
- [ ] Multi-tenant cloud scale: Qdrant sharding, per-org graph partitioning, GPU autoscale on queue depth, Postgres read replicas
- [ ] Adopt Temporal for the cloud profile if DBOS/Hatchet hit a ceiling
- [ ] Validate hybrid VPC deployment with a pilot customer
- [ ] Validate on-prem and air-gapped deployments with pilot customers (one each)
- [ ] SOC 2 Type II readiness program
- [ ] GDPR data-subject export/delete workflows
- [ ] Full cost/latency review of the routing policy using a quarter of production data; right-size the model fleet; tune quantization / speculative decoding / batching
- [ ] Publish the `/api/v1` deprecation timeline once `/api/v2` has full parity

## Continuous / cross-cutting (all phases)

- [~] Every prompt/model/provider/routing-policy change passes the eval gate before merge — `tests/test_eval_gate.py` (clause-type, deontic, sensitivity accuracy) + `test_model_router.py` + `test_provider_isolation.py` are CI-gated; the full `eval_runs`-joined regression gate is future work
- [x] The import-linter contract stays green — `tests/test_provider_isolation.py` (AST scan) + `.importlinter`; forbidden roots now include `transformers`, `gliner`, `fastcoref`
- [ ] Every sensitive-tier code-path change gets a security review, with extra scrutiny on Class C egress
- [ ] Model cards maintained for every trained model (`DEEP_LEARNING.md`)
- [ ] Quarterly drift-monitoring review of production eval scores against the gold benchmark
- [ ] Keep flagging, per item, *why* something is deferred: "GPU", "no training data yet", "not needed yet", "separate scope" are four different reasons with four different follow-ups
