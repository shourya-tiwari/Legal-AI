# backend/app/agents/registry.py
"""
The agent catalog the Planner draws from (docs/v2/AGENTS.md).

Adding a new agent to the pipeline is:
  1. write `run_<agent>(state) -> dict` (a node fn, same shape as the others)
  2. add one `AgentSpec` here
  3. add one rule to `app/agents/planner.py`

That's the whole extensibility contract -- `graph.py` builds the graph from
this registry, and the planner reasons over it.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Tuple

from .extraction import run_extraction
from .research import run_research
from .risk_compliance import run_risk_compliance
from .summary import run_summary
from .verifier import run_verifier


@dataclass(frozen=True)
class AgentSpec:
    node_id: str            # graph node id (also the registry key and the plan token)
    fn: Callable            # the node function; None for `planner` (wired specially)
    always: bool = False    # the planner cannot drop this one
    description: str = ""    # shown to the LLM planner and in docs


# `planner.fn` is None -- graph.py wires run_planner directly (it must not be
# wrapped the way the executable nodes are).
AGENT_REGISTRY: Dict[str, AgentSpec] = {
    "extraction": AgentSpec(
        "extraction", run_extraction, always=True,
        description="Segment the document into typed Clause objects (NLP pipeline).",
    ),
    "planner": AgentSpec(
        "planner", None, always=True,  # type: ignore[arg-type]
        description="Decide which of the middle agents to run for this document.",
    ),
    "risk_compliance": AgentSpec(
        "risk_compliance", run_risk_compliance,
        description="Keyword risk flags per clause + cross-document KG conflict candidates.",
    ),
    "research": AgentSpec(
        "research", run_research,
        description="Hybrid RAG over the legal knowledge base for flagged/ambiguous clauses.",
    ),
    "summarize": AgentSpec(
        "summarize", run_summary,
        description="Generate a plain-English risk summary citing retrieved sources.",
    ),
    "verifier": AgentSpec(
        "verifier", run_verifier, always=True,
        description="Mandatory gate: citation check, KG consistency, NLI faithfulness.",
    ),
}

# The agents the planner may include or drop (order matters -- it's the
# execution order within a plan).
PLANNABLE: Tuple[str, ...] = ("risk_compliance", "research", "summarize")

# Node ids for graph wiring / plan validation.
EXECUTABLE_NODE_IDS: Tuple[str, ...] = tuple(
    nid for nid, spec in AGENT_REGISTRY.items() if spec.fn is not None
)
