# backend/app/models.py
from __future__ import annotations

from typing import List, Optional, Dict
from pydantic import BaseModel, Field

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

# ----- Contextualizer (/api/contextualize) -----
class ContextualizerRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000, description="Contract clause text to explain")
    context: dict = Field(..., description="User context including role, location, contract_type, interests, tone")

class ContextualizerResponse(BaseModel):
    clause: str
    context: dict
    explanation: str
    used_hints: List[str] = Field(default_factory=list, description="Contextual hints used in the explanation")
