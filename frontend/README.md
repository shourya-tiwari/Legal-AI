# LegalAI — frontend

Production-grade SaaS UI for the LegalAI backend. Next.js 16 (App Router,
Turbopack) · React 19 · TypeScript · Tailwind v4 · TanStack Query · Radix
primitives · Framer Motion · React Flow · Recharts · Zustand.

The backend is a **separate, frozen** FastAPI origin (`docs/v2/ROADMAP.md`).
This app makes no API or architecture changes to it — see
`docs/v2/FRONTEND_PLAN.md` for the backend→frontend capability map and the
honest handling of the five things the backend can't do (no document-list,
streaming, conversation-history, trace-history, or usage-metrics endpoints).

## Develop

```bash
npm install
npm run dev            # http://localhost:3000
```

Point the SPA at a backend with `NEXT_PUBLIC_API_BASE_URL` (see
`.env.local.example`). Defaults to `http://127.0.0.1:8000/api`. Auth is
optional — the app works token-less when the backend runs
`AUTH_REQUIRED=false`.

## API types

`src/lib/api-types.ts` is generated from the backend's live OpenAPI schema and
committed. The backend schema is stable, so regeneration is rarely needed:

```bash
npm run codegen       # shells out to ../backend's venv; no running server needed
```

## Checks

```bash
npm run lint
npm run build
```

## Layout

```
src/app/
  (marketing)/    – public site: /, /features, /architecture, /research,
                    /docs, /about, /about/developer, /contact
  (app)/          – the application shell (sidebar + topbar + ⌘K palette)
    welcome/             – guided onboarding (Get started lands here)
    dashboard/           documents/          documents/upload/
    documents/[id]/      – tabbed workspace: overview · clauses · risk ·
                           timeline · negotiation · graph · agents · ask
    assistant/           knowledge-graph/    review/
    evaluation/          models/             analytics/
    admin/               – overview · users · models · egress · flags
    settings/            profile/
  login/          – session auth (outside both shells)
```

The marketing site and the app are **one product**: the sidebar's Resources
group and the topbar dropdown link into `(marketing)`, and the public header
always offers a route back to the dashboard. `layout/nav-config.tsx` is the
single source of nav truth; `layout/route-tabs.tsx` is the shared underline tab
bar (workspace + admin).

```
src/components/
  ui/             – ~32 Radix-backed primitives (shadcn-style API)
  layout/         – AppShell, SidebarNav, Topbar, CommandPalette, headers
  shared/         – badges, dropzone, markdown, loaders, code block
  workspace/      – WorkspaceProvider + the per-tab components
  marketing/      – hero/section helpers, home sections

src/lib/
  api.ts          – one typed client for every endpoint
  api-types.ts    – generated
  stores/         – Zustand: documents, chat, ui, auth (localStorage-backed)
  format.ts       – formatters + metadata lookups
  query-keys.ts   – centralised TanStack Query keys
```
