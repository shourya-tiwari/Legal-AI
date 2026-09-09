/** Centralised TanStack Query keys so invalidation stays consistent. */
export const qk = {
  health: ["health"] as const,

  document: (id: number) => ["document", id] as const,
  sensitivity: (id: number) => ["sensitivity", id] as const,
  nlp: (id: number, ai: boolean) => ["nlp", id, ai] as const,
  analyze: (id: number, mode: string, aiPlanner: boolean) =>
    ["analyze", id, mode, aiPlanner] as const,
  map: (id: number) => ["map", id] as const,
  riskDashboard: (id: number) => ["risk-dashboard", id] as const,
  consistency: (id: number) => ["consistency", id] as const,
  simulate: (id: number, ref: string, window: number) =>
    ["simulate", id, ref, window] as const,
  kgGraph: (id: number) => ["kg-graph", id] as const,
  kgVersions: (id: number) => ["kg-versions", id] as const,

  kgQuery: (term: string, asOf?: string) =>
    ["kg-query", term, asOf ?? null] as const,
  kgConflicts: (term: string) => ["kg-conflicts", term] as const,

  reviewQueue: (includeResolved: boolean) =>
    ["review-queue", includeResolved] as const,
  modelsStatus: ["models-status"] as const,
  evalRuns: ["eval-runs"] as const,
  classCOverrides: ["class-c-overrides"] as const,
  egress: (limit: number) => ["egress", limit] as const,
  orgSettings: ["org-settings"] as const,
  users: ["users"] as const,
};
