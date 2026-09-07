# backend/app/agents/tools.py
"""
Typed tool interfaces (docs/v2/AGENTS.md "Tool interface", Phase 7): "Every
tool is a typed, JSON-schema-validated function — agents cannot execute
arbitrary code or make unbounded network calls." Grammar-constrained
decoding at the LLM layer (the other half of that sentence) needs a served
self-hosted model this environment doesn't have running; this module is the
mechanical enforcement layer that sits *behind* whichever calling
convention eventually drives it (a rule-based planner today, a real
tool-calling LLM once one is served) -- every input is Pydantic-validated
before the wrapped service runs, and every output is validated before it's
handed back, so a malformed call fails loudly and structurally instead of
propagating a bad value.

Every tool here wraps an already-shipped service function -- this is a
*formalization* pass, not new capability: `kg_query`/`kg_conflicts` wrap
`services/kg/queries.py`, `vector_search` wraps `services/rag/hybrid.py`,
`statute_lookup` filters `services/rag/corpus.py`, `date_math` and
`clause_diff` are genuinely new (deterministic, stdlib-only, no service
existed to wrap), and `request_human_approval` is honestly scoped: this
codebase has no synchronous blocking-for-a-human mechanism (`AGENTS.md`'s
"blocks the workflow pending human sign-off" is aspirational for that part)
-- what exists is the async review queue (`CaseAnalysis.needs_human_review`,
`routes/review.py`), so this tool creates a request in that same shape
rather than pretending to block.

Same registry pattern as `app/agents/registry.py`: adding a tool is one
`ToolSpec` entry, no wiring change to `call_tool`.
"""
from __future__ import annotations

import difflib
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Callable, Dict, List, Optional, Type

from dateutil.relativedelta import relativedelta
from pydantic import BaseModel, Field

logger_name = "legalai.agents.tools"


class ToolError(Exception):
    """Raised on invalid input/output for a tool call -- the mechanical
    "structured tool calls are enforced" guarantee AGENTS.md names."""


# --------------------------------------------------------------------------
# kg_query / kg_conflicts
# --------------------------------------------------------------------------

class KGQueryInput(BaseModel):
    org_id: int
    term: str = Field(..., min_length=1)


class KGClauseMatch(BaseModel):
    clause_id: str
    text: str
    clause_type: Optional[str] = None
    document_id: int


class KGQueryOutput(BaseModel):
    matches: List[KGClauseMatch] = Field(default_factory=list)


def _kg_query(input: KGQueryInput) -> KGQueryOutput:
    from app.services.kg.client import get_kg_client
    from app.services.kg.queries import find_clauses_using_term

    client = get_kg_client()
    rows = find_clauses_using_term(client, input.org_id, input.term)
    return KGQueryOutput(matches=[
        KGClauseMatch(clause_id=r["clause_id"], text=r["text"],
                      clause_type=r.get("clause_type"), document_id=r["document_id"])
        for r in rows
    ])


class KGConflictOutput(BaseModel):
    conflicts: List[Dict[str, Any]] = Field(default_factory=list)


def _kg_conflicts(input: KGQueryInput) -> KGConflictOutput:
    from app.services.kg.client import get_kg_client
    from app.services.kg.queries import find_potential_conflicts

    client = get_kg_client()
    return KGConflictOutput(conflicts=find_potential_conflicts(client, input.org_id, input.term))


# --------------------------------------------------------------------------
# vector_search (hybrid RAG)
# --------------------------------------------------------------------------

class VectorSearchInput(BaseModel):
    query: str = Field(..., min_length=1)
    k: int = Field(3, ge=1, le=20)


class VectorSearchHit(BaseModel):
    text: str
    topic: str
    citation: Optional[str] = None


class VectorSearchOutput(BaseModel):
    hits: List[VectorSearchHit] = Field(default_factory=list)


def _vector_search(input: VectorSearchInput) -> VectorSearchOutput:
    from app.services.rag.hybrid import hybrid_search

    entries = hybrid_search(input.query, k=input.k)
    return VectorSearchOutput(hits=[
        VectorSearchHit(text=e.text, topic=e.topic, citation=e.citation) for e in entries
    ])


# --------------------------------------------------------------------------
# statute_lookup
# --------------------------------------------------------------------------

class StatuteLookupInput(BaseModel):
    topic: str = Field(..., min_length=1)


class StatuteLookupOutput(BaseModel):
    citations: List[VectorSearchHit] = Field(default_factory=list)


def _statute_lookup(input: StatuteLookupInput) -> StatuteLookupOutput:
    """Corpus entries for this topic that carry a real, confidently-
    verifiable citation (services/rag/corpus.py's own convention: `None`
    means "a general principle, not a specific statute" -- this tool is
    specifically for the case a caller wants a citable source, so entries
    without one are filtered out rather than returned with a null citation)."""
    from app.services.rag.corpus import LEGAL_KNOWLEDGE_BASE

    matches = [
        VectorSearchHit(text=e.text, topic=e.topic, citation=e.citation)
        for e in LEGAL_KNOWLEDGE_BASE
        if e.topic == input.topic and e.citation is not None
    ]
    return StatuteLookupOutput(citations=matches)


# --------------------------------------------------------------------------
# date_math -- deterministic, no LLM, no model call at all
# --------------------------------------------------------------------------

class DateMathInput(BaseModel):
    reference_date: date
    amount: int
    unit: str = Field(..., description="'day' | 'week' | 'month' | 'year'")
    direction: str = Field("after", description="'after' (add) or 'before' (subtract)")


class DateMathOutput(BaseModel):
    result_date: date


