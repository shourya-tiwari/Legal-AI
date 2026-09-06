# backend/app/models.py
from __future__ import annotations

from typing import List, Optional, Dict, Union
from pydantic import BaseModel, Field

from app.agents.state import AgentStep, KGConflictFinding, RiskFinding
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
class UploadResponse(BaseModel):
    session_id: str = Field(..., description="Unique ID for this document session.")
    filename: str
    message: str = "File uploaded and text extracted successfully."

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

class KGQueryResponse(BaseModel):
    term: str
    clauses: List[dict] = Field(default_factory=list)

class KGConflictsResponse(BaseModel):
    term: str
    conflicts: List[dict] = Field(default_factory=list)

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

class ModelsStatusResponse(BaseModel):
    providers: List[ModelProviderStatus]
    policy_version: int
    external_providers_enabled: bool
    strict_local_only: bool


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
