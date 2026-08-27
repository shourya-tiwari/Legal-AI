# backend/app/agents/risk_compliance.py
"""
Risk & Compliance agent: keyword risk flags per clause (reuses
services/risk_radar/rules.py -- no new detection logic, same rationale as
the Extraction agent) plus a knowledge-graph check for candidate
cross-document conflicts on any defined term this document uses (reuses
services/kg/queries.py). The AI risk pass from services/risk_radar/detector.py
is deliberately NOT called here -- that's a per-clause Gemini call, and
Phase 4's agent-level risk pass is meant to be the fast, deterministic
Tier 0 sweep; nothing stops a future iteration from adding an AI-escalation
branch here the same way the NLP pipeline does for deontic tagging.
"""
from __future__ import annotations

from app.services.kg.client import get_kg_client
from app.services.kg.queries import find_potential_conflicts
from app.services.risk_radar.rules import RISKY_TERMS, find_keyword_flags

from .state import AgentStep, CaseState, KGConflictFinding, RiskFinding


def run_risk_compliance(state: CaseState) -> dict:
    risk_findings = []
    for clause in state.clauses:
        for flag in find_keyword_flags(clause.text, RISKY_TERMS):
            risk_findings.append(
                RiskFinding(
                    clause_id=clause.id,
                    term=flag["term"],
                    explanation=flag["predefined_explanation"],
                    source="keyword",
                )
            )

    kg_conflicts = []
    client = get_kg_client()
    if client.available:
        seen_terms = {t for clause in state.clauses for t in clause.defined_terms_used}
        for term in seen_terms:
            for conflict in find_potential_conflicts(client, state.org_id, term):
                kg_conflicts.append(
                    KGConflictFinding(
                        term=term,
                        obligation_clause=conflict["obligation"]["text"],
                        prohibition_clause=conflict["prohibition"]["text"],
                        obligation_document_id=conflict["obligation"]["document_id"],
                        prohibition_document_id=conflict["prohibition"]["document_id"],
                    )
                )

    step = AgentStep(
        agent_name="risk_compliance",
        input_summary=f"{len(state.clauses)} clauses",
        output_summary=f"{len(risk_findings)} keyword risk flags, {len(kg_conflicts)} candidate KG conflicts",
    )

    return {"risk_findings": risk_findings, "kg_conflicts": kg_conflicts, "trace": state.trace + [step]}
