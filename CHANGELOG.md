# Changelog

All notable changes to the LegalAI platform. Backend and frontend tracked together;
the backend is feature-complete for the current environment (see `docs/v2/ROADMAP.md`),
so ongoing work is the frontend rebuild toward a production-grade SaaS UI.

Format loosely follows [Keep a Changelog](https://keepachangelog.com/). Dates are ISO-8601.

## [Unreleased]

### Added
- **Frontend implementation plan** (`docs/v2/FRONTEND_PLAN.md`) — complete backend→frontend
  capability map, information architecture, design-system spec, and a 9-milestone delivery plan
  for rebuilding `frontend/` into a world-class Legal-AI platform UI.
- This `CHANGELOG.md`.

---

## History

Prior work is recorded per-phase in `docs/v2/ROADMAP.md` / `docs/v2/TASKS.md` and, in detail,
in the append-only engineering journal `LEARNING_LOG.md` (entries #1–#62). Highlights:

- **Phases 0–4** — V1 hardening; FastAPI re-platform (Postgres/Redis, org auth); CPU NLP/CV
  pipelines producing structured `ClauseObject`s; Knowledge Graph + hybrid RAG; a planner-driven
  LangGraph agent pipeline with a real NLI faithfulness verifier.
- **Phase 5** — provider-agnostic Model Router; embeddings/rerank self-hosted; Gemini demoted to
  an optional Class C plugin; import-linter contract.
- **Phase 6** — self-hosted generation target (Qwen3-8B/14B); graded eval harness + cutover gate;
  GLiNER NER; NLI head.
- **Phase 7** — document sensitivity tiering (end-to-end Class C egress enforcement); PII
  redaction gate + egress audit trail; per-key RBAC + per-user identity; on-prem/air-gapped
  packaging; KùzuDB collapsed data layer; DBOS durable execution; three-tier Memory Service;
  the first Next.js SPA slice.
- **Phase 8** — bitemporal graph versioning; Cross-Document Consistency + Simulation baselines;
  Negotiation/Drafting agent; Risk Dashboard + KG Explorer; classical training runs
  (sensitivity, risk — eval-gated, not promoted); MLflow + DVC; eval-gated promotion gate;
  all five `NOVELTY.md` CPU prototypes.
- **Post-Phase-8** — dev-environment repair (Python 3.13); backend polish (error-handling
  hardening, CV redaction wiring, dead-code removal); repo hygiene (V1 frontend removed,
  `frontend-v2/` → `frontend/`).
