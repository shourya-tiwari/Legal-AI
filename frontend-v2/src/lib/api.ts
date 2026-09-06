// Thin typed fetch wrapper around the LegalAI backend.
//
// Everything except /upload is typed from the backend's live OpenAPI schema
// (src/lib/api-types.ts, generated via `npm run codegen` -- see package.json).
// /upload has no response_model on the FastAPI side (app/routes/upload.py
// returns a hand-built dict), so its shape is hand-typed here instead.
import type { components } from "./api-types";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000/api";

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const isForm = init?.body instanceof FormData;
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: isForm
      ? init?.headers
      : { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new ApiError(text || res.statusText, res.status);
  }
  return res.json() as Promise<T>;
}

// ----- /api/upload (no response_model backend-side -- hand-typed) -----
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

export interface UploadResult {
  document_id: number;
  filename: string;
  content_type: string | null;
  full_text: string;
  clauses: UploadBlock[];
  count: number;
  sensitivity: UploadSensitivity;
}

export async function uploadDocument(file: File): Promise<UploadResult> {
  const form = new FormData();
  form.append("file", file);
  return request<UploadResult>("/upload", { method: "POST", body: form });
}

// ----- /api/v2/documents/{id}/* (typed from the generated OpenAPI schema) -----
export type DocumentResponse = components["schemas"]["V2DocumentResponse"];
export type RewriteResponse = components["schemas"]["RewriteResponse"];
export type MapResponse = components["schemas"]["MapResponse"];
export type AskResponse = components["schemas"]["AskResponse"];
export type RiskScanResponse = components["schemas"]["RiskScanResponse"];
export type ContextualizerResponse =
  components["schemas"]["ContextualizerResponse"];
export type AgentAnalyzeResponse =
  components["schemas"]["AgentAnalyzeResponse"];
export type SensitivityResponse = components["schemas"]["SensitivityResponse"];

export async function getDocument(id: number): Promise<DocumentResponse> {
  return request<DocumentResponse>(`/v2/documents/${id}`);
}

export async function getSensitivity(id: number): Promise<SensitivityResponse> {
  return request<SensitivityResponse>(`/v2/documents/${id}/sensitivity`);
}

export async function rewriteDocument(
  id: number,
  blockId?: string | number | null,
): Promise<RewriteResponse> {
  return request<RewriteResponse>(`/v2/documents/${id}/rewrite`, {
    method: "POST",
    body: JSON.stringify({ block_id: blockId ?? null, mode: "layman" }),
  });
}

export async function mapDocument(id: number): Promise<MapResponse> {
  return request<MapResponse>(`/v2/documents/${id}/map`, { method: "POST" });
}

export async function riskScanDocument(
  id: number,
  blockId?: string | number | null,
): Promise<RiskScanResponse> {
  return request<RiskScanResponse>(`/v2/documents/${id}/risk-scan`, {
    method: "POST",
    body: JSON.stringify({ block_id: blockId ?? null }),
  });
}

export async function askDocument(
  id: number,
  question: string,
): Promise<AskResponse> {
  return request<AskResponse>(`/v2/documents/${id}/ask`, {
    method: "POST",
    body: JSON.stringify({ question }),
  });
}

export interface ContextualizeContext {
  role: string;
  location: string | null;
  contract_type: string | null;
  interests: string | null;
  tone: string;
}

export async function contextualizeDocument(
  id: number,
  blockId: string | number,
  context: ContextualizeContext,
): Promise<ContextualizerResponse> {
  return request<ContextualizerResponse>(
    `/v2/documents/${id}/contextualize`,
    {
      method: "POST",
      body: JSON.stringify({ block_id: blockId, context }),
    },
  );
}

export async function analyzeDocument(
  id: number,
  opts?: { analysis_mode?: string; use_ai_planner?: boolean },
): Promise<AgentAnalyzeResponse> {
  return request<AgentAnalyzeResponse>(`/v2/documents/${id}/analyze`, {
    method: "POST",
    body: JSON.stringify(opts ?? {}),
  });
}

// ----- /api/nlp/analyze (V1 route -- takes raw text, not a document_id) -----
export type ClauseObject = components["schemas"]["ClauseObject"];
export type NlpAnalyzeResponse = components["schemas"]["NlpAnalyzeResponse"];

export async function analyzeNlp(contractText: string): Promise<NlpAnalyzeResponse> {
  return request<NlpAnalyzeResponse>("/nlp/analyze", {
    method: "POST",
    body: JSON.stringify({ contract_text: contractText, use_ai_escalation: false }),
  });
}

// ----- /api/models/status -----
export type ModelsStatusResponse = components["schemas"]["ModelsStatusResponse"];

export async function getModelsStatus(): Promise<ModelsStatusResponse> {
  return request<ModelsStatusResponse>("/models/status");
}

// ----- /api/kg/* (org-wide, term-based -- not document-scoped) -----
export type KGIngestResponse = components["schemas"]["KGIngestResponse"];
export type KGQueryResponse = components["schemas"]["KGQueryResponse"];
export type KGConflictsResponse = components["schemas"]["KGConflictsResponse"];

export async function ingestKg(documentId: number): Promise<KGIngestResponse> {
  return request<KGIngestResponse>("/kg/ingest", {
    method: "POST",
    body: JSON.stringify({ document_id: documentId }),
  });
}

export async function queryKgTerm(term: string): Promise<KGQueryResponse> {
  return request<KGQueryResponse>("/kg/query", {
    method: "POST",
    body: JSON.stringify({ term }),
  });
}

export async function queryKgConflicts(term: string): Promise<KGConflictsResponse> {
  return request<KGConflictsResponse>("/kg/conflicts", {
    method: "POST",
    body: JSON.stringify({ term }),
  });
}

// ----- /api/v2/documents/{id}/consistency (Phase 8 embedding-similarity baseline) -----
export type ConsistencyResponse = components["schemas"]["ConsistencyResponse"];

export async function checkConsistency(id: number): Promise<ConsistencyResponse> {
  return request<ConsistencyResponse>(`/v2/documents/${id}/consistency`, {
    method: "POST",
  });
}
