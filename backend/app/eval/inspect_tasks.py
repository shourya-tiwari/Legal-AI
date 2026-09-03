# backend/app/eval/inspect_tasks.py
"""
Inspect AI suite wrappers (docs/v2/MODEL_STACK.md "Evaluation", ROADMAP Phase 6
"Adopt Inspect AI as the suite backbone").

The graded logic lives in `app/eval/tasks.py` (runnable with no inspect-ai);
this module exposes it as Inspect `@task`s for the richer reporting / logging
Inspect gives. Runnable once `pip install -r requirements-eval.txt`:

    inspect eval app/eval/inspect_tasks.py@rule_clause_type
    inspect eval app/eval/inspect_tasks.py@legalbench_qa --model openai/qwen3:8b \
        -M base_url=http://localhost:11434/v1

The fast pre-merge gate stays app/eval/run_eval.py + tests/test_eval_gate.py.
"""
from __future__ import annotations

from app.eval.gold_set import GOLD_SET

try:
    from inspect_ai import Task, task
    from inspect_ai.dataset import Sample
    from inspect_ai.scorer import match
    from inspect_ai.solver import Generate, TaskState, generate, solver

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
    def rule_clause_type() -> Task:
        samples = [
            Sample(input=ex["text"], target=ex["expected_clause_type"])
            for ex in GOLD_SET
        ]
        return Task(dataset=samples, solver=rule_based_clause_classifier(),
                    scorer=match(location="any"))

    @task
    def legalbench_qa(limit_per: int = 25) -> Task:
        """Yes/No LegalBench QA (CUAD + ContractNLI subtasks) -- pass a --model
        to grade a served LLM; the cutover gate (app/eval/cutover_gate.py)
        automates the self-hosted-vs-Gemini comparison."""
        from app.eval.datasets import (CONTRACT_NLI_SUBTASKS, CUAD_SUBTASKS,
                                       load_legalbench)

        samples = []
        for st in CUAD_SUBTASKS[:4] + CONTRACT_NLI_SUBTASKS[:2]:
            try:
                for e in load_legalbench(st, limit=limit_per):
                    samples.append(Sample(input=e["input"], target=e["answer"]))
            except Exception:
                continue
        return Task(
            dataset=samples,
            solver=generate(),
            scorer=match(location="begin"),
        )
