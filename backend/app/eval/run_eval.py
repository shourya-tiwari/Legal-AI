# backend/app/eval/run_eval.py
"""
Runnable eval harness for the rule-based NLP pipeline. Reports clause-type
accuracy and deontic-tag recall against the hand-curated gold set
(gold_set.py). This is the lightweight, CPU-only stand-in for the full
Ragas + CUAD/ContractNLI harness in docs/v2/AI_STACK.md — see gold_set.py's
docstring for why, and docs/v2/TASKS.md for the deferred full version.

Usage (from backend/):
    python -m app.eval.run_eval
"""
from __future__ import annotations

from dataclasses import dataclass

from app.eval.gold_set import GOLD_SET
from app.services.nlp.clause_classifier import classify_clause_type
from app.services.nlp.deontic import tag_deontic_modality_rule_based


@dataclass
class EvalResult:
    total: int
    clause_type_correct: int
    deontic_recall_hits: int
    deontic_recall_total: int

    @property
    def clause_type_accuracy(self) -> float:
        return self.clause_type_correct / self.total if self.total else 0.0

    @property
    def deontic_recall(self) -> float:
        return self.deontic_recall_hits / self.deontic_recall_total if self.deontic_recall_total else 1.0


def run_eval(verbose: bool = False) -> EvalResult:
    clause_type_correct = 0
    deontic_hits = 0
    deontic_total = 0

    for example in GOLD_SET:
        predicted_type, _ = classify_clause_type(example["text"])
        is_type_correct = predicted_type == example["expected_clause_type"]
        clause_type_correct += int(is_type_correct)

        predicted_modalities = {t.modality for t in tag_deontic_modality_rule_based(example["text"])}
        expected_modalities = set(example["expected_deontic_modalities"])
        deontic_total += len(expected_modalities)
        deontic_hits += len(expected_modalities & predicted_modalities)

        if verbose:
            marker = "OK" if is_type_correct else "MISS"
            print(f"[{marker}] type={predicted_type!r} expected={example['expected_clause_type']!r} :: {example['text'][:70]}")

    return EvalResult(
        total=len(GOLD_SET),
        clause_type_correct=clause_type_correct,
        deontic_recall_hits=deontic_hits,
        deontic_recall_total=deontic_total,
    )


if __name__ == "__main__":
    result = run_eval(verbose=True)
    print(f"\nClause type accuracy: {result.clause_type_accuracy:.1%} ({result.clause_type_correct}/{result.total})")
    print(f"Deontic tag recall:   {result.deontic_recall:.1%} ({result.deontic_recall_hits}/{result.deontic_recall_total})")
