# backend/app/agents/state.py
"""
The shared CaseState every agent reads/writes (docs/v2/AGENTS.md). The
pipeline is planner-driven (Phase 7): after extraction, the `planner` node
sets `plan` -- the ordered node ids to run -- and the graph dispatches by it
instead of a fixed chain. Still not the full docs/v2 vision (no memory_refs,
no per-tier routing, no dynamic tool selection) -- those are real future work.
"""
from __future__ import annotations

from typing import Dict, List

from pydantic import BaseModel, Field

from app.services.nlp.schema import ClauseObject


class AgentStep(BaseModel):
    """One row of the audit trail -- also what gets persisted to the
    `agent_traces` table (db_models.py) after a run completes."""
    agent_name: str
    input_summary: str
    output_summary: str


class RiskFinding(BaseModel):
    clause_id: int
    term: str
    explanation: str
    source: str  # "keyword" -- from services/risk_radar/rules.py


class KGConflictFinding(BaseModel):
    term: str
    obligation_clause: str
    prohibition_clause: str
    obligation_document_id: int
    prohibition_document_id: int


class CaseState(BaseModel):
    document_id: int
    org_id: int
    full_text: str = ""

    # ---- planning (Phase 7 Orchestrator/Planner) ----
    # analysis_mode: a named preset the request asks for ("full" | "risk_only"
    #   | "quick" | "extract_only"); the planner starts from its agent list.
    # use_ai_planner: let an LLM choose the plan (falls back to rules offline).
    # plan: the ordered node ids the planner chose (always ends with "verifier").
    # ran_steps: node ids already executed -- the graph's dispatch key.
    analysis_mode: str = "full"
    use_ai_planner: bool = False
    plan: List[str] = Field(default_factory=list)
    plan_rationale: str = ""
    ran_steps: List[str] = Field(default_factory=list)

    clauses: List[ClauseObject] = Field(default_factory=list)
    risk_findings: List[RiskFinding] = Field(default_factory=list)
    kg_conflicts: List[KGConflictFinding] = Field(default_factory=list)
    # clause id -> list of {text, topic, citation} dicts retrieved for it
    research_citations: Dict[int, List[dict]] = Field(default_factory=dict)

    summary: str = ""
    summary_citation_count: int = 0
    invalid_citation_numbers: List[int] = Field(default_factory=list)
    faithfulness_ok: bool = True
    # "nli" (real entailment head) or "lexical_fallback" (NLI head not installed)
    faithfulness_method: str = "nli"
    # claim sentences a source contradicted or failed to support (NLI method only)
    unsupported_claims: List[str] = Field(default_factory=list)
    needs_human_review: bool = False

    trace: List[AgentStep] = Field(default_factory=list)
