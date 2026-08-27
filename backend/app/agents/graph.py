# backend/app/agents/graph.py
"""
Wires the five agent nodes into a fixed LangGraph pipeline: extract -> risk &
compliance -> research -> summarize -> verify. This is a fixed sequence, not
a dynamic planner choosing which agents to run -- docs/v2/AGENTS.md's
Orchestrator/Planner agent is a genuine future step (e.g. skipping research/
summary entirely for a document with zero risk findings), not implemented
here to keep Phase 4's MVP scope honest about what it actually is.

Runs synchronously within the request (no Temporal). docs/v2/AGENTS.md calls
for Temporal-backed durable execution so a workflow survives a process crash
and can retry individual steps -- a real capability this doesn't have yet.
For a single-document analysis on the order of seconds, that durability
isn't earning its complexity cost yet; introduce it once a workflow is long/
expensive enough that losing progress mid-run is a real problem, not before.
"""
from __future__ import annotations

from functools import lru_cache

from langgraph.graph import END, StateGraph

from .extraction import run_extraction
from .research import run_research
from .risk_compliance import run_risk_compliance
from .state import CaseState
from .summary import run_summary
from .verifier import run_verifier


@lru_cache
def _compiled_graph():
    graph = StateGraph(CaseState)
    graph.add_node("extraction", run_extraction)
    graph.add_node("risk_compliance", run_risk_compliance)
    graph.add_node("research", run_research)
    # Node id is "summarize", not "summary" -- LangGraph forbids a node name
    # that collides with a state field name, and CaseState.summary is the
    # actual output field this node writes to.
    graph.add_node("summarize", run_summary)
    graph.add_node("verifier", run_verifier)

    graph.set_entry_point("extraction")
    graph.add_edge("extraction", "risk_compliance")
    graph.add_edge("risk_compliance", "research")
    graph.add_edge("research", "summarize")
    graph.add_edge("summarize", "verifier")
    graph.add_edge("verifier", END)

    return graph.compile()


def run_case_analysis(document_id: int, org_id: int, full_text: str) -> CaseState:
    initial_state = CaseState(document_id=document_id, org_id=org_id, full_text=full_text)
    result = _compiled_graph().invoke(initial_state)
    return CaseState(**result)
