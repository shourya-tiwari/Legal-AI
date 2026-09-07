# backend/training/prepare_risk_data.py
"""
Build a weak-supervision training set for the classical (TF-IDF + LightGBM)
Risk Scoring Model (docs/v2/ROADMAP.md Phase 8 "Train the Risk Scoring
Model (LightGBM, CPU -- blocked on labelled data, not hardware)").

No real customer documents (and no real per-clause risk-severity labels)
exist to train on -- the actual reason this line was previously unbuilt.
Same weak-supervision-from-an-existing-rule-tagger shape
prepare_sensitivity_data.py already established for sensitivity tiering:
source real (not fabricated) legal-domain clause text already committed in
this repo, and weak-label each one by a simple **keyword-flag-count
heuristic** built on top of the *existing*, already-production
`risk_radar/rules.py::find_keyword_flags` (the same 55-term risky-phrase
list the live `/api/risk/scan` endpoint already uses) -- bucketed
0 flags -> low, 1-2 -> medium, >=3 -> high.

This heuristic is NOT a production classifier anywhere in this app (unlike
`classify_sensitivity()`, which the sensitivity script distills) -- it's
invented here purely as a cheap, explainable way to bootstrap weak labels
from the one rule-based signal this codebase already has for "is this
clause risky." `app/eval/gold_set.py::RISK_SEVERITY_GOLD` (14 hand-labelled,
real examples, judged directly against risk conventions, NOT against this
heuristic) is deliberately NEVER used here -- held out entirely for
train_risk_model.py's evaluation, so the one genuinely human-judged signal
available never leaks into training, and comparing the trained model
against the heuristic's own accuracy on that gold set is a real test of
whether learning from text generalizes past a keyword count.

Output: training/data/risk_{train,val}.jsonl
  {"text": "...", "label": "low|medium|high", "n_flags": int, "source": "weak"}

    python training/prepare_risk_data.py [--n-documents 250] [--dry-run]
"""
from __future__ import annotations

import argparse
import random

from _common import DATA_DIR, class_balance, log, train_val_split, write_jsonl


def _real_clause_snippets() -> list[str]:
    """Every real (hand-written-for-this-repo) clause already committed
    elsewhere in the eval harness and the RAG corpus -- the same source
    pool prepare_sensitivity_data.py draws from."""
    from app.eval.gold_set import GOLD_SET, RISK_GOLD, TIMELINE_GOLD
    from app.services.rag.corpus import LEGAL_KNOWLEDGE_BASE

    snippets = [ex["text"] for ex in GOLD_SET]
    snippets += [ex["text"] for ex in RISK_GOLD]
    snippets += [ex.get("text", "") for ex in TIMELINE_GOLD if ex.get("text")]
    snippets += [entry.text for entry in LEGAL_KNOWLEDGE_BASE]
    return [s for s in snippets if s]


def severity_from_flag_count(n_flags: int) -> str:
    """The weak-supervision heuristic: bucket the existing keyword-flag
    count into a severity tier. Deliberately simple and fully explainable
    -- the point is a cheap distillation source, not a good classifier in
    its own right (see module docstring)."""
    if n_flags >= 3:
        return "high"
    if n_flags >= 1:
        return "medium"
    return "low"


def build_synthetic_clauses(n_documents: int, seed: int = 13) -> list[dict]:
    from app.services.risk_radar.rules import RISKY_TERMS, find_keyword_flags

    rng = random.Random(seed)
    base_snippets = _real_clause_snippets()

    rows: list[dict] = []
    for _ in range(n_documents):
        n_snippets = rng.randint(1, 2)
        parts = [rng.choice(base_snippets) for _ in range(n_snippets)]
        text = "\n\n".join(parts)
        n_flags = len(find_keyword_flags(text, RISKY_TERMS))
        rows.append({
            "text": text,
            "label": severity_from_flag_count(n_flags),
            "n_flags": n_flags,
            "source": "weak",
        })
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-documents", type=int, default=250)
    ap.add_argument("--seed", type=int, default=13)
    ap.add_argument("--dry-run", action="store_true", help="print stats, don't write files")
    args = ap.parse_args()

    rows = build_synthetic_clauses(args.n_documents, seed=args.seed)
    log.info("built %d weak-labelled synthetic clauses", len(rows))
    log.info("class balance: %s", class_balance(rows, "label"))

    if args.dry_run:
        log.info("--dry-run: no files written")
        return
    train, val = train_val_split(rows)
    write_jsonl(train, DATA_DIR / "risk_train.jsonl")
    write_jsonl(val, DATA_DIR / "risk_val.jsonl")


if __name__ == "__main__":
    main()
