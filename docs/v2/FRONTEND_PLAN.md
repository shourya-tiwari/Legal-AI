# Frontend Implementation Plan — LegalAI Platform

> **Status**: living plan for the `frontend/` rebuild (Next.js 16 / React 19 / Tailwind v4).
> Goal: a world-class, production-grade Legal-AI SaaS UI on top of the **feature-complete,
> frozen backend**. No backend API or architecture changes (bug fixes only).

This document maps **every backend capability to a frontend surface**, defines the design
system and information architecture, and breaks the work into shippable milestones.

---

## 1. Constraints derived from the backend

The backend is a separate FastAPI origin reached over `fetch` (`NEXT_PUBLIC_API_BASE_URL`).
`AUTH_REQUIRED=false` by default; when on, a `sess_`/`lai_` bearer token is sent. The SPA is
therefore **client-rendered with TanStack Query** for all data; RSC is used only for static
marketing content.

What the backend **does not** provide — and how the frontend handles it honestly:

| Gap | Frontend approach |
|---|---|
| No `GET /documents` list endpoint | **Client-side document library** (Zustand + `localStorage`): every upload records `{id, filename, uploaded_at, tier, tags}`; the library hydrates each entry with `GET /v2/documents/{id}`. Clearly labelled "documents uploaded from this browser". |
| `/ask` is single-turn, stateless, **non-streaming** JSON | AI Assistant keeps **conversation history in `localStorage`**; each turn is an independent grounded call with the selected document as context. No fake token streaming — a real "thinking" state with the actual request lifecycle. |
| No agent-trace history endpoint (only the `analyze()` response + the review queue) | Agent Trace reads the **cached `analyze()` result** (TanStack Query) or a **review-queue item**. Post-hoc only — real-time trace needs a WebSocket the backend doesn't have (documented in ROADMAP Phase 7). |
| No usage-metrics endpoint | Analytics is built from **real sources**: `models/status` latency, `models/eval-runs`, `audit/egress`, review-queue counts, plus client-tracked local activity. |
| API keys are created by a **script** (`create_api_key.py`), not an API | Admin → API Keys shows the exact command + explains the model; it does not pretend to mint keys. |
| Class C egress log is **not org-scoped** (documented backend gap) | Surfaced as-is with a note. |

Everything else has a real endpoint (see §2).

---

## 2. Backend capability → frontend map

### Documents & extraction
| Endpoint | Frontend surface |
|---|---|
| `POST /api/upload` | `/documents/upload` (dropzone, progress) + quick-upload dialog (⌘U) |
| `GET /api/v2/documents/{id}` | Workspace loader — metadata, blocks, `full_text`, `quality`, sensitivity |
| `GET /api/v2/documents/{id}/original` | "Download original" action + PDF/text viewer source |
| `GET/PUT /api/v2/documents/{id}/sensitivity` | Sensitivity panel — tier, signals, rationale, **admin override** dialog with reason |
| `POST /api/nlp/analyze` | `/documents/[id]/clauses` — rich `ClauseObject` list (type, deontic modality, entities, defined terms, cross-refs, temporal, ambiguity) with `use_ai_escalation` toggle |

### Analysis
| Endpoint | Frontend surface |
|---|---|
| `POST /api/v2/documents/{id}/analyze` | `/documents/[id]/agents` — planner plan + rationale, agent trace, risk findings, KG conflicts, summary, faithfulness verdict, unsupported claims, invalid citations, negotiation suggestions, `needs_human_review`. `analysis_mode` (full/quick/risk_only/extract_only) + `use_ai_planner` controls. Result cached and reused across the workspace. |
| `POST /api/v2/documents/{id}/rewrite` | Workspace "Plain English" — whole-doc or per-clause (`block_id`), side-by-side |
| `POST /api/v2/documents/{id}/map` | `/documents/[id]/timeline` — document structure tree + descriptive timeline |
| `POST /api/v2/documents/{id}/simulate` | `/documents/[id]/timeline` — dated obligation events (past/upcoming/future), configurable warning window + reference date |
| `POST /api/v2/documents/{id}/risk-scan` | Workspace "Risk" quick scan — keyword + contextual flags per clause |
| `POST /api/v2/documents/{id}/risk-dashboard` | `/documents/[id]/risk` — 8-category radar, severity, per-category drill-down, clause heatmap |
| `POST /api/v2/documents/{id}/ask` | `/documents/[id]/ask` + AI Assistant — grounded answer + faithfulness badge + unsupported claims |
| `POST /api/v2/documents/{id}/contextualize` | Workspace clause action — role/location/contract-type/interests/tone form → personalized explanation + KB citations |
| `POST /api/v2/documents/{id}/consistency` | `/documents/[id]` panel + `/analytics` — cross-document contradiction findings with similarity + modality conflict |

