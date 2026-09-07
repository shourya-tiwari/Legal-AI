# backend/training/prepare_sensitivity_data.py
"""
Build a weak-supervision training set for the classical (TF-IDF + linear)
Document Sensitivity Classifier (docs/v2/ROADMAP.md Phase 8 "Document
Sensitivity Classifier — classical first").

No real customer documents exist to train on (the honest reason this line
was previously unbuilt, not "blocked on infra"). Same shape as
prepare_clause_data.py's `--weak-corpus` step: source real (not fabricated)
legal-domain text already committed in this repo -- GOLD_SET/RISK_GOLD/
TIMELINE_GOLD clause examples, the RAG corpus's legal-knowledge entries --
combine 1-3 of them into a synthetic "document," sometimes injecting a real
trigger phrase drawn from the rule-based classifier's own regex patterns,
and weak-label the result with the existing rule-based
`classify_sensitivity()` -- distilling the rules into a model that can
learn to generalize past exact phrase matches, the identical "weak
supervision via the rule-based classifier" methodology
prepare_clause_data.py already established for clause typing.

`app/eval/gold_set.py::SENSITIVITY_GOLD` (11 hand-labelled, real examples)
is deliberately NEVER used here -- it's held out entirely for
train_sensitivity_classifier.py's evaluation, so the one genuinely
human-labelled signal available never leaks into training.

Output: training/data/sensitivity_train.jsonl, sensitivity_val.jsonl
  {"text": "...", "label": "public|internal|confidential|privileged", "source": "weak"}

    python training/prepare_sensitivity_data.py [--n-documents 200] [--dry-run]
"""
from __future__ import annotations

import argparse
import random

from _common import DATA_DIR, class_balance, log, train_val_split, write_jsonl

# Real trigger phrases drawn directly from
# app/services/sensitivity/classifier.py's own regex patterns -- not
# invented for this script, so weak-labelling with classify_sensitivity()
# against text containing them is exercising the same signal the production
# rules already use, not a different one.
_PRIVILEGE_PHRASES = [
    "This memorandum is protected by the attorney-client privilege.",
    "PRIVILEGED AND CONFIDENTIAL work product prepared in anticipation of litigation.",
    "This communication is subject to the attorney-client privilege.",
]
_CONFIDENTIAL_PHRASES = [
    "This information is strictly confidential and constitutes a trade secret.",
    "The parties acknowledge this Agreement contains Confidential Information.",
    "Employee record on file: SSN 123-45-6789.",
]
_PUBLIC_PHRASES = [
    "FOR IMMEDIATE RELEASE. The Company announces its quarterly results, filed on Form 8-K.",
    "This filing is available to the general public via the SEC's EDGAR system.",
]


def _real_text_snippets() -> list[str]:
    """Every real (hand-written-for-this-repo, not fabricated for this
    script) clause/document text already committed elsewhere in the eval
    harness and the RAG corpus."""
    from app.eval.gold_set import GOLD_SET, RISK_GOLD, TIMELINE_GOLD
    from app.services.rag.corpus import LEGAL_KNOWLEDGE_BASE

    snippets = [ex["text"] for ex in GOLD_SET]
    snippets += [ex["text"] for ex in RISK_GOLD]
    snippets += [ex.get("text", "") for ex in TIMELINE_GOLD if ex.get("text")]
    snippets += [entry.text for entry in LEGAL_KNOWLEDGE_BASE]
    return [s for s in snippets if s]


def build_synthetic_documents(n_documents: int, seed: int = 13) -> list[dict]:
    from app.services.sensitivity.classifier import classify_sensitivity

    rng = random.Random(seed)
    base_snippets = _real_text_snippets()
    trigger_phrases = _PRIVILEGE_PHRASES + _CONFIDENTIAL_PHRASES + _PUBLIC_PHRASES

    rows: list[dict] = []
    for _ in range(n_documents):
        n_snippets = rng.randint(1, 3)
        parts = [rng.choice(base_snippets) for _ in range(n_snippets)]
        # ~40% of documents get a real trigger phrase inserted at a random
        # position -- the rest stay plain contract boilerplate (the "internal"
        # default case, since classify_sensitivity() defaults there).
        if rng.random() < 0.4:
            parts.insert(rng.randint(0, len(parts)), rng.choice(trigger_phrases))
        text = "\n\n".join(parts)
        assessment = classify_sensitivity(text)
        rows.append({"text": text, "label": assessment.tier, "source": "weak"})
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-documents", type=int, default=200)
    ap.add_argument("--seed", type=int, default=13)
    ap.add_argument("--dry-run", action="store_true", help="print stats, don't write files")
    args = ap.parse_args()

    rows = build_synthetic_documents(args.n_documents, seed=args.seed)
    log.info("built %d weak-labelled synthetic documents", len(rows))
    log.info("class balance: %s", class_balance(rows, "label"))

    if args.dry_run:
        log.info("--dry-run: no files written")
        return
    train, val = train_val_split(rows)
    write_jsonl(train, DATA_DIR / "sensitivity_train.jsonl")
    write_jsonl(val, DATA_DIR / "sensitivity_val.jsonl")


if __name__ == "__main__":
    main()
