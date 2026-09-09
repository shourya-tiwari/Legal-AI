# Changelog

All notable changes to the LegalAI platform. Backend and frontend tracked together;
the backend is feature-complete for the current environment (see `docs/v2/ROADMAP.md`),
so ongoing work is the frontend rebuild toward a production-grade SaaS UI.

Format loosely follows [Keep a Changelog](https://keepachangelog.com/). Dates are ISO-8601.

## [Unreleased]

### Docs
- **README** rewritten as a full project README — architecture (mermaid),
  feature tour, a zero-config quick start plus the docker / self-hosted-GPU
  paths, a complete configuration reference, API examples (V1 + V2 + KG),
  project layout, the four deployment profiles, the research track, and the
  roadmap. Added an MIT `LICENSE`.

### Frontend — M11: UX/UI consistency pass
- No behaviour changes — standardising drift found in a full page-by-page audit.
- **`<RouteTabs>`** — the workspace and admin tab bars were two copies that had
  diverged on hover styling; now one shared component.
- **Card body padding** for header-less cards standardised to `pt-5` (was a mix
  of `pt-4` / `pt-5` / `pt-6`); **page rhythm** standardised to `space-y-6`.
- **CardTitle icons** were sporadic (one card per view carried one) — removed
  the outliers so each view is internally consistent; admin keeps its full set.
- **Class C** hosting badge is now `warning`, matching how "leaves the perimeter"
  is signalled everywhere else.
- Native `window.prompt` for adding a document tag → a proper dialog; the
  document-card menu trigger uses `<MoreHorizontal>` like the workspace header;
  the risk-page clear-filter affordance is a `<Button>`, not a bare link.
- Page title "Human review queue" → "Review Queue" (matches the nav).
- Removed dead code: a misleading icon re-export, an unused testimonials
  section, an always-"unknown" admin line, a disabled "coming soon" button.

### Frontend — M10: unified information architecture

The marketing site and the application stopped behaving like two products.

- **Cross-layout navigation** — the app sidebar gains a **Resources** group
  (Documentation, Architecture, Research, About — these bridge into the
  `(marketing)` layout) and a footer with **Settings**, **Back to website**,
  and **GitHub**. The topbar has a **Resources** dropdown; the user menu
  regains Profile / Settings / Documentation / Marketing site; the command
  palette mirrors all of it. The public header now carries a persistent
  **Open dashboard** alongside **Get started**, so the app is one click from
  any marketing page.
- **Guided onboarding** — a new `/welcome` route (upload / try-sample /
  explore, plus a five-stage pipeline primer). `lib/sample-contract.ts` +
  `<TrySampleButton>` upload a synthetic mutual NDA through the real
  `POST /api/upload` and open its workspace — nothing stubbed. "Get started"
  now routes here instead of dropping first-time users into an empty
  dashboard.
- **Dashboard** — the empty state is a teaching experience (welcome hero,
  quick links to docs/features/architecture, a capability preview) with
  platform status kept secondary. The populated dashboard is unchanged.
- **Sidebar groups** — Workspace (Dashboard, Upload, Documents, AI Assistant)
  / Analysis (Review Queue, Knowledge Graph, Evaluation) / Platform (Model
  Router, Analytics, Admin) / Resources / Settings.
- **Marketing landing page** — expanded from hero + cards to the full product
  website: how-it-works, architecture overview, security & privacy, AI
  pipeline, knowledge graph, risk analysis, negotiation agent, evaluation
  framework, research contributions, screenshots (`<BrowserFrame>` previews
  built from the live design system), technology stack, roadmap, about
  teasers, FAQ, CTA — every section backed by a real backend capability.
- **About page** — rewritten as an engineering case study: why / vision /
  design philosophy, five architecture decisions with the problem each
  solved, research inspiration, technologies, the eight-phase development
  journey, statistics, and a Future-work section that splits next-phase vs.
  GPU-blocked vs. infra/human-blocked work explicitly.
- **Footer** — Product / Platform / Resources / Project columns, an MIT
  License link, and a "Built by Shourya Tiwari" line.
- **Motion** — a short per-navigation enter transition via
  `(app)/template.tsx`, `prefers-reduced-motion`-aware.

### Frontend — M2 + M5 + M9: marketing polish, consistency, hygiene
- **Home page** grew a "by the numbers" strip, a "why this platform" section, a testimonials
  placeholder (honest — it's a portfolio project), and an FAQ accordion. Scroll-reveal motion via
  Framer Motion, `prefers-reduced-motion`-aware.
- **Cross-document consistency** — a previously-unsurfaced endpoint. The workspace Overview now
  has a consistency card: embed this document's deontic clauses, compare against the rest of the
  library, flag semantic matches and active modality conflicts.
- **`.gitattributes`** — `text=auto eol=lf` normalisation (ends the CRLF churn), binary-asset
  markers, `linguist-generated` on `api-types.ts` / `package-lock.json` / training data.
- **`next.config.ts`** — `poweredByHeader: false`, `compress`, `optimizePackageImports` for
  lucide/recharts/date-fns. React Flow and Recharts are already `next/dynamic`-lazy at their call
  sites.

### Frontend — M7 + M8: Ops, admin, settings
- **Evaluation** (`/evaluation`) — most-recent eval run per task/provider with candidate-vs-baseline
  score bars and cutover pass/fail; admin "run delta report" (real provider calls).
- **Analytics** (`/analytics`) — Recharts provider-latency (coloured by hosting class), Class-C
  egress by provider, evaluation pass rate by task, recent external dispatches, and local activity.
- **Admin** (`/admin/*`, tabbed) — health tiles + provider reachability + `create_api_key.py`
  command; Users (list/create/revoke); Models (per-task Class-C kill switches); Egress Log (the
  full SHA-256 audit trail with PII-redaction counts); Feature Flags + completion webhook.
- **Settings** (`/settings`, tabbed) — negotiation playbook editor, appearance, keyboard-shortcut
  reference, and local-data controls.
- **Profile** (`/profile`), **`/login`** (session auth, graceful when auth is off), and the
  portfolio **Knowledge Graph** (`/knowledge-graph`) — term usage across ingested documents +
  candidate cross-document conflicts + an as-of time-travel control.

### Frontend — M6: AI Assistant
- `/assistant` — a full chat experience over the frozen single-turn `/ask` endpoint. Conversation
  list (create/rename/delete/search, `localStorage`-persisted), per-conversation document context,
  `react-markdown` + `remark-gfm` rendering, faithfulness badge + unsupported-claims callout per
  answer, suggested prompts, Markdown export, collapsible sidebar. No fake token streaming.

### Frontend — M4: Document workspace
- **Tabbed workspace** at `/documents/[id]` — a shared `WorkspaceProvider` (document +
  sensitivity queries) and `WorkspaceChrome` (header, 8-tab bar, quality warning, version
  history, sensitivity override dialog, KG ingest). Eight tabs, all backed by real endpoints:
  - **Overview** — text viewer with in-document search/highlight, plain-English rewrite dialog,
    agent-analysis summary card, clause preview.
  - **Clauses** — `POST /api/nlp/analyze` rendered as rich `ClauseCard`s (deontic modality,
    entities, defined terms, cross-references, temporal expressions, ambiguity flags), per-clause
    rewrite + "explain for my situation" (contextualize) dialogs, clause-type filter, AI-escalation
    toggle.
  - **Risk** — Recharts radar over the 8-category dashboard with click-to-drill-down, plus the
    AI + keyword scan.
  - **Timeline** — dated-obligation timeline from `simulate` (past/upcoming/future) with a
    configurable reference date and warning window, plus the descriptive timeline and structure
    tree from `map`.
  - **Negotiation** — redline diff of each deviation from the org playbook, local accept/reject,
    Markdown redline export; honest empty state linking to Settings when no preferences are set.
  - **Graph** — React Flow (`@xyflow/react`) knowledge-graph canvas with ingest/refresh,
    portfolio-link (`SAME_AS`) highlighting, minimap, and a fail-soft "graph offline" state.
  - **Agents** — planner plan + rationale, verifier verdict (faithfulness, unsupported claims,
    fabricated citations, `needs_human_review`), risk/KG findings, and an accordion execution
    trace; analysis-mode and AI-planner controls.
  - **Ask** — a grounded per-document Q&A thread with a faithfulness badge and unsupported-claim
    callouts.
- Shared `useAnalysis` hook caches the `analyze()` result across the Agents and Negotiation tabs.

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