### Negotiation
| Endpoint | Frontend surface |
|---|---|
| `analyze()` → `negotiation_suggestions` | `/documents/[id]/negotiation` — **Negotiation Studio**: side-by-side current vs. preferred language, unified diff (`diff_lines`), rationale, similarity, accept/reject (local state), export (`.md`/`.txt`) |
| `GET/PUT /api/org/settings` → `negotiation_preferences` | `/settings` — per-clause-type preferred-language editor (drives the agent) |

### Knowledge Graph
| Endpoint | Frontend surface |
|---|---|
| `POST /api/kg/ingest` | Workspace "Add to knowledge graph" action (idempotent) |
| `GET /api/kg/documents/{id}/graph` | `/documents/[id]/graph` — **React Flow** node/edge graph, zoom/pan/search, node inspector, portfolio-linked-term highlight |
| `POST /api/kg/query` `{term, as_of?}` | `/knowledge-graph` — portfolio term explorer: every clause across docs using a term, with an **as-of** time-travel control |
| `POST /api/kg/conflicts` `{term}` | `/knowledge-graph` — candidate cross-document obligation/prohibition conflicts |
| `POST /api/kg/supersede` + `GET /api/kg/documents/{id}/versions` | Workspace "Version history" — supersede dialog + `SUPERSEDES` chain timeline |

All KG surfaces render an honest **"knowledge graph offline"** state when `kg_available: false`.

### Review, evaluation, model router
| Endpoint | Frontend surface |
|---|---|
| `GET /api/review-queue` `?include_resolved` | `/review` — table, unresolved-first, filters, detail drawer |
| `POST /api/review-queue/{id}/resolve` | `/review` — resolve action (admin/editor) with reviewer note |
| `GET /api/models/status` | `/models` + `/admin/health` + dashboard widget — provider cards (hosting class A/B/C, capabilities, availability, `leaves_perimeter`, models, recent latency), policy version, external-providers/strict-local flags |
| `GET /api/models/eval-runs` | `/evaluation` — most-recent run per task/provider, cutover-gate pass/fail, baseline vs. candidate, metrics |
| `GET/PUT/DELETE /api/models/class-c-overrides` | `/admin/models` — per-task Class C kill switches (admin) |
| `POST /api/models/delta-report` | `/evaluation` — "Run delta report" (admin; makes real calls) → self-hosted-vs-external comparison table |
| `GET /api/audit/egress` | `/admin/egress` — every Class C dispatch: task, provider, model, policy version, payload SHA-256, redacted PII categories |

### Auth & org
| Endpoint | Frontend surface |
|---|---|
| `POST /api/auth/login` / `logout` | `/login` + user menu — token stored in `localStorage`, sent as bearer; graceful when auth is off |
| `POST/GET /api/auth/users`, `POST /api/auth/users/{id}/revoke` | `/admin/users` — list, create (admin), revoke |
| `GET/PUT /api/org/settings` | `/settings` — feature flags (`api_v2_enabled`, …), webhook URL, negotiation preferences |
| `GET /` health | dashboard + `/admin/health` reachability check |

---

## 3. Information architecture & routing

Two route groups under `frontend/src/app/`:

```
(marketing)/                      – PublicHeader + Footer, mostly RSC
  page.tsx                        /                 Landing
  features/page.tsx              /features
  architecture/page.tsx         /architecture      interactive diagram
  research/page.tsx             /research          NOVELTY.md — 5 ideas
  docs/page.tsx                 /docs              concept hub
  about/page.tsx                /about             project case study
  about/developer/page.tsx      /about/developer   portfolio
  contact/page.tsx              /contact

(app)/                            – AppShell: sidebar + topbar + command palette
  dashboard/page.tsx            /dashboard
  assistant/page.tsx            /assistant         + /assistant/[conversationId]
  documents/page.tsx            /documents         library (grid/list)
  documents/upload/page.tsx     /documents/upload
  documents/[id]/layout.tsx     – workspace tab bar + shared analysis cache
    page.tsx                    /documents/[id]              Overview
    clauses/page.tsx            /documents/[id]/clauses
    risk/page.tsx               /documents/[id]/risk
    timeline/page.tsx           /documents/[id]/timeline
    negotiation/page.tsx        /documents/[id]/negotiation
    graph/page.tsx              /documents/[id]/graph
    agents/page.tsx             /documents/[id]/agents
    ask/page.tsx                /documents/[id]/ask
  knowledge-graph/page.tsx      /knowledge-graph   portfolio term explorer
  review/page.tsx               /review
  evaluation/page.tsx           /evaluation
  models/page.tsx               /models
  analytics/page.tsx            /analytics
  admin/layout.tsx              – admin tab bar
    page.tsx                    /admin             overview / health
    users/page.tsx              /admin/users
    models/page.tsx             /admin/models      class-C overrides + policy
    egress/page.tsx             /admin/egress
    flags/page.tsx              /admin/flags
  settings/page.tsx             /settings
  profile/page.tsx              /profile

login/page.tsx                  /login             (no shell)
```

