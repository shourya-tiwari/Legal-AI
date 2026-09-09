# backend/app/models.py
from __future__ import annotations

from typing import List, Optional, Dict, Union
from pydantic import BaseModel, Field

from app.agents.state import AgentStep, KGConflictFinding, NegotiationSuggestion, RiskFinding
from app.services.consistency import ConsistencyFinding
from app.services.nlp.schema import ClauseObject
from app.services.simulation import DEFAULT_WARNING_WINDOW_DAYS, SimulatedEvent

# ----- Rewrite -----
class RewriteRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=20000)
    mode: str = Field("layman", pattern="^(layman)$")

class RewriteResponse(BaseModel):
    rewritten_text: str
    meta: dict | None = None

# ----- Upload -----
# POST /api/upload returns a hand-built dict (document_id + sensitivity +
# optional quality), not a Pydantic model -- see app/routes/upload.py and
# the frontend's hand-typed UploadResult. No response_model here on purpose.

# ----- Timeline (/api/map) -----
class DocumentSection(BaseModel):
    title: str
    content_summary: str
    # Use default_factory to avoid shared mutable defaults
    subsections: List["DocumentSection"] = Field(default_factory=list)

class TimelineEvent(BaseModel):
    date_description: str
    event: str

# Request model expected by the timeline route
class MapRequest(BaseModel):
    contract_text: str

class MapResponse(BaseModel):
    structure: List[DocumentSection]
    timeline: List[TimelineEvent]

# Resolve forward refs for recursive model (Pydantic v2)
DocumentSection.model_rebuild()

# ----- Chatbot (/api/ask) -----
class AskRequest(BaseModel):
    contract_text: str
    question: str

class AskResponse(BaseModel):
    answer: str
    # Additive (backward-compatible): the faithfulness check the agent
    # pipeline's Verifier has always had, now applied to the single
    # most-used feature in the product. Defaults are honest sentinels for
    # any hypothetical caller that constructs AskResponse without routing
    # through answer_question()'s check -- not a claim that a check ran.
    faithful: bool = Field(True, description="Whether the answer's claims are entailed by the contract text.")
    faithfulness_method: str = Field(
        "not_checked",
        description="'nli' (real entailment head) | 'lexical_fallback' (NLI head not installed) | 'not_checked'.",
    )
    unsupported_claims: List[str] = Field(
        default_factory=list,
        description="Answer sentences a source contradicted or failed to support (NLI method only).",
    )

# ----- Risk Radar (/api/risk/scan) -----
class RiskScanRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=20000)

class KeywordRiskFlag(BaseModel):
    term: str
    predefined_explanation: str

class ContextualRiskFlag(BaseModel):
    term: str
    explanation: str

class FlaggedClause(BaseModel):
    clause: str
    keyword_flags: List[KeywordRiskFlag] = Field(default_factory=list)
    contextual_flags: List[ContextualRiskFlag] = Field(default_factory=list)

class RiskScanResponse(BaseModel):
    flagged_clauses: List[FlaggedClause]
    risk_summary: str

class ClauseRiskFinding(BaseModel):
    clause_id: int
    category: str
    term: str
    explanation: str

class RiskDashboardResponse(BaseModel):
    categories: Dict[str, int] = Field(
        description="Every category name (app/services/risk_radar/rules.py::RISK_CATEGORY_NAMES) "
        "mapped to its keyword-flag count across the whole document -- always present, zero-filled "
        "if nothing was flagged, so a spider/radar chart's axes stay stable across documents.",
    )
    total_flags: int
    clause_findings: List[ClauseRiskFinding] = Field(
        default_factory=list, description="Per-clause detail for drill-down from a chart axis/category.",
    )

# ----- Structured Clause Analysis (/api/nlp/analyze) -----
class NlpAnalyzeRequest(BaseModel):
    contract_text: str = Field(..., min_length=1, max_length=50000)
    use_ai_escalation: bool = Field(
        False,
        description="If true, clauses the rule-based deontic tagger/classifier can't confidently handle "
        "are escalated to Gemini. Off by default for determinism/speed/cost.",
    )

