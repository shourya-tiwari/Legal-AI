# backend/app/agents/planner.py
"""
The Orchestrator/Planner agent (docs/v2/AGENTS.md).

Runs once, right after extraction, and produces `state.plan` -- the ordered
list of node ids the graph will execute. Everything else in the pipeline is
still a real agent node; the planner just decides which of the middle ones
(`PLANNABLE`) are worth running for *this* document.

Two modes:
  - rule-based (default): deterministic heuristics over the extracted clauses
    -- a cheap keyword pre-scan (the same `find_keyword_flags` the Risk agent
    uses), ambiguity flags, defined-term presence. Fast, offline, testable.
  - LLM-assisted (`use_ai_planner=True`): the Model Router picks the plan;
    falls back to the rule plan on any error (including "no LLM served").

`verifier` is always appended last -- it is the mandatory release gate and is
never the planner's to omit.
"""
from __future__ import annotations

import json
import logging
import re
from typing import List, Tuple

from app.services.model_router import ModelRouterError, generate_content
from app.services.risk_radar.rules import RISKY_TERMS, find_keyword_flags

from .registry import AGENT_REGISTRY, PLANNABLE
from .state import AgentStep, CaseState

logger = logging.getLogger("legalai.agents.planner")

# A named preset is the starting point; the rule engine then prunes it.
ANALYSIS_MODES = {
    "full": ["risk_compliance", "research", "summarize"],
    "quick": ["risk_compliance", "summarize"],   # skip the RAG research leg
    "risk_only": ["risk_compliance"],            # just the flags, no narrative
    "extract_only": [],                          # clause objects + the gate only
}
DEFAULT_MODE = "full"

_VERIFIER = "verifier"


def _signals(state: CaseState) -> dict:
    """Cheap pre-scan of the already-extracted clauses."""
    keyword_hits = sum(len(find_keyword_flags(c.text, RISKY_TERMS)) for c in state.clauses)
    ambiguous = sum(1 for c in state.clauses if c.ambiguity_flags)
    with_terms = sum(1 for c in state.clauses if c.defined_terms_used)
    return {
        "clauses": len(state.clauses),
        "keyword_hits": keyword_hits,
        "ambiguous_clauses": ambiguous,
        "clauses_with_defined_terms": with_terms,
    }


def _rule_plan(state: CaseState, mode: str) -> Tuple[List[str], str]:
    base = list(ANALYSIS_MODES.get(mode, ANALYSIS_MODES[DEFAULT_MODE]))
    sig = _signals(state)

    if mode != "full":
        return base, f"analysis_mode={mode} preset over {sig['clauses']} clauses"

    has_risk_signal = sig["keyword_hits"] > 0 or sig["ambiguous_clauses"] > 0
    if has_risk_signal:
        return base, (
            f"{sig['keyword_hits']} risky-term hit(s), {sig['ambiguous_clauses']} ambiguous "
            f"clause(s) in {sig['clauses']} clauses -> full analysis"
        )

    # Nothing to research or summarize. Keep the risk sweep only if there are
    # defined terms whose cross-document KG conflict check is still worth it.
    if sig["clauses_with_defined_terms"] > 0:
        return ["risk_compliance"], (
            f"no risk/ambiguity signal in {sig['clauses']} clauses; "
            f"{sig['clauses_with_defined_terms']} clause(s) use defined terms -> "
            f"KG conflict check only, no research/summary"
        )
    return [], (
        f"no risk/ambiguity signal and no defined terms in {sig['clauses']} clauses -> "
        f"structural extraction only"
    )


_AI_PROMPT = """You are the planner for a legal-contract analysis pipeline. Given a document
summary, choose which of these optional agents to run (in this order): {menu}

Document: {n_clauses} clauses. Clause types present: {types}.
Keyword risk hits: {keyword_hits}. Ambiguous clauses: {ambiguous}.

Reply with ONLY a JSON array of agent names to run, e.g. ["risk_compliance","summarize"].
Include an agent only if it would add value for THIS document. "verifier" always runs and
must NOT be in your list."""


def _ai_plan(state: CaseState) -> Tuple[List[str], str]:
    menu = "; ".join(f"{n} ({AGENT_REGISTRY[n].description})" for n in PLANNABLE)
    types = sorted({c.clause_type for c in state.clauses if c.clause_type}) or ["unknown"]
    sig = _signals(state)
    prompt = _AI_PROMPT.format(
        menu=menu, n_clauses=sig["clauses"], types=", ".join(types),
        keyword_hits=sig["keyword_hits"], ambiguous=sig["ambiguous_clauses"],
    )
    raw = generate_content(prompt, task="agent_plan", sensitivity=state.sensitivity_tier,
                           temperature=0.0, max_output_tokens=60)  # may raise ModelRouterError
    match = re.search(r"\[.*?\]", raw, re.DOTALL)
    if not match:
        raise ValueError(f"planner LLM returned no JSON array: {raw!r}")
    chosen = json.loads(match.group(0))
    plan = [a for a in PLANNABLE if a in chosen]  # normalize order, drop unknowns
    return plan, f"LLM planner chose {plan} (raw={chosen})"


def run_planner(state: CaseState) -> dict:
    mode = state.analysis_mode if state.analysis_mode in ANALYSIS_MODES else DEFAULT_MODE

    if state.use_ai_planner:
        try:
            plan, rationale = _ai_plan(state)
        except (ModelRouterError, ValueError, json.JSONDecodeError, KeyError) as e:
            logger.info("AI planner unavailable/invalid (%s); using rule plan.", e)
            plan, rationale = _rule_plan(state, mode)
            rationale = f"[ai->rule fallback] {rationale}"
    else:
        plan, rationale = _rule_plan(state, mode)

    plan = plan + [_VERIFIER]  # mandatory gate, always last

    step = AgentStep(
        agent_name="planner",
        input_summary=f"analysis_mode={mode} use_ai_planner={state.use_ai_planner} "
                      f"({len(state.clauses)} clauses)",
        output_summary=f"plan={plan} :: {rationale}",
    )
    return {
        "plan": plan,
        "plan_rationale": rationale,
        "ran_steps": state.ran_steps + ["planner"],
        "trace": state.trace + [step],
    }