Sidebar groups: **Workspace** (Dashboard, Assistant, Documents) · **Analysis** (Review, Knowledge Graph, Evaluation) · **Platform** (Models, Analytics, Admin) · footer (Settings, Profile, theme, docs link).

---

## 4. Design system

**Language**: precise, calm, dense-but-breathable — Linear/Stripe/Vercel register. Dark-first with a real light theme. One accent (indigo→violet), semantic colors for risk (emerald/amber/rose), sensitivity tiers (slate/sky/amber/rose), and hosting classes (A/B/C).

**Tokens** (`globals.css`, CSS variables, `:root` + `.dark`): background/surface/elevated/overlay, border/ring, foreground/muted/subtle, primary + 5 semantic scales, radius (sm/md/lg/xl/2xl), shadow (xs→xl, all subtle), font sizes with tuned line-heights, mono stack for code/hashes/IDs.

**Primitives** (`components/ui/`, Radix-backed, shadcn-style API): `button`, `card`, `badge`, `input`, `textarea`, `label`, `select`, `checkbox`, `switch`, `radio-group`, `slider`, `dialog`, `sheet`, `drawer`, `dropdown-menu`, `popover`, `tooltip`, `hover-card`, `context-menu`, `tabs`, `accordion`, `collapsible`, `table` (+ `data-table` with TanStack Table), `command`, `toast` (sonner), `skeleton`, `separator`, `scroll-area`, `progress`, `avatar`, `breadcrumb`, `alert`, `kbd`, `empty-state`, `error-state`, `code-block` (Shiki), `stat`, `spinner`.

**Composite** (`components/`): `AppShell`, `Sidebar`, `Topbar`, `CommandPalette`, `GlobalSearch`, `PageHeader`, `PublicHeader`, `PublicFooter`, `SensitivityBadge`, `HostingClassBadge`, `FaithfulnessBadge`, `RiskMeter`, `RadarChart`, `DeonticTag`, `ClauseCard`, `DiffView`, `GraphCanvas` (React Flow), `TraceFlow`, `MarkdownMessage`, `Dropzone`, `ThemeToggle`, `Logo`.

**Motion**: `framer-motion` — page transitions (subtle fade/slide), list stagger, panel expand, number tick-ups, shared-layout for tab indicator. Respect `prefers-reduced-motion`.

**Icons**: `lucide-react` throughout.

---

## 5. Tech stack / dependencies

Already present: `next@16`, `react@19`, `@tanstack/react-query`, `tailwindcss@4`, `cytoscape`.

To add: `@radix-ui/react-*` (primitives), `class-variance-authority`, `clsx`, `tailwind-merge`,
`tailwindcss-animate`, `lucide-react`, `framer-motion`, `sonner`, `cmdk`, `next-themes`,
`zustand`, `react-hook-form`, `zod`, `@hookform/resolvers`, `@tanstack/react-table`,
`@tanstack/react-query-devtools`, `@xyflow/react` (React Flow v12), `recharts`, `date-fns`,
`react-markdown`, `remark-gfm`, `rehype-raw`, `shiki`, `react-pdf` (lazy), `@monaco-editor/react` (lazy).

**Performance**: `next/dynamic` for React Flow, Recharts, Monaco, react-pdf, cytoscape; route-level
code splitting via the route groups; TanStack Query cache + `staleTime`; `Link` prefetch; skeletons
via `loading.tsx` per heavy route; `next/image` for illustrations; target Lighthouse ≥ 95
perf/a11y/best-practices on marketing, ≥ 90 on app routes.

---

## 6. Milestones

Each milestone: implemented · responsive (sm→2xl) · a11y (keyboard, focus, ARIA, contrast) ·
`npm run lint` + `npm run build` clean · docs updated · committed.