class NlpAnalyzeResponse(BaseModel):
    clauses: List[ClauseObject]

# ----- Knowledge Graph (/api/kg) -----
class KGIngestRequest(BaseModel):
    document_id: int

class KGIngestResponse(BaseModel):
    document_id: int
    clauses: int
    defined_terms: int
    cross_references: int
    portfolio_links_created: int
    kg_available: bool = Field(
        description="False if Memgraph was unreachable -- the ingest call still succeeds (fail-soft), it just wrote nothing."
    )

class KGQueryRequest(BaseModel):
    term: str = Field(..., min_length=1, max_length=200)
    as_of: Optional[str] = Field(
        None, description="ISO date/datetime string. If set, returns clauses valid as of this point in time "
                           "instead of the current graph state (bitemporal versioning, LEARNING_LOG.md #50)."
    )

class KGQueryResponse(BaseModel):
    term: str
    as_of: Optional[str] = None
    clauses: List[dict] = Field(default_factory=list)

class KGConflictsResponse(BaseModel):
    term: str
    conflicts: List[dict] = Field(default_factory=list)

class KGSupersedeRequest(BaseModel):
    old_document_id: int
    new_document_id: int
    valid_from: Optional[str] = Field(
        None, description="ISO date/datetime the new version took effect. Defaults to now."
    )

class KGSupersedeResponse(BaseModel):
    old_document_id: int
    new_document_id: int
    valid_from: Optional[str] = None
    clauses_closed: int = 0
    kg_available: bool

class KGVersionHistoryResponse(BaseModel):
    document_id: int
    versions: List[dict] = Field(default_factory=list)

class KGGraphResponse(BaseModel):
    document_id: int
    nodes: List[dict] = Field(
        default_factory=list,
        description="{id, label, type} -- type is one of Document/Clause/DefinedTerm/CrossReferenceTarget.",
    )
    edges: List[dict] = Field(
        default_factory=list,
        description="{source, target, type} -- type is one of PART_OF/DEFINES/USES_TERM/REFERENCES/SAME_AS.",
    )
    kg_available: bool

# ----- Agentic Case Analysis (/api/agents/analyze) -----
_ANALYSIS_MODE_PATTERN = "^(full|quick|risk_only|extract_only)$"


class AgentAnalyzeRequest(BaseModel):
    document_id: int
    analysis_mode: str = Field(
        "full", pattern=_ANALYSIS_MODE_PATTERN,
        description="Planner preset: 'full' (all agents), 'quick' (skip RAG research), "
        "'risk_only' (flags only), 'extract_only' (clauses + the verifier gate only). "
        "The planner still prunes 'full' when a document has no risk/ambiguity signal.",
    )
    use_ai_planner: bool = Field(
        False,
        description="Let an LLM choose which agents run (falls back to the rule-based "
        "planner when no self-hosted model is served).",
    )

class AgentAnalyzeResponse(BaseModel):
    document_id: int
    clause_count: int
    sensitivity_tier: str = Field(
        "internal",
        description="The document's sensitivity tier. confidential/privileged documents are "
        "never routed to an external provider during this analysis.",
    )
    external_providers_permitted: bool = Field(
        True, description="False when the tier + settings forbid any Class C (external) routing."
    )
    plan: List[str] = Field(
        default_factory=list,
        description="The ordered agent node ids the planner ran (ends with 'verifier').",
    )
    plan_rationale: str = Field("", description="Why the planner chose that plan.")
    risk_findings: List[RiskFinding] = Field(default_factory=list)
    kg_conflicts: List[KGConflictFinding] = Field(default_factory=list)
    summary: str
    faithfulness_ok: bool = Field(
        description="Each summary claim is entailed by a retrieved source (NLI check). "
        "False means a claim was contradicted or left unsupported -- see unsupported_claims."
    )
    faithfulness_method: str = Field(
        "nli",
        description="'nli' = real entailment head (Class A DeBERTa/ModernBERT); "
        "'lexical_fallback' = the NLI head isn't installed, a weaker vocabulary-overlap check ran",
    )
    unsupported_claims: List[str] = Field(
        default_factory=list,
        description="Claim sentences a source contradicted or failed to support (NLI method only)",
    )
    invalid_citation_numbers: List[int] = Field(
        default_factory=list, description="Non-empty means the summary cited a source it was never given"
    )
    negotiation_suggestions: List[NegotiationSuggestion] = Field(
        default_factory=list,
        description="Clauses deviating from the org's configured preferred language (Organization."
        "negotiation_preferences). Always status='pending_review' -- never auto-applied.",
    )
    needs_human_review: bool
    trace: List[AgentStep] = Field(default_factory=list)

