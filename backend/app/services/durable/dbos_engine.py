# backend/app/services/durable/dbos_engine.py
"""
DBOS-driven agent pipeline execution (docs/v2/ROADMAP.md Phase 7 "Durable
execution & Memory Service"). An alternative *orchestrator* over the exact
same building blocks `app/agents/graph.py`'s LangGraph driver uses --
`AGENT_REGISTRY`, `run_planner`, `CaseState` -- not a wrapper around
LangGraph's own execution loop. That distinction is load-bearing: LangGraph's
`.invoke()` is a single opaque call with no mid-execution checkpoint hook to
attach to, so durability has to be implemented at the level of "call each
agent node function in turn," reimplementing `graph.py::_next_step`'s plan-
dispatch loop here, one `@DBOS.step()` per agent node, wrapped in one
`@DBOS.workflow()` for the whole run. If the process crashes after node N
completes, DBOS's checkpoint means node N does not re-run when the workflow
resumes -- only N+1 onward.

Only imported when `Settings.DURABLE_EXECUTION_ENABLED=true` (see
`app/services/durable/__init__.py`'s docstring) -- importing this module
immediately constructs the DBOS singleton and requires a real Postgres
`Settings.DBOS_DATABASE_URL` (DBOS has no SQLite mode, unlike the rest of
this app's persistence layer). `app/agents/graph.py`'s synchronous,
in-request LangGraph execution remains the default; this is an opt-in
alternative, not a replacement -- swapping the default requires the same
kind of "wrong pick is expensive to unwind without a real target" caution
docs/v2/ROADMAP.md names, which this environment still can't fully resolve
(no long-running production traffic to observe recovery against), even
though the mechanism itself is now real and tested.
"""
from __future__ import annotations

import logging

from dbos import DBOS, DBOSConfig

from app.agents.planner import run_planner
from app.agents.registry import AGENT_REGISTRY, EXECUTABLE_NODE_IDS
from app.agents.state import CaseState
from app.config import get_settings

logger = logging.getLogger("legalai.durable.dbos_engine")

_settings = get_settings()
_config: DBOSConfig = {
    "name": "legalai-agent-pipeline",
    "database_url": _settings.DBOS_DATABASE_URL,
}
DBOS(config=_config)

def _make_step(node_id: str):
    """One fixed, module-level @DBOS.step() per registry node -- DBOS
    identifies a step/workflow by its registered function, so these are all
    created once at import time (this function runs once per node_id below,
    not per call), never dynamically per workflow invocation. A per-call
    closure would register a "new" function on every invocation and break
    recovery matching across process restarts, which is the entire point
    of this module."""
    fn = AGENT_REGISTRY[node_id].fn

    @DBOS.step(name=f"agent_{node_id}")
    def _step(state_dict: dict) -> dict:
        state = CaseState(**state_dict)
        return fn(state)

    return _step


_STEPS = {node_id: _make_step(node_id) for node_id in EXECUTABLE_NODE_IDS}


@DBOS.workflow(name="case_analysis")
def _case_analysis_workflow(initial_state_dict: dict) -> dict:
    state = CaseState(**initial_state_dict)

    update = _STEPS["extraction"](state.model_dump())
    state = state.model_copy(update={**update, "ran_steps": state.ran_steps + ["extraction"]})

    planner_update = run_planner(state)  # deterministic/cheap -- not a durable step of its own
    state = state.model_copy(update=planner_update)

    for node_id in state.plan:
        if node_id in state.ran_steps:
            continue
        update = _STEPS[node_id](state.model_dump())
        state = state.model_copy(update={**update, "ran_steps": state.ran_steps + [node_id]})

    return state.model_dump()


_launched = False


def ensure_launched() -> None:
    """Idempotent -- DBOS.launch() must run exactly once per process before
    any workflow call, and triggers automatic recovery of any workflow left
    pending by a prior crash of a process with the same application code."""
    global _launched
    if not _launched:
        DBOS.launch()
        _launched = True
        logger.info("DBOS durable execution engine launched (database_url configured).")


def run_case_analysis_durable(
    document_id: int,
    org_id: int,
    full_text: str,
    *,
    analysis_mode: str = "full",
    use_ai_planner: bool = False,
    sensitivity_tier: str = "internal",
) -> CaseState:
    """Same signature and contract as app.agents.graph.run_case_analysis,
    driven by DBOS instead of LangGraph -- each agent node is an
    individually durable, checkpointed step."""
    ensure_launched()
    initial_state = CaseState(
        document_id=document_id, org_id=org_id, full_text=full_text,
        analysis_mode=analysis_mode, use_ai_planner=use_ai_planner,
        sensitivity_tier=sensitivity_tier,
    )
    result_dict = _case_analysis_workflow(initial_state.model_dump())
    return CaseState(**result_dict)