| # | Milestone | Scope |
|---|---|---|
| **M0** | Plan ✅ | this document + `CHANGELOG.md` |
| **M1** | Foundation ✅ | deps, design tokens + light/dark, 30 `components/ui/` primitives, `AppShell`/`SidebarNav`/`Topbar`, ⌘K command palette, `PublicHeader`/`Footer`, `(marketing)`/`(app)` route groups, `lib/` (typed api client + optional auth + query keys + Zustand stores + formatters), sonner toasts, error/not-found/loading boundaries. Rebuilt Dashboard, Documents, Upload, Workspace-overview, Review, Model Router; full marketing skeleton (Home, Features, Architecture, Research, Docs, About, About/Developer, Contact) + `/login`. `READY_ROUTES` gate keeps every commit 404-free as later milestones add pages. |
| **M2** | Marketing | Landing (hero, animated bg, feature cards, architecture preview, workflow viz, security, tech, research highlights, benchmarks, FAQ, CTA, footer) · Features · Architecture (interactive) · Research · Docs hub · About (case study) · About/Developer (portfolio) · Contact |
| **M3** | Dashboard + Documents | `/dashboard` (recent, review count, model status, eval summary, risk overview, quick actions) · `/documents` (grid/list, search, filter, tags, dropzone) · `/documents/upload` · document-library store |
| **M4** | Workspace ✅ | `documents/[id]/layout.tsx` — `WorkspaceProvider` (shared doc/sensitivity queries) + `WorkspaceChrome` (header, 8-tab bar, quality/version/override/KG-ingest actions). Tabs: **Overview** (text viewer w/ in-doc search, rewrite dialog, analysis summary, clause preview), **Clauses** (`nlp/analyze` — rich `ClauseCard` w/ deontic/entity/xref/temporal/ambiguity chips, per-clause rewrite + contextualize dialogs, type filter, AI-escalation toggle), **Risk** (recharts radar + category drill-down + AI/keyword scan), **Timeline** (dated-obligation timeline from `simulate` + descriptive timeline + structure from `map`, configurable ref date / window), **Negotiation** (redline diff, accept/reject, markdown export), **Graph** (React Flow KG canvas, ingest/refresh, portfolio-link highlight, offline state), **Agents** (planner plan, verifier verdict, findings, accordion trace; mode + AI-planner controls), **Ask** (grounded per-doc Q&A thread w/ faithfulness + unsupported-claims). Shared `useAnalysis` hook caches the `analyze()` result across the Agents + Negotiation tabs. |
| **M5** | Analysis polish | React Flow agent-trace DAG (currently an accordion), diff-viewer refinement, KG-explorer layout/search upgrades, risk severity heatmap, cross-document consistency panel. |
| **M6** | AI Assistant ✅ | `/assistant` — conversation list (create/rename/delete/search, all `localStorage`), per-conversation document-context selector, `react-markdown`+`remark-gfm` rendering, faithfulness badge + unsupported-claims per answer, suggested prompts, export to Markdown, collapsible sidebar. No fake token streaming (the frozen `/ask` is JSON). |
| **M7+M8** | Ops + Admin ✅ | **Evaluation** (`/evaluation`): eval-runs table with candidate-vs-baseline score bars + cutover pass/fail; admin delta-report. **Analytics** (`/analytics`): Recharts provider-latency, Class-C egress by provider, eval pass rate, recent dispatches, local activity. **Admin** (`/admin/*` tabbed): overview/health, users (list/create/revoke), models (Class-C kill switches), egress log (SHA-256 audit trail + redaction counts), feature flags + webhook. **Settings** (`/settings` tabbed): negotiation playbook editor, appearance, shortcut reference, local-data controls. **Profile**, **`/login`**, and the portfolio **Knowledge Graph** (`/knowledge-graph`): term-usage across ingested docs + candidate conflicts + as-of time-travel. |
| **M2** | Marketing polish | FAQ, benchmarks strip, testimonials placeholder, "why this platform", subtle hero motion, interactive architecture. |
| **M5** | Analysis polish | Cross-document consistency panel (a currently-unsurfaced endpoint), diff-viewer refinement, KG-explorer layout upgrades. |
| **M9** | Polish | `.gitattributes` (LF normalisation), per-route `loading.tsx`/`error.tsx`, keyboard shortcuts, responsive + a11y audit, perf (lazy heavy libs — done for React Flow/Recharts — bundle check, Lighthouse), final docs sync. |

Backend docs to keep synced after every milestone: `README.md`, `ROADMAP.md`, `TASKS.md`,
`ARCHITECTURE.md`, `CLAUDE.md`, `CHANGELOG.md`, `LEARNING_LOG.md`, `docs/v2/FRONTEND.md`, this plan.

---

## 7. Non-goals (this phase)

Backend changes of any kind (except genuine bug fixes); real-time WebSocket features; server-side
rendering of authenticated data; a mobile app; i18n (structure kept i18n-friendly, not wired).