# ----- Model Router status (/api/models/status) -----
class ModelProviderStatus(BaseModel):
    name: str
    hosting_class: str = Field(description="A (deterministic/CPU), B (self-hosted neural), C (external API)")
    capabilities: List[str] = Field(default_factory=list)
    available: bool = Field(description="Provider's own is_available() -- config present, dependency importable")
    leaves_perimeter: bool = Field(description="True only for Class C providers that call a third-party API")
    models: List[str] = Field(default_factory=list)
    note: str = ""
    # Phase 7 "Model status panel: queue depth/latency" -- queue depth has no
    # meaning here (no job queue exists in this codebase), but latency is
    # real, already-collected data (model_calls.latency_ms) that was simply
    # never aggregated and surfaced before.
    recent_avg_latency_ms: Optional[float] = Field(
        None, description="Average latency_ms over this provider's most recent model_calls rows, if any."
    )
    recent_call_count: int = Field(0, description="How many recent model_calls rows the average above is based on.")

class ModelsStatusResponse(BaseModel):
    providers: List[ModelProviderStatus]
    policy_version: int
    external_providers_enabled: bool
    strict_local_only: bool


# ----- Class C policy overrides (LEARNING_LOG.md #42) -----
class ClassCOverrideItem(BaseModel):
    task: str
    class_c_disabled: bool
    reason: Optional[str] = None
    updated_at: Optional[str] = None


class ClassCOverridesResponse(BaseModel):
    overrides: List[ClassCOverrideItem] = Field(default_factory=list)


class SetClassCOverrideRequest(BaseModel):
    class_c_disabled: bool
    reason: Optional[str] = None


# ----- Self-hosted-vs-external delta report (LEARNING_LOG.md #42) -----
class DeltaReportRow(BaseModel):
    task: str
    local_ms: Optional[int] = None
    external_ms: Optional[int] = None
    local_len: int
    external_len: int
    agreement_f1: float
    local_error: Optional[str] = None
    external_error: Optional[str] = None


class DeltaReportResponse(BaseModel):
    rows: List[DeltaReportRow] = Field(default_factory=list)


# ----- Org settings: feature flags + webhook (LEARNING_LOG.md #42) -----
class OrgSettingsResponse(BaseModel):
    org_id: int
    feature_flags: dict = Field(default_factory=dict)
    webhook_url: Optional[str] = None
    negotiation_preferences: dict = Field(
        default_factory=dict,
        description="{clause_type: {preferred_language, rationale}} -- the Negotiation/Drafting "
        "agent's static-preferences input (docs/v2/ROADMAP.md Phase 8).",
    )


class UpdateOrgSettingsRequest(BaseModel):
    feature_flags: Optional[dict] = Field(None, description="Merged into the existing flags, not replaced wholesale.")
    webhook_url: Optional[str] = Field(None, description="Pass an empty string to clear it.")
    negotiation_preferences: Optional[dict] = Field(
        None, description="Merged into the existing preferences, keyed by clause_type, not replaced wholesale."
    )


