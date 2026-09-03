# backend/training/prepare_clause_data.py
"""
Build the clause-type classification training set (Phase 6/8).

Sources, in decreasing label confidence:
  1. app/eval/gold_set.py GOLD_SET      -- hand labels (gold)
  2. LegalBench cuad_* subtasks         -- a "Yes" answer for `cuad_governing_law`
     on a clause is a weak signal that the clause IS a governing-law clause
  3. --weak-corpus *.txt                -- classify_clause_type_rule_based() over
     unlabeled contract text (weak supervision; low confidence, high volume)

Output: training/data/clause_train.jsonl, clause_val.jsonl
  {"text": "...", "label": "governing_law", "source": "gold|legalbench|weak"}

    python training/prepare_clause_data.py [--limit-per 60] [--weak-corpus DIR] [--dry-run]
"""
from __future__ import annotations

import argparse
import glob
from pathlib import Path

from _common import DATA_DIR, class_balance, log, train_val_split, write_jsonl

# LegalBench cuad_<x> subtask -> our clause_type label
_LEGALBENCH_TO_LABEL = {
    "cuad_governing_law": "governing_law",
    "cuad_anti-assignment": "assignment",
    "cuad_cap_on_liability": "limitation_of_liability",
    "cuad_uncapped_liability": "limitation_of_liability",
    "cuad_termination_for_convenience": "termination",
    "cuad_non-compete": "non_compete",
    "cuad_exclusivity": "exclusivity",
    "cuad_audit_rights": "audit_rights",
}


def from_gold() -> list[dict]:
    from app.eval.gold_set import GOLD_SET

    return [
        {"text": ex["text"], "label": ex["expected_clause_type"], "source": "gold"}
        for ex in GOLD_SET
        if ex["expected_clause_type"] != "other"
    ]


def from_legalbench(limit_per: int) -> list[dict]:
    from app.eval.datasets import load_legalbench

    rows: list[dict] = []
    for subtask, label in _LEGALBENCH_TO_LABEL.items():
        try:
            for e in load_legalbench(subtask, split="test", limit=limit_per):
                if e["answer"].strip().lower() == "yes":
                    rows.append({"text": e["input"][:2000], "label": label, "source": "legalbench"})
        except Exception as exc:  # a missing subtask shouldn't kill prep
            log.warning("legalbench/%s skipped (%s)", subtask, exc)
    return rows


def from_weak_corpus(corpus_dir: str) -> list[dict]:
    from app.services.nlp.clause_classifier import classify_clause_type_rule_based
    from app.services.nlp.segmentation import segment_into_clauses

    rows: list[dict] = []
    for path in glob.glob(str(Path(corpus_dir) / "**" / "*.txt"), recursive=True):
        text = Path(path).read_text(encoding="utf-8", errors="ignore")
        for clause in segment_into_clauses(text):
            label = classify_clause_type_rule_based(clause)
            if label:
                rows.append({"text": clause[:2000], "label": label, "source": "weak"})
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit-per", type=int, default=60)
    ap.add_argument("--weak-corpus", help="directory of *.txt contracts for weak supervision")
    ap.add_argument("--dry-run", action="store_true", help="print stats, don't write files")
    args = ap.parse_args()

    rows = from_gold() + from_legalbench(args.limit_per)
    if args.weak_corpus:
        rows += from_weak_corpus(args.weak_corpus)

    log.info("collected %d labelled clauses", len(rows))
    log.info("class balance: %s", class_balance(rows, "label"))
    log.info("by source: %s", class_balance(rows, "source"))

    if args.dry_run:
        log.info("--dry-run: no files written")
        return
    train, val = train_val_split(rows)
    write_jsonl(train, DATA_DIR / "clause_train.jsonl")
    write_jsonl(val, DATA_DIR / "clause_val.jsonl")


if __name__ == "__main__":
    main()
