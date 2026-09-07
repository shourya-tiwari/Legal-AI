# backend/training/train_sensitivity_classifier.py
"""
Train + eval-gate the classical (TF-IDF + LogisticRegression) Document
Sensitivity Classifier (docs/v2/ROADMAP.md Phase 8 "Document Sensitivity
Classifier — classical first"). CPU-only, no GPU/Model-Router dependency,
runs in seconds -- unlike backend/train_clause_classifier.py's BERT fine-
tune, this needed nothing this environment lacked.

Eval-gated exactly like app/eval/cutover_gate.py's philosophy, just without
that module's Model-Router plumbing (sensitivity classification is a plain
function call, not a routed task): trained on the *weak*-labelled synthetic
corpus (prepare_sensitivity_data.py), then scored against
app/eval/gold_set.py::SENSITIVITY_GOLD -- the 11 hand-labelled, real
examples, held out of training entirely -- and compared against the
existing rule-based classifier's own score on the identical set. **Only
reports whether it would pass, does not wire anything in itself** — that
stays a manual, reviewed promotion step (this script's own README section),
the same "never a false PASS, never an automatic cutover" discipline
app/eval/cutover_gate.py already established for Model Router tasks.

    python training/train_sensitivity_classifier.py [--dry-run]
"""
from __future__ import annotations

import argparse
import json

from _common import DATA_DIR, log, read_jsonl


def _load_split(name: str) -> tuple[list[str], list[str]]:
    rows = read_jsonl(DATA_DIR / name)
    return [r["text"] for r in rows], [r["label"] for r in rows]


def train_and_evaluate(dry_run: bool = False) -> dict:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import accuracy_score, f1_score
    from sklearn.pipeline import Pipeline

    from app.eval.gold_set import SENSITIVITY_GOLD
    from app.services.sensitivity.classifier import classify_sensitivity

    X_train, y_train = _load_split("sensitivity_train.jsonl")
    X_val, y_val = _load_split("sensitivity_val.jsonl")
    log.info("train=%d val=%d", len(X_train), len(X_val))

    pipeline = Pipeline([
        ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=1, max_features=5000)),
        ("clf", LogisticRegression(max_iter=1000, class_weight="balanced")),
    ])
    pipeline.fit(X_train, y_train)

    val_pred = pipeline.predict(X_val)
    val_accuracy = accuracy_score(y_val, val_pred)
    val_macro_f1 = f1_score(y_val, val_pred, average="macro", zero_division=0)
    log.info("weak-labelled val split: accuracy=%.3f macro_f1=%.3f", val_accuracy, val_macro_f1)

    # The real evaluation: the 11 hand-labelled examples, never seen in training.
    gold_texts = [ex["text"] for ex in SENSITIVITY_GOLD]
    gold_expected = [ex["expected_tier"] for ex in SENSITIVITY_GOLD]
    model_pred = pipeline.predict(gold_texts)
    model_accuracy = accuracy_score(gold_expected, model_pred)

    rule_pred = [classify_sensitivity(t).tier for t in gold_texts]
    rule_accuracy = accuracy_score(gold_expected, rule_pred)

    passed = model_accuracy >= rule_accuracy
    result = {
        "weak_val_accuracy": round(val_accuracy, 3),
        "weak_val_macro_f1": round(val_macro_f1, 3),
        "gold_n": len(SENSITIVITY_GOLD),
        "classical_model_gold_accuracy": round(model_accuracy, 3),
        "rule_baseline_gold_accuracy": round(rule_accuracy, 3),
        "passed_cutover_gate": passed,
        "gold_predictions": [
            {"text": t[:80], "expected": e, "classical": m, "rule": r}
            for t, e, m, r in zip(gold_texts, gold_expected, model_pred, rule_pred)
        ],
    }

    log.info("classical model on SENSITIVITY_GOLD: %.3f  |  rule baseline: %.3f  |  %s",
             model_accuracy, rule_accuracy,
             "PASS (classical >= rule)" if passed else "FAIL (rule baseline stays production)")

    if not dry_run:
        import joblib

        model_path = DATA_DIR.parent / "models"
        model_path.mkdir(exist_ok=True)
        joblib.dump(pipeline, model_path / "sensitivity_classifier.joblib")
        with open(model_path / "sensitivity_classifier_eval.json", "w", encoding="utf-8") as fh:
            json.dump(result, fh, indent=2)
        log.info("saved model + eval report -> %s", model_path)

    return result


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="train + evaluate, don't save the model")
    args = ap.parse_args()
    train_and_evaluate(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
