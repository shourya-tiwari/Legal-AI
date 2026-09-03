# backend/app/agents/extraction.py
"""Extraction agent: wraps Phase 2's NLP pipeline (docs/v2/AGENTS.md's
Extraction agent). No new logic -- an agent, in this codebase's sense, is a
node that owns one step of the pipeline and contributes to the trace; the
actual extraction work already exists in services/nlp/."""
from __future__ import annotations

from app.services.nlp.pipeline import build_clause_objects

from .state import AgentStep, CaseState


def run_extraction(state: CaseState) -> dict:
    clauses = build_clause_objects(state.full_text, sensitivity=state.sensitivity_tier)

    step = AgentStep(
        agent_name="extraction",
        input_summary=f"{len(state.full_text)} chars of contract text",
        output_summary=f"{len(clauses)} clauses extracted",
    )

    return {"clauses": clauses, "trace": state.trace + [step]}
