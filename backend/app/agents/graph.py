# backend/app/agents/graph.py
"""
The agent pipeline as a **planner-driven** LangGraph (docs/v2/AGENTS.md).

  extraction -> planner -> (dispatch by state.plan) -> ... -> verifier -> END

`extraction` and `planner` always run. `planner` sets `state.plan` (an ordered
list of node ids ending in "verifier"); after the planner and after every
executable node, `_next_step` picks the first planned node not yet in
`state.ran_steps`, or END. So a document with no risk signal runs
`extraction -> planner -> verifier` and skips research/summary entirely.

The graph is built from `app/agents/registry.py` -- adding an agent is a
registry entry + a planner rule, no wiring change here.

Still runs synchronously in-request (no durable-execution engine). For a
single-document analysis on the order of seconds that durability isn't
earning its complexity yet; it lands with the Phase 7 durable engine
(`docs/v2/BACKEND.md`), and the abstraction here stays engine-agnostic.
"""
from __future__ import annotations

from functools import lru_cache

from langgraph.graph import END, StateGraph

from .planner import run_planner
from .registry import AGENT_REGISTRY, EXECUTABLE_NODE_IDS
from .state import CaseState


def _planned(node_id: str):
    """Wrap an executable node so it records that it ran (the dispatch key)."""
    fn = AGENT_REGISTRY[node_id].fn

    def wrapped(state: CaseState) -> dict:
        update = fn(state)
        update["ran_steps"] = state.ran_steps + [node_id]
        return update

    wrapped.__name__ = f"planned_{node_id}"
    return wrapped


def _next_step(state: CaseState) -> str:
    """First planned node not yet run, else END."""
    for node_id in state.plan:
        if node_id not in state.ran_steps:
            return node_id
    return END


@lru_cache
def _compiled_graph():
    graph = StateGraph(CaseState)

    graph.add_node("extraction", _planned("extraction"))
    graph.add_node("planner", run_planner)  # sets ran_steps itself; not wrapped
    for node_id in EXECUTABLE_NODE_IDS:
        if node_id == "extraction":
            continue
        graph.add_node(node_id, _planned(node_id))

    graph.set_entry_point("extraction")
    graph.add_edge("extraction", "planner")

    # After the planner and every executable node, dispatch by the plan.
    path_map = {nid: nid for nid in EXECUTABLE_NODE_IDS if nid != "extraction"}
    path_map[END] = END
    for source in ("planner", *(n for n in EXECUTABLE_NODE_IDS if n != "extraction")):
        graph.add_conditional_edges(source, _next_step, path_map)

    return graph.compile()


def run_case_analysis(
    document_id: int,
    org_id: int,
    full_text: str,
    *,
    analysis_mode: str = "full",
    use_ai_planner: bool = False,
    sensitivity_tier: str = "internal",
) -> CaseState:
    initial_state = CaseState(
        document_id=document_id,
        org_id=org_id,
        full_text=full_text,
        analysis_mode=analysis_mode,
        use_ai_planner=use_ai_planner,
        sensitivity_tier=sensitivity_tier,
    )
    result = _compiled_graph().invoke(initial_state)
    return CaseState(**result)
