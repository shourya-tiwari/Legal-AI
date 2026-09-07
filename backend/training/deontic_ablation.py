# backend/training/deontic_ablation.py
"""
NOVELTY.md idea #5, "Explainable Risk Attribution via Deontic-Structure-
Aware Counterfactual Ablation" -- the CPU-only research-track prototype
step (docs/v2/TASKS.md: "Idea #5 ... CPU-only -- runs against the existing
LightGBM risk model"). Now concretely buildable: `train_risk_model.py`
(#45) produced a real, trained TF-IDF + LightGBM risk-severity classifier
to actually ablate against -- it wasn't promoted (didn't beat the
weak-supervision heuristic on the gold set), but the ablation *technique*
this prototypes is independent of whether the underlying model is
production-grade; it's being validated here, not the model.

The idea's own framing: generic text-SHAP ablates arbitrary tokens/n-grams,
which often don't align with anything a legal reviewer would find
meaningful. This instead perturbs one **legally meaningful sub-span** at a
time -- a deontic modal marker (`DeonticTag.trigger_phrase`, e.g. "shall
not"), an extracted entity (`EntityMention.text` -- a money amount, a
jurisdiction, a duration), or a defined term the clause uses -- using
spans the *existing* NLP pipeline (`app/services/nlp/`) already extracts,
not a new parser built for this. For each span, the clause with that span
removed is re-run through the trained model, and the shift in predicted-
class probability is the span's attributed risk contribution.

    python training/deontic_ablation.py [--n 5]
"""
from __future__ import annotations

import argparse
import json

from _common import DATA_DIR, log


def _spans_for_clause(clause) -> list[tuple[str, str]]:
    """(span_text, span_type) pairs from the clause's own already-extracted
    structure -- no new extraction logic, per the module's own point."""
    spans: list[tuple[str, str]] = []
    for tag in clause.deontic_tags:
        if tag.trigger_phrase:
            spans.append((tag.trigger_phrase, "deontic_marker"))
    for entity in clause.entities:
        if entity.text:
            spans.append((entity.text, f"entity:{entity.type}"))
    for term in clause.defined_terms_used:
        spans.append((term, "defined_term"))
    # De-duplicate while preserving order (a term can appear as both an
    # entity and a defined term use, e.g. a party name).
    seen: set[tuple[str, str]] = set()
    unique: list[tuple[str, str]] = []
    for span in spans:
        if span not in seen:
            seen.add(span)
            unique.append(span)
    return unique


def _ablate(text: str, span: str) -> str:
    """Remove the first occurrence of `span` from `text` -- single-instance
    removal, the standard ablation convention (removing every occurrence of
    a common word like a party name could gut the whole clause)."""
    idx = text.find(span)
    if idx == -1:
        return text
    return (text[:idx] + text[idx + len(span):]).strip()


def explain_risk_prediction(clause, vectorizer, classifier, labels: list[str]) -> dict:
    """Perturbs each legally-meaningful span in `clause` one at a time and
    measures the shift in the trained model's predicted-class probability
    -- the actual attribution this idea proposes."""
    original_vec = vectorizer.transform([clause.text])
    original_proba = classifier.predict_proba(original_vec)[0]
    predicted_idx = int(original_proba.argmax())
    predicted_class = labels[predicted_idx]
    original_p = float(original_proba[predicted_idx])

    attributions = []
    for span, span_type in _spans_for_clause(clause):
        perturbed_text = _ablate(clause.text, span)
        if perturbed_text == clause.text:
            continue  # span wasn't found verbatim (e.g. normalized differently) -- skip, don't fabricate
        perturbed_vec = vectorizer.transform([perturbed_text])
        perturbed_p = float(classifier.predict_proba(perturbed_vec)[0][predicted_idx])
        attributions.append({
            "span": span,
            "span_type": span_type,
            "delta": round(original_p - perturbed_p, 4),
        })

    attributions.sort(key=lambda a: abs(a["delta"]), reverse=True)
    return {
        "clause": clause.text,
        "predicted_class": predicted_class,
        "predicted_proba": round(original_p, 4),
        "span_attributions": attributions,
    }


def main() -> None:
    import joblib

    from app.eval.gold_set import RISK_SEVERITY_GOLD
    from app.services.nlp.pipeline import build_clause_objects

    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=5, help="how many RISK_SEVERITY_GOLD examples to explain")
    args = ap.parse_args()

    model_path = DATA_DIR.parent / "models" / "risk_model.joblib"
    if not model_path.exists():
        log.error(
            "%s not found -- run prepare_risk_data.py and train_risk_model.py first "
            "(see backend/training/README.md).", model_path,
        )
        return

    bundle = joblib.load(model_path)
    vectorizer, classifier, labels = bundle["vectorizer"], bundle["classifier"], bundle["labels"]

    reports = []
    for example in RISK_SEVERITY_GOLD[: args.n]:
        clause = build_clause_objects(example["text"])[0]
        report = explain_risk_prediction(clause, vectorizer, classifier, labels)
        report["expected_severity"] = example["expected_severity"]
        reports.append(report)
        log.info(
            "predicted=%s (p=%.2f, expected=%s): %s",
            report["predicted_class"], report["predicted_proba"], example["expected_severity"],
            report["clause"][:70],
        )
        for a in report["span_attributions"][:3]:
            log.info("  %+.4f  [%s]  %r", a["delta"], a["span_type"], a["span"])

    out_path = DATA_DIR.parent / "models" / "deontic_ablation_report.json"
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(reports, fh, indent=2)
    log.info("wrote %d ablation reports -> %s", len(reports), out_path)


if __name__ == "__main__":
    main()
