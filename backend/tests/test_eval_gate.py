"""
The eval gate: CI fails if a future change to the rule-based clause
classifier or deontic tagger regresses accuracy against the gold set
(app/eval/gold_set.py). This is the lightweight, always-on version of
docs/v2/ARCHITECTURE.md's "no prompt/model change merges without passing the
eval suite at or above the current baseline" -- scoped to what's real today
(a hand-curated gold set, not the full Ragas+CUAD harness).

Raise these thresholds as the gold set/rules improve; never lower them to
make a regression pass.
"""
from app.eval.run_eval import run_eval

MIN_CLAUSE_TYPE_ACCURACY = 1.0
MIN_DEONTIC_RECALL = 1.0
MIN_SENSITIVITY_ACCURACY = 0.9


def test_clause_type_accuracy_meets_baseline():
    result = run_eval()
    assert result.clause_type_accuracy >= MIN_CLAUSE_TYPE_ACCURACY, (
        f"Clause type accuracy {result.clause_type_accuracy:.1%} dropped below "
        f"baseline {MIN_CLAUSE_TYPE_ACCURACY:.1%}"
    )


def test_deontic_recall_meets_baseline():
    result = run_eval()
    assert result.deontic_recall >= MIN_DEONTIC_RECALL, (
        f"Deontic tag recall {result.deontic_recall:.1%} dropped below baseline {MIN_DEONTIC_RECALL:.1%}"
    )


def test_sensitivity_classifier_meets_baseline():
    from app.eval.gold_set import SENSITIVITY_GOLD
    from app.services.sensitivity import classify_sensitivity

    correct = sum(classify_sensitivity(ex["text"]).tier == ex["expected_tier"] for ex in SENSITIVITY_GOLD)
    accuracy = correct / len(SENSITIVITY_GOLD)
    assert accuracy >= MIN_SENSITIVITY_ACCURACY, (
        f"Sensitivity classifier accuracy {accuracy:.1%} ({correct}/{len(SENSITIVITY_GOLD)}) "
        f"dropped below baseline {MIN_SENSITIVITY_ACCURACY:.1%}"
    )
