# backend/app/agents/research.py
"""
Clause Research agent: runs hybrid RAG (services/rag/) on clauses worth
grounding in outside sources -- ones already flagged as ambiguous or risky by
earlier agents. Deliberately not run on every clause: most clauses (payment
schedules, boilerplate recitals) have nothing a legal-knowledge-base lookup
would add, and retrieval isn't free (an embedding call per query).
"""
from __future__ import annotations

from typing import Dict, List

from app.services.rag.graph_retrieval import graph_hits_for_terms
from app.services.rag.hybrid import hybrid_search

from .state import AgentStep, CaseState

MAX_HITS_PER_CLAUSE = 3


def _needs_research(state: CaseState, clause) -> bool:
    if clause.ambiguity_flags:
        return True
    return any(f.clause_id == clause.id for f in state.risk_findings)


def run_research(state: CaseState) -> dict:
    citations: Dict[int, List[dict]] = {}

    for clause in state.clauses:
        if not _needs_research(state, clause):
            continue
        # GraphRAG leg: other portfolio clauses that share this clause's
        # defined terms (fail-soft -- [] when Memgraph is unreachable).
        graph_hits = graph_hits_for_terms(
            state.org_id, clause.defined_terms_used, exclude_texts=[clause.text]
        )
        hits = hybrid_search(clause.text, k=MAX_HITS_PER_CLAUSE, graph_hits=graph_hits)
        if hits:
            citations[clause.id] = [h.model_dump() for h in hits]

    step = AgentStep(
        agent_name="clause_research",
        input_summary=f"{sum(1 for c in state.clauses if _needs_research(state, c))} clauses flagged for research",
        output_summary=f"citations found for {len(citations)} clauses",
    )

    return {"research_citations": citations, "trace": state.trace + [step]}
