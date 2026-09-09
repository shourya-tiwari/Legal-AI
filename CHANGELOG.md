# Changelog

All notable changes to the LegalAI platform. Backend and frontend tracked together;
the backend is feature-complete for the current environment (see `docs/v2/ROADMAP.md`),
so ongoing work is the frontend rebuild toward a production-grade SaaS UI.

Format loosely follows [Keep a Changelog](https://keepachangelog.com/). Dates are ISO-8601.

## [Unreleased]

### Frontend — M1: Foundation & design system
- **Design system** — `frontend/src/components/ui/` (30 Radix-backed primitives: button, card,
  badge, dialog, sheet, dropdown-menu, popover, tooltip, tabs, select, accordion, table, command,
  toast, skeleton, switch, checkbox, progress, scroll-area, avatar, alert, empty/error states,
  stat, …). oklch design tokens with a real light + dark theme (`next-themes`), tuned typography,
  radius, and shadow scales.
- **App shell** — collapsible sidebar with nav groups, sticky topbar, ⌘K command palette (`cmdk`),
  theme toggle, user menu; `(marketing)` and `(app)` route groups with their own layouts.
- **Data layer** — a fully typed `lib/api.ts` client covering every backend endpoint, with
  optional bearer auth (works token-less when `AUTH_REQUIRED=false`), `XMLHttpRequest` upload
  progress, and structured `ApiError`. Zustand stores: client-side document library, AI-assistant
  conversation history, and UI preferences (all `localStorage`-persisted). Centralised query keys
  and formatters.
- **Pages** — rebuilt Dashboard, Documents (library, grid/list/search/filter/tags), Upload
  (dropzone + progress), Workspace overview, Review Queue, and Model Router in the new system.
  Full marketing skeleton: Home (hero, pipeline, features, security, CTA), Features, Architecture,
  Research (the 5 `NOVELTY.md` ideas), Docs hub, About (case study), About/Developer (portfolio),
  Contact; plus `/login`.
- **Dependencies added** — framer-motion, lucide-react, sonner, cmdk, next-themes, zustand,
  react-hook-form, zod, `@tanstack/react-table`, `@xyflow/react`, recharts, react-markdown,
  date-fns, class-variance-authority, tailwind-merge, and the Radix primitive set.
- Removed the old V1-scaffold panel components; the V1 `SiteHeader` and one-page workspace.

### Added
- **Frontend implementation plan** (`docs/v2/FRONTEND_PLAN.md`) — complete backend→frontend
  capability map, information architecture, design-system spec, and a 9-milestone delivery plan
  for rebuilding `frontend/` into a world-class Legal-AI platform UI.
- This `CHANGELOG.md`.

### Notes
- `openapi-typescript` (dev-only, used by `npm run codegen`) pulls a transitive `js-yaml`
  advisory (`GHSA-2883-xcg3-v3hh`). Not shipped in the app bundle; tracked for a future override.

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