# ----- Eval runs behind the routing policy (/api/models/eval-runs) -----
# Phase 7 "Provider & Model admin": the eval_runs table (app/eval/) already
# has this data -- the routing policy previously had no view showing it.
class EvalRunSummary(BaseModel):
    task: str
    provider: str
    model: str
    metric: str
    score: float
    n_examples: int
    baseline_score: Optional[float] = None
    passed: Optional[bool] = Field(
        None, description="For a cutover-gate row: candidate >= baseline * ratio. Null for a non-cutover eval run."
    )
    notes: Optional[str] = None
    created_at: Optional[str] = None


class EvalRunsResponse(BaseModel):
    runs: List[EvalRunSummary] = Field(
        default_factory=list,
        description="Most recent run per (task, provider) pair -- a snapshot, not the full history.",
    )


# ----- Contextualizer (/api/contextualize) -----
class ContextualizerRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000, description="Contract clause text to explain")
    context: dict = Field(..., description="User context including role, location, contract_type, interests, tone")

class ContextualizerResponse(BaseModel):
    clause: str
    context: dict
    explanation: str
    used_hints: List[str] = Field(default_factory=list, description="Contextual hints used in the explanation")
    citations: List[dict] = Field(
        default_factory=list,
        description="The retrieved knowledge-base entries backing used_hints, each with its source citation "
        "(or null if this is a general principle with no single controlling citation -- see "
        "services/rag/corpus.py). Additive field; used_hints is unchanged for backward compatibility.",
    )
    citation_warning: bool = Field(
        False, description="True if the model referenced a bracket citation number it wasn't actually given."
    )


# ----- /api/v2 -- document-first request bodies (the doc id is a path param) -----
# These reuse the V1 response models (RewriteResponse, MapResponse, AskResponse,
# RiskScanResponse, ContextualizerResponse, AgentAnalyzeResponse) unchanged.
class V2AnalyzeRequest(BaseModel):
    analysis_mode: str = Field("full", pattern=_ANALYSIS_MODE_PATTERN)
    use_ai_planner: bool = False

class V2RewriteRequest(BaseModel):
    block_id: Optional[Union[int, str]] = Field(None, description="A block id from the upload response; omit to rewrite the whole document.")
    mode: str = Field("layman", pattern="^(layman)$")

class V2AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)

class V2RiskScanRequest(BaseModel):
    block_id: Optional[Union[int, str]] = Field(None, description="A block id; omit to scan the whole document.")

class V2ContextualizeRequest(BaseModel):
    block_id: Union[int, str] = Field(..., description="The block id whose clause to explain.")
    context: dict = Field(..., description="User context: role, location, contract_type, interests, tone.")

class V2DocumentResponse(BaseModel):
    document_id: int
    filename: str
    content_type: Optional[str] = None
    full_text: str
    blocks: List[dict] = Field(default_factory=list)
    created_at: Optional[str] = None
    sensitivity_tier: str = "internal"
    sensitivity_source: str = "auto"
    quality: Optional[dict] = Field(
        None, description="CV quality triage (blur/skew) -- only set for PDFs with scanned pages."
    )
    original_available: bool = Field(
        False,
        description="True when the original uploaded file bytes were stored and can be "
        "fetched from GET /api/v2/documents/{id}/original.",
    )
    original_size: Optional[int] = Field(
        None, description="Byte count of the stored original file, when available."
    )


# ----- Document sensitivity (/api/v2/documents/{id}/sensitivity) -----
_SENSITIVITY_TIER_PATTERN = "^(public|internal|confidential|privileged)$"


class SensitivityResponse(BaseModel):
    document_id: int
    tier: str
    source: str = Field(description="'auto' (rule classifier) or 'override' (org-admin set it)")
    signals: List[dict] = Field(default_factory=list, description="The phrases that drove the tier.")
    rationale: str = ""
    external_providers_permitted: bool = Field(
        description="False => every model call for this document stays on self-hosted providers."
    )

class SensitivityOverrideRequest(BaseModel):
    tier: str = Field(..., pattern=_SENSITIVITY_TIER_PATTERN)
    reason: str = Field(..., min_length=1, max_length=500, description="Recorded in the audit log.")


