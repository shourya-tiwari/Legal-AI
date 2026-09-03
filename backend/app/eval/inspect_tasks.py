# backend/app/eval/inspect_tasks.py
"""
Inspect AI suite seed (docs/v2/MODEL_STACK.md "Evaluation", ROADMAP Phase 5/6
"Adopt Inspect AI as the suite backbone").

The backbone the legal gold set and (Phase 6) the LegalBench / CUAD /
ContractNLI corpora will hang off. It houses ONE task today -- the rule-based
clause-type classifier scored against the hand-curated gold set -- to prove
the harness wraps our own components, not just LLM calls.

Runnable once `pip install -r requirements-eval.txt`:

    inspect eval app/eval/inspect_tasks.py

The fast pre-merge gate stays app/eval/run_eval.py + tests/test_eval_gate.py;
this is the richer, extensible harness alongside it. Next step (Phase 6):
add a `cuad_extraction` task over app/eval/datasets.load_cuad() and point its
graded solver at the self-hosted model via the Model Router.
"""
from __future__ import annotations

from app.eval.gold_set import GOLD_SET

try:
    from inspect_ai import Task, task
    from inspect_ai.dataset import Sample
    from inspect_ai.scorer import match
    from inspect_ai.solver import Generate, TaskState, solver

    _INSPECT_AVAILABLE = True
except Exception:  # inspect-ai not installed -- module stays import-safe
    _INSPECT_AVAILABLE = False


if _INSPECT_AVAILABLE:

    @solver
    def rule_based_clause_classifier():
        from app.services.nlp.clause_classifier import classify_clause_type

        async def solve(state: TaskState, generate: Generate) -> TaskState:
            predicted, _score = classify_clause_type(state.input_text)
            state.output.completion = predicted or "unknown"
            return state

        return solve

    @task
    def legal_clause_type() -> Task:
        samples = [
            Sample(input=ex["text"], target=ex["expected_clause_type"])
            for ex in GOLD_SET
        ]
        return Task(
            dataset=samples,
            solver=rule_based_clause_classifier(),
            scorer=match(location="any"),
        )