_UNIT_KWARGS = {"day": "days", "week": "weeks", "month": "months", "year": "years"}


def _date_math(input: DateMathInput) -> DateMathOutput:
    """`reference_date + amount unit`, correctly (a month/year is not a
    fixed number of days -- relativedelta handles calendar arithmetic, a
    plain timedelta would silently mis-add across month/year boundaries).
    Deliberately does not parse a free-text "expression" string -- that
    ambiguity (is "30 days" relative to today or to some other clause's
    trigger event?) is exactly why services/nlp/temporal.py refuses to
    resolve a bare duration on its own; this tool only does the arithmetic
    once a caller has already resolved which reference_date to use."""
    if input.unit not in _UNIT_KWARGS:
        raise ToolError(f"unit must be one of {sorted(_UNIT_KWARGS)}, got {input.unit!r}")
    if input.direction not in ("after", "before"):
        raise ToolError(f"direction must be 'after' or 'before', got {input.direction!r}")

    signed_amount = input.amount if input.direction == "after" else -input.amount
    delta = relativedelta(**{_UNIT_KWARGS[input.unit]: signed_amount})
    return DateMathOutput(result_date=input.reference_date + delta)


# --------------------------------------------------------------------------
# clause_diff -- deterministic, stdlib difflib
# --------------------------------------------------------------------------

class ClauseDiffInput(BaseModel):
    clause_a: str
    clause_b: str


class ClauseDiffOutput(BaseModel):
    similarity: float
    diff_lines: List[str]


def _clause_diff(input: ClauseDiffInput) -> ClauseDiffOutput:
    matcher = difflib.SequenceMatcher(None, input.clause_a, input.clause_b)
    diff_lines = list(difflib.unified_diff(
        input.clause_a.splitlines(), input.clause_b.splitlines(),
        fromfile="clause_a", tofile="clause_b", lineterm="",
    ))
    return ClauseDiffOutput(similarity=matcher.ratio(), diff_lines=diff_lines)


# --------------------------------------------------------------------------
# request_human_approval -- honestly scoped to the async review queue
# --------------------------------------------------------------------------

class HumanApprovalInput(BaseModel):
    payload: Dict[str, Any]
    reason: str = Field(..., min_length=1)


class HumanApprovalOutput(BaseModel):
    status: str = "pending_review"
    reason: str


def _request_human_approval(input: HumanApprovalInput) -> HumanApprovalOutput:
    """Does NOT block execution -- this codebase has no synchronous
    human-in-the-loop mechanism. Returns a structured "pending" marker; the
    caller is responsible for setting `needs_human_review=True` on whatever
    record it's producing (app/routes/review.py's queue is the actual
    async follow-up a human acts on)."""
    return HumanApprovalOutput(reason=input.reason)


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    input_model: Type[BaseModel]
    output_model: Type[BaseModel]
    fn: Callable[[BaseModel], BaseModel]


TOOL_REGISTRY: Dict[str, ToolSpec] = {
    "kg_query": ToolSpec(
        "kg_query", "All clauses across the org's portfolio using a defined term.",
        KGQueryInput, KGQueryOutput, _kg_query,
    ),
    "kg_conflicts": ToolSpec(
        "kg_conflicts", "Candidate cross-document obligation/prohibition conflicts sharing a term.",
        KGQueryInput, KGConflictOutput, _kg_conflicts,
    ),
    "vector_search": ToolSpec(
        "vector_search", "Hybrid (dense+sparse+graph) search over the legal knowledge base.",
        VectorSearchInput, VectorSearchOutput, _vector_search,
    ),
    "statute_lookup": ToolSpec(
        "statute_lookup", "Citable statute/regulation entries for a topic.",
        StatuteLookupInput, StatuteLookupOutput, _statute_lookup,
    ),
    "date_math": ToolSpec(
        "date_math", "Deterministic calendar arithmetic: reference_date +/- amount unit.",
        DateMathInput, DateMathOutput, _date_math,
    ),
    "clause_diff": ToolSpec(
        "clause_diff", "Structured similarity + unified diff between two clause texts.",
        ClauseDiffInput, ClauseDiffOutput, _clause_diff,
    ),
    "request_human_approval": ToolSpec(
        "request_human_approval", "Records a pending-review request (async, not a blocking call).",
        HumanApprovalInput, HumanApprovalOutput, _request_human_approval,
    ),
}


def call_tool(name: str, **kwargs: Any) -> BaseModel:
    """The single entrypoint every caller uses. Validates `kwargs` against
    the tool's input schema, runs it, validates the result against the
    output schema -- raises ToolError on any of these instead of letting a
    malformed call or a misbehaving tool implementation propagate silently."""
    spec = TOOL_REGISTRY.get(name)
    if spec is None:
        raise ToolError(f"Unknown tool {name!r}. Registered tools: {sorted(TOOL_REGISTRY)}")

    try:
        validated_input = spec.input_model(**kwargs)
    except Exception as e:
        raise ToolError(f"Invalid input for tool {name!r}: {e}") from e

    result = spec.fn(validated_input)

    if not isinstance(result, spec.output_model):
        raise ToolError(
            f"Tool {name!r} returned {type(result).__name__}, expected {spec.output_model.__name__}"
        )
    return result


def tool_json_schemas() -> Dict[str, dict]:
    """One JSON schema per tool (input side) -- what a future grammar-
    constrained tool-calling LLM would be given to constrain its output
    against, once a self-hosted model capable of it is actually served
    (docs/v2/ROADMAP.md Phase 6)."""
    return {name: spec.input_model.model_json_schema() for name, spec in TOOL_REGISTRY.items()}