# ----- Cross-Document Consistency (/api/v2/documents/{id}/consistency) -----
# Phase 8 embedding-similarity baseline -- ConsistencyFinding is defined once
# in app/services/consistency.py and reused here (same pattern as AgentStep/
# RiskFinding/KGConflictFinding, defined in app/agents/state.py above).
class ConsistencyResponse(BaseModel):
    document_id: int
    other_documents_checked: int
    findings: List[ConsistencyFinding] = Field(default_factory=list)


# ----- Simulation (/api/v2/documents/{id}/simulate) -----
# Phase 8 deterministic discrete-event baseline -- see app/services/simulation.py.
class SimulationRequest(BaseModel):
    reference_date: Optional[str] = Field(
        None, description="ISO date to simulate from; defaults to today. Mainly for testing/demo."
    )
    warning_window_days: int = Field(DEFAULT_WARNING_WINDOW_DAYS, ge=1, le=365)


class SimulationResponse(BaseModel):
    document_id: int
    reference_date: str
    warning_window_days: int
    events: List[SimulatedEvent] = Field(default_factory=list)


# ----- Human-in-the-loop review queue (/api/review-queue) -----
# Phase 7 -- CaseAnalysis persists the run-level outcome of an agent
# analysis (app/routes/agents.py) so "needs_human_review" runs can actually
# be listed and resolved, instead of only appearing in the one HTTP
# response at analysis time.
class ReviewQueueItem(BaseModel):
    id: int
    document_id: int
    document_filename: str
    analysis_mode: str
    plan: List[str] = Field(default_factory=list)
    summary: str
    faithfulness_ok: bool
    faithfulness_method: str
    unsupported_claims: List[str] = Field(default_factory=list)
    invalid_citation_numbers: List[int] = Field(default_factory=list)
    needs_human_review: bool
    reviewed: bool
    reviewed_at: Optional[str] = None
    reviewer_note: Optional[str] = None
    created_at: Optional[str] = None


class ReviewQueueResponse(BaseModel):
    items: List[ReviewQueueItem] = Field(default_factory=list)


# ----- Egress audit log (GET /api/audit/egress) -----
class EgressLogEntry(BaseModel):
    id: int
    task: str = Field(..., description="The Model Router task, e.g. 'qa', 'clause_rewrite'.")
    provider: str = Field(..., description="The Class C provider this request was dispatched to.")
    model: Optional[str] = None
    sensitivity: Optional[str] = None
    policy_version: Optional[int] = None
    payload_sha256: Optional[str] = Field(
        None, description="SHA-256 of the exact text sent -- proves what left without storing it."
    )
    redacted_categories: dict = Field(
        default_factory=dict,
        description="PII categories the redaction gate masked before this call, with counts.",
    )
    created_at: Optional[str] = None


class EgressLogResponse(BaseModel):
    entries: List[EgressLogEntry] = Field(default_factory=list)


# ----- Per-user identity (app/routes/auth.py, LEARNING_LOG.md #37) -----
class LoginRequest(BaseModel):
    email: str
    password: str = Field(..., min_length=1)


class LoginResponse(BaseModel):
    token: str = Field(..., description="Bearer session token -- shown once, never recoverable again.")
    org_id: int
    org_name: str
    role: str
    expires_at: str


class CreateUserRequest(BaseModel):
    email: str
    password: str = Field(..., min_length=8, description="At least 8 characters -- no other complexity rule enforced yet.")
    role: str = Field("admin", description="One of 'admin' | 'editor' | 'viewer'.")


class UserSummary(BaseModel):
    id: int
    email: str
    role: str
    created_at: Optional[str] = None
    revoked_at: Optional[str] = None


class UsersListResponse(BaseModel):
    users: List[UserSummary] = Field(default_factory=list)


class ReviewResolveRequest(BaseModel):
    note: Optional[str] = Field(None, max_length=1000)
