// Typed fetch client for the LegalAI backend.
//
// Everything except /upload is typed from the backend's live OpenAPI schema
// (src/lib/api-types.ts, regenerated via `npm run codegen`). /upload has no
// response_model on the FastAPI side so its shape is hand-typed here.
//
// The backend is a separate origin (NEXT_PUBLIC_API_BASE_URL). Auth is
// optional: when the backend runs with AUTH_REQUIRED=true, a bearer token
// obtained from POST /api/auth/login is stored in localStorage and attached
// to every request. When auth is off, requests work with no token.
import type { components } from "./api-types";

export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000/api";

const TOKEN_KEY = "legalai.auth.token";

export function getAuthToken(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setAuthToken(token: string | null) {
  if (typeof window === "undefined") return;
  try {
    if (token) window.localStorage.setItem(TOKEN_KEY, token);
    else window.localStorage.removeItem(TOKEN_KEY);
    window.dispatchEvent(new Event("legalai:auth"));
  } catch {
    /* storage unavailable — auth simply stays off */
  }
}

export class ApiError extends Error {
  status: number;
  body: string;
  constructor(message: string, status: number, body = "") {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const isForm = init?.body instanceof FormData;
  const token = getAuthToken();
  const headers: Record<string, string> = {
    ...(isForm ? {} : { "Content-Type": "application/json" }),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...((init?.headers as Record<string, string>) ?? {}),
  };

  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, { ...init, headers });
  } catch {
    throw new ApiError(
      "Could not reach the backend. Is it running?",
      0,
    );
  }

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    let message = res.statusText;
    try {
      const json = JSON.parse(text);
      message = json.detail || json.error || json.message || message;
    } catch {
      if (text) message = text.slice(0, 300);
    }
    throw new ApiError(message, res.status, text);
  }

  if (res.status === 204) return undefined as T;
  const ct = res.headers.get("content-type") ?? "";
  if (!ct.includes("application/json")) return (await res.text()) as unknown as T;
  return res.json() as Promise<T>;
}

type S = components["schemas"];

/* ------------------------------------------------------------------ *
 * Health
 * ------------------------------------------------------------------ */
export async function getHealth(): Promise<{ message: string }> {
  // GET / lives at the API root, one level above /api
  const base = API_BASE.replace(/\/api\/?$/, "");
  const res = await fetch(`${base}/`);
  if (!res.ok) throw new ApiError("backend unreachable", res.status);
  return res.json();
}

/* ------------------------------------------------------------------ *
 * Upload (no response_model — hand-typed)
 * ------------------------------------------------------------------ */
export interface UploadBlock {
  id: string | number;
  text: string;
  rewritten: string | null;
}
export interface UploadSensitivity {
  tier: string;
  source: string;
  rationale: string;
  external_providers_permitted: boolean;
}
export interface DocumentQuality {
  pages_assessed: number;
  low_quality_pages: number[];
  pages_with_redactions?: number[];
  pages: {
    page: number;
    blur_score: number;
    skew_angle_degrees: number;
    is_low_quality: boolean;
    redacted_regions?: { x: number; y: number; width: number; height: number }[];
  }[];
}
export interface UploadResult {
  document_id: number;
  filename: string;
  content_type: string | null;
  full_text: string;
  clauses: UploadBlock[];
  count: number;
  sensitivity: UploadSensitivity;
  quality?: DocumentQuality;
}

