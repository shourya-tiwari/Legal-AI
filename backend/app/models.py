# backend/app/models.py
from __future__ import annotations

from typing import List, Optional, Dict
from pydantic import BaseModel, Field

from app.agents.state import AgentStep, KGConflictFinding, RiskFinding
from app.services.nlp.schema import ClauseObject

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
class AgentAnalyzeRequest(BaseModel):
    document_id: int

class AgentAnalyzeResponse(BaseModel):
    document_id: int
    clause_count: int
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
