# backend/training/train_risk_model.py
"""
Train + eval-gate the classical (TF-IDF + LightGBM) Risk Scoring Model
(docs/v2/ROADMAP.md Phase 8 "Train the Risk Scoring Model (LightGBM,
CPU -- blocked on labelled data, not hardware); integrate SHAP"). CPU-only,
no GPU/Model-Router dependency -- LightGBM is a gradient-boosted-tree
library, not a neural model, so this needed nothing this environment
lacked, exactly like train_sensitivity_classifier.py.

Eval-gated the same way: trained on the *weak*-labelled synthetic corpus
(prepare_risk_data.py, weak-labelled by a keyword-flag-count heuristic
built on top of the existing, production `risk_radar/rules.py`), then
scored against app/eval/gold_set.py::RISK_SEVERITY_GOLD -- 14 hand-labelled,
real examples judged directly against risk conventions (not against the
heuristic), held out of training entirely -- and compared against that
same heuristic's own accuracy on the identical set. **Only reports whether
it would pass, does not wire anything in itself** -- no code path in
app/services/risk_radar/ calls this model; promotion stays a manual,
reviewed step.

SHAP (TreeExplainer, exact for gradient-boosted trees): after training,
explains a handful of gold predictions by their top contributing TF-IDF
tokens, written into the eval report -- the roadmap's "integrate SHAP"
line, in service of the one thing SHAP is actually for here: making a
severity prediction inspectable, not a black box.

    python training/train_risk_model.py [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import os

os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "1")

from _common import DATA_DIR, log, read_jsonl

MLFLOW_DB = DATA_DIR.parent / "mlruns.db"
MLFLOW_ARTIFACTS_DIR = DATA_DIR.parent / "mlruns"

_LABELS = ["low", "medium", "high"]
_LABEL_TO_ID = {label: i for i, label in enumerate(_LABELS)}


def _load_split(name: str) -> tuple[list[str], list[str]]:
    rows = read_jsonl(DATA_DIR / name)
    return [r["text"] for r in rows], [r["label"] for r in rows]


def _shap_top_tokens(explainer, X_row, feature_names, predicted_class_id: int, top_n: int = 3) -> list[str]:
    """Top-N TF-IDF tokens (by |SHAP value|) pushing this row toward its
    predicted class. Returns [] if shap isn't installed or explanation fails
    -- SHAP is diagnostic sugar on top of the eval-gate result, never a
    dependency of it (same posture as the mlflow-optional pattern below)."""
    try:
        shap_values = explainer.shap_values(X_row.toarray())
        # New-style shap returns one array shaped (n_samples, n_features, n_classes);
        # older API returns a list of per-class arrays. Handle both.
        if isinstance(shap_values, list):
            row_values = shap_values[predicted_class_id][0]
        else:
            row_values = shap_values[0, :, predicted_class_id]
        nonzero = [(feature_names[i], v) for i, v in enumerate(row_values) if v != 0]
        nonzero.sort(key=lambda t: abs(t[1]), reverse=True)
        return [f"{tok} ({val:+.3f})" for tok, val in nonzero[:top_n]]
    except Exception as exc:  # pragma: no cover -- diagnostic path only
        log.warning("shap explanation skipped: %s", exc)
        return []


def train_and_evaluate(dry_run: bool = False) -> dict:
    from lightgbm import LGBMClassifier
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics import accuracy_score, f1_score

    from app.eval.gold_set import RISK_SEVERITY_GOLD
    from training.prepare_risk_data import severity_from_flag_count
    from app.services.risk_radar.rules import RISKY_TERMS, find_keyword_flags

    X_train, y_train = _load_split("risk_train.jsonl")
    X_val, y_val = _load_split("risk_val.jsonl")
    log.info("train=%d val=%d", len(X_train), len(X_val))

    vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=1, max_features=3000)
    X_train_vec = vectorizer.fit_transform(X_train)
    X_val_vec = vectorizer.transform(X_val)

    y_train_ids = [_LABEL_TO_ID[y] for y in y_train]
    y_val_ids = [_LABEL_TO_ID[y] for y in y_val]

    clf = LGBMClassifier(
        objective="multiclass",
        num_class=len(_LABELS),
        class_weight="balanced",
        n_estimators=200,
        max_depth=4,
        random_state=13,
        verbosity=-1,
    )
    clf.fit(X_train_vec, y_train_ids)

    val_pred_ids = clf.predict(X_val_vec)
    val_accuracy = accuracy_score(y_val_ids, val_pred_ids)
    val_macro_f1 = f1_score(y_val_ids, val_pred_ids, average="macro", zero_division=0)
    log.info("weak-labelled val split: accuracy=%.3f macro_f1=%.3f", val_accuracy, val_macro_f1)

    # The real evaluation: 14 hand-labelled examples, judged against real
    # risk conventions, never seen in training.
    gold_texts = [ex["text"] for ex in RISK_SEVERITY_GOLD]
    gold_expected = [ex["expected_severity"] for ex in RISK_SEVERITY_GOLD]
    gold_vec = vectorizer.transform(gold_texts)
    model_pred_ids = clf.predict(gold_vec)
    model_pred = [_LABELS[i] for i in model_pred_ids]
    model_accuracy = accuracy_score(gold_expected, model_pred)

    heuristic_pred = [
        severity_from_flag_count(len(find_keyword_flags(t, RISKY_TERMS))) for t in gold_texts
    ]
    heuristic_accuracy = accuracy_score(gold_expected, heuristic_pred)

    passed = model_accuracy >= heuristic_accuracy

    # SHAP: explain the model's own predictions on the first few gold
    # examples, purely diagnostic -- doesn't affect passed/failed.
    shap_explanations: list[dict] = []
    try:
        import shap

        explainer = shap.TreeExplainer(clf)
        feature_names = vectorizer.get_feature_names_out()
        for i in range(min(3, len(gold_texts))):
            top_tokens = _shap_top_tokens(explainer, gold_vec[i], feature_names, int(model_pred_ids[i]))
            shap_explanations.append({
                "text": gold_texts[i][:80],
                "predicted": model_pred[i],
                "top_contributing_tokens": top_tokens,
            })
    except ImportError:
        log.info("shap not installed -- skipping model-explanation step (eval-gate result is unaffected)")

    result = {
        "weak_val_accuracy": round(val_accuracy, 3),
        "weak_val_macro_f1": round(val_macro_f1, 3),
        "gold_n": len(RISK_SEVERITY_GOLD),
        "classical_model_gold_accuracy": round(model_accuracy, 3),
        "heuristic_baseline_gold_accuracy": round(heuristic_accuracy, 3),
        "passed_cutover_gate": passed,
        "gold_predictions": [
            {"text": t[:80], "expected": e, "classical": m, "heuristic": h}
            for t, e, m, h in zip(gold_texts, gold_expected, model_pred, heuristic_pred)
        ],
        "shap_explanations": shap_explanations,
    }

    log.info("classical model on RISK_SEVERITY_GOLD: %.3f  |  heuristic baseline: %.3f  |  %s",
             model_accuracy, heuristic_accuracy,
             "PASS (classical >= heuristic)" if passed else "FAIL (heuristic stays the weak-supervision source, not promoted as a classifier)")

    eval_path = None
    if not dry_run:
        import joblib

        model_path = DATA_DIR.parent / "models"
        model_path.mkdir(exist_ok=True)
        joblib.dump({"vectorizer": vectorizer, "classifier": clf, "labels": _LABELS},
                    model_path / "risk_model.joblib")
        eval_path = model_path / "risk_model_eval.json"
        with open(eval_path, "w", encoding="utf-8") as fh:
            json.dump(result, fh, indent=2)
        log.info("saved model + eval report -> %s", model_path)

    try:
        import mlflow
    except ImportError:
        log.info("mlflow not installed -- skipping run tracking (eval-gate result above is unaffected)")
        return result

    mlflow.set_tracking_uri(f"sqlite:///{MLFLOW_DB.resolve().as_posix()}")
    experiment_name = "risk-scoring-model"
    if mlflow.get_experiment_by_name(experiment_name) is None:
        mlflow.create_experiment(
            experiment_name,
            artifact_location=f"file:///{MLFLOW_ARTIFACTS_DIR.resolve().as_posix()}",
        )
    mlflow.set_experiment(experiment_name)
    with mlflow.start_run(run_name="dry-run" if dry_run else None):
        mlflow.log_params({
            "vectorizer": "tfidf",
            "ngram_range": "(1, 2)",
            "max_features": 3000,
            "classifier": "lightgbm",
            "n_estimators": 200,
            "max_depth": 4,
            "class_weight": "balanced",
            "n_train": len(X_train),
            "n_val": len(X_val),
            "gold_n": result["gold_n"],
            "dry_run": dry_run,
        })
        mlflow.log_metrics({
            "weak_val_accuracy": result["weak_val_accuracy"],
            "weak_val_macro_f1": result["weak_val_macro_f1"],
            "classical_model_gold_accuracy": result["classical_model_gold_accuracy"],
            "heuristic_baseline_gold_accuracy": result["heuristic_baseline_gold_accuracy"],
            "passed_cutover_gate": float(passed),
        })
        if eval_path is not None:
            mlflow.log_artifact(str(eval_path))
        card_path = DATA_DIR.parent / "models" / "risk_model_card.md"
        if card_path.exists():
            mlflow.log_artifact(str(card_path))
        log.info("logged run to mlflow (sqlite:///%s, experiment=risk-scoring-model)", MLFLOW_DB.resolve().as_posix())

    return result


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="train + evaluate, don't save the model")
    args = ap.parse_args()
    train_and_evaluate(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
