# LegalAI — v2 frontend

Next.js (App Router) + TypeScript + Tailwind + TanStack Query SPA for the
LegalAI backend. Dark theme, no third-party font/asset origins.

## Develop

```bash
npm install
npm run dev            # http://localhost:3000
```

Point the SPA at a backend with `NEXT_PUBLIC_API_BASE_URL` (see
`.env.local.example`). Defaults to `http://127.0.0.1:8000/api`.

## API types

`src/lib/api-types.ts` is generated from the backend's live OpenAPI schema and
committed. Regenerate after a backend schema change:

```bash
npm run codegen       # shells out to ../backend's venv; no running server needed
```

## Checks

```bash
npm run lint
npm run build
```

## Layout

- `src/app/` — routes: `/` (marketing), `/upload`, `/documents/[id]` (workspace),
  `/models`, `/review`, `/about`
- `src/components/` — panels (Analysis, StructuredAnalysis, KnowledgeGraph,
  Consistency, Simulation, RiskDashboard, …)
- `src/lib/` — `api.ts` (typed fetch wrapper), `api-types.ts` (generated),
  `query-client.tsx`