export async function uploadDocument(
  file: File,
  onProgress?: (pct: number) => void,
): Promise<UploadResult> {
  // XHR so we can report upload progress; falls back to fetch semantics.
  return new Promise<UploadResult>((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${API_BASE}/upload`);
    const token = getAuthToken();
    if (token) xhr.setRequestHeader("Authorization", `Bearer ${token}`);
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable && onProgress)
        onProgress(Math.round((e.loaded / e.total) * 100));
    };
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          resolve(JSON.parse(xhr.responseText));
        } catch {
          reject(new ApiError("Malformed upload response", xhr.status));
        }
      } else {
        let msg = xhr.statusText;
        try {
          msg = JSON.parse(xhr.responseText).detail ?? msg;
        } catch {
          /* keep statusText */
        }
        reject(new ApiError(msg, xhr.status, xhr.responseText));
      }
    };
    xhr.onerror = () =>
      reject(new ApiError("Could not reach the backend.", 0));
    const form = new FormData();
    form.append("file", file);
    xhr.send(form);
  });
}

/* ------------------------------------------------------------------ *
 * Documents (/api/v2)
 * ------------------------------------------------------------------ */
export type DocumentResponse = S["V2DocumentResponse"];
export type SensitivityResponse = S["SensitivityResponse"];

export const getDocument = (id: number) =>
  request<DocumentResponse>(`/v2/documents/${id}`);

export const getSensitivity = (id: number) =>
  request<SensitivityResponse>(`/v2/documents/${id}/sensitivity`);

export const overrideSensitivity = (
  id: number,
  tier: string,
  reason: string,
) =>
  request<SensitivityResponse>(`/v2/documents/${id}/sensitivity`, {
    method: "PUT",
    body: JSON.stringify({ tier, reason }),
  });

export function originalFileUrl(id: number): string {
  return `${API_BASE}/v2/documents/${id}/original`;
}

/* ------------------------------------------------------------------ *
 * Analysis
 * ------------------------------------------------------------------ */
export type RewriteResponse = S["RewriteResponse"];
export type MapResponse = S["MapResponse"];
export type AskResponse = S["AskResponse"];
export type RiskScanResponse = S["RiskScanResponse"];
export type RiskDashboardResponse = S["RiskDashboardResponse"];
export type ContextualizerResponse = S["ContextualizerResponse"];
export type AgentAnalyzeResponse = S["AgentAnalyzeResponse"];
export type ConsistencyResponse = S["ConsistencyResponse"];
export type SimulationResponse = S["SimulationResponse"];
export type NlpAnalyzeResponse = S["NlpAnalyzeResponse"];
export type ClauseObject = S["ClauseObject"];

export const rewriteDocument = (
  id: number,
  blockId?: string | number | null,
) =>
  request<RewriteResponse>(`/v2/documents/${id}/rewrite`, {
    method: "POST",
    body: JSON.stringify({ block_id: blockId ?? null, mode: "layman" }),
  });

export const mapDocument = (id: number) =>
  request<MapResponse>(`/v2/documents/${id}/map`, { method: "POST" });

export const riskScanDocument = (
  id: number,
  blockId?: string | number | null,
) =>
  request<RiskScanResponse>(`/v2/documents/${id}/risk-scan`, {
    method: "POST",
    body: JSON.stringify({ block_id: blockId ?? null }),
  });

export const getRiskDashboard = (id: number) =>
  request<RiskDashboardResponse>(`/v2/documents/${id}/risk-dashboard`, {
    method: "POST",
  });

export const askDocument = (id: number, question: string) =>
  request<AskResponse>(`/v2/documents/${id}/ask`, {
    method: "POST",
    body: JSON.stringify({ question }),
  });

export interface ContextualizeContext {
  role: string;
  location?: string | null;
  contract_type?: string | null;
  interests?: string | null;
  tone: string;
}

export const contextualizeDocument = (
  id: number,
  blockId: string | number,
  context: ContextualizeContext,
) =>
  request<ContextualizerResponse>(`/v2/documents/${id}/contextualize`, {
    method: "POST",
    body: JSON.stringify({ block_id: blockId, context }),
  });

export type AnalysisMode = "full" | "quick" | "risk_only" | "extract_only";

export const analyzeDocument = (
  id: number,
  opts?: { analysis_mode?: AnalysisMode; use_ai_planner?: boolean },
) =>
  request<AgentAnalyzeResponse>(`/v2/documents/${id}/analyze`, {
    method: "POST",
    body: JSON.stringify(opts ?? {}),
  });

export const checkConsistency = (id: number) =>
  request<ConsistencyResponse>(`/v2/documents/${id}/consistency`, {
    method: "POST",
  });

export const simulateTimeline = (
  id: number,
  opts?: { reference_date?: string; warning_window_days?: number },
) =>
  request<SimulationResponse>(`/v2/documents/${id}/simulate`, {
    method: "POST",
    body: JSON.stringify(opts ?? {}),
  });

export const analyzeNlp = (contractText: string, useAiEscalation = false) =>
  request<NlpAnalyzeResponse>("/nlp/analyze", {
    method: "POST",
    body: JSON.stringify({
      contract_text: contractText,
      use_ai_escalation: useAiEscalation,
    }),
  });

/* ------------------------------------------------------------------ *
 * Knowledge Graph
 * ------------------------------------------------------------------ */
export type KGIngestResponse = S["KGIngestResponse"];
export type KGQueryResponse = S["KGQueryResponse"];
export type KGConflictsResponse = S["KGConflictsResponse"];
export type KGGraphResponse = S["KGGraphResponse"];
export type KGVersionHistoryResponse = S["KGVersionHistoryResponse"];
export type KGSupersedeResponse = S["KGSupersedeResponse"];

export const ingestKg = (documentId: number) =>
  request<KGIngestResponse>("/kg/ingest", {
    method: "POST",
    body: JSON.stringify({ document_id: documentId }),
  });

export const queryKgTerm = (term: string, asOf?: string) =>
  request<KGQueryResponse>("/kg/query", {
    method: "POST",
    body: JSON.stringify({ term, as_of: asOf ?? null }),
  });

export const queryKgConflicts = (term: string) =>
  request<KGConflictsResponse>("/kg/conflicts", {
    method: "POST",
    body: JSON.stringify({ term }),
  });

export const getKgGraph = (documentId: number) =>
  request<KGGraphResponse>(`/kg/documents/${documentId}/graph`);

export const getKgVersions = (documentId: number) =>
  request<KGVersionHistoryResponse>(`/kg/documents/${documentId}/versions`);

export const supersedeDocument = (
  oldId: number,
  newId: number,
  validFrom?: string,
) =>
  request<KGSupersedeResponse>("/kg/supersede", {
    method: "POST",
    body: JSON.stringify({
      old_document_id: oldId,
      new_document_id: newId,
      valid_from: validFrom ?? null,
    }),
  });

/* ------------------------------------------------------------------ *
 * Review queue
 * ------------------------------------------------------------------ */
export type ReviewQueueResponse = S["ReviewQueueResponse"];
export type ReviewQueueItem = S["ReviewQueueItem"];

export const getReviewQueue = (includeResolved = false) =>
  request<ReviewQueueResponse>(
    `/review-queue${includeResolved ? "?include_resolved=true" : ""}`,
  );

export const resolveReviewItem = (id: number, note?: string) =>
  request<ReviewQueueItem>(`/review-queue/${id}/resolve`, {
    method: "POST",
    body: JSON.stringify({ note: note ?? null }),
  });

/* ------------------------------------------------------------------ *
 * Model Router / Evaluation
 * ------------------------------------------------------------------ */
export type ModelsStatusResponse = S["ModelsStatusResponse"];
export type EvalRunsResponse = S["EvalRunsResponse"];
export type ClassCOverridesResponse = S["ClassCOverridesResponse"];
export type ClassCOverrideItem = S["ClassCOverrideItem"];
export type DeltaReportResponse = S["DeltaReportResponse"];

export const getModelsStatus = () =>
  request<ModelsStatusResponse>("/models/status");

export const getEvalRuns = () => request<EvalRunsResponse>("/models/eval-runs");

export const getClassCOverrides = () =>
  request<ClassCOverridesResponse>("/models/class-c-overrides");

export const setClassCOverride = (
  task: string,
  classCDisabled: boolean,
  reason?: string,
) =>
  request<ClassCOverrideItem>(`/models/class-c-overrides/${task}`, {
    method: "PUT",
    body: JSON.stringify({ class_c_disabled: classCDisabled, reason: reason ?? null }),
  });

export const clearClassCOverride = (task: string) =>
  request<{ cleared: boolean; task: string }>(
    `/models/class-c-overrides/${task}`,
    { method: "DELETE" },
  );

export const runDeltaReport = () =>
  request<DeltaReportResponse>("/models/delta-report", { method: "POST" });

/* ------------------------------------------------------------------ *
 * Audit / egress
 * ------------------------------------------------------------------ */
export type EgressLogResponse = S["EgressLogResponse"];

export const getEgressLog = (limit = 100) =>
  request<EgressLogResponse>(`/audit/egress?limit=${limit}`);

/* ------------------------------------------------------------------ *
 * Org settings
 * ------------------------------------------------------------------ */
export type OrgSettingsResponse = S["OrgSettingsResponse"];

export const getOrgSettings = () =>
  request<OrgSettingsResponse>("/org/settings");

export const updateOrgSettings = (body: {
  feature_flags?: Record<string, boolean>;
  webhook_url?: string | null;
  negotiation_preferences?: Record<
    string,
    { preferred_language: string; rationale?: string }
  >;
}) =>
  request<OrgSettingsResponse>("/org/settings", {
    method: "PUT",
    body: JSON.stringify(body),
  });

/* ------------------------------------------------------------------ *
 * Auth
 * ------------------------------------------------------------------ */
export type LoginResponse = S["LoginResponse"];
export type UsersListResponse = S["UsersListResponse"];
export type UserSummary = S["UserSummary"];

export async function login(email: string, password: string) {
  const res = await request<LoginResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  setAuthToken(res.token);
  return res;
}

export async function logout() {
  try {
    await request("/auth/logout", { method: "POST" });
  } finally {
    setAuthToken(null);
  }
}

export const listUsers = () => request<UsersListResponse>("/auth/users");

export const createUser = (email: string, password: string, role: string) =>
  request<UserSummary>("/auth/users", {
    method: "POST",
    body: JSON.stringify({ email, password, role }),
  });

export const revokeUser = (id: number) =>
  request<UserSummary>(`/auth/users/${id}/revoke`, { method: "POST" });
