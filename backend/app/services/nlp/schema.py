# backend/app/services/nlp/schema.py
"""
The canonical ClauseObject (docs/v2/NLP.md) — scoped down for the CPU-only
Phase 2 slice: no bbox/page_ref (that needs the CV layout models we deferred)
and no embedding_ref/kg_node_id (Phase 3+ concerns). Everything here is
produced by rule-based/regex logic or an optional Gemini escalation, and each
field says which.
"""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class EntityMention(BaseModel):
    text: str
    type: str  # "money" | "jurisdiction"


class DeonticTag(BaseModel):
    modality: str  # "obligation" | "permission" | "prohibition" | "discretion"
    trigger_phrase: str
    actor: Optional[str] = None
    confidence: float = 1.0
    source: str = "rule"  # "rule" | "ai"


class CrossReference(BaseModel):
    text: str  # e.g. "Section 4.2"


class TemporalExpression(BaseModel):
    text: str
    normalized_date: Optional[str] = None  # ISO date, when resolvable


class AmbiguityFlag(BaseModel):
    term: str
    explanation: str


class ClauseObject(BaseModel):
    id: int
    text: str
    clause_type: str
    clause_type_source: str = "rule"  # "rule" | "ai"
    entities: List[EntityMention] = Field(default_factory=list)
    defined_terms_used: List[str] = Field(default_factory=list)
    cross_references: List[CrossReference] = Field(default_factory=list)
    deontic_tags: List[DeonticTag] = Field(default_factory=list)
    temporal_expressions: List[TemporalExpression] = Field(default_factory=list)
    ambiguity_flags: List[AmbiguityFlag] = Field(default_factory=list)
    # Heuristic only (not real coreference resolution — see coref.py docstring):
    # defined terms seen earlier in the document that a generic role word in
    # this clause ("the Company", "it") might refer to.
    pronoun_candidates: List[str] = Field(default_factory=list)
