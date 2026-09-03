# backend/training/prepare_deontic_data.py
"""
Build the deontic-modality tagger training set by weak supervision (Phase 6/8,
docs/v2/MODEL_STACK.md "Weak-supervision teacher").

Teacher (this scaffold): the rule-based tagger
`tag_deontic_modality_rule_based()` over a sentence corpus. Multi-label:
a sentence can be {obligation, permission, prohibition, discretion} or none.

The Phase 6 upgrade is to swap the teacher for a self-hosted LLM via the
Model Router (`task="deontic_escalation"`) and keep only high-agreement
labels -- distil-then-serve. The student stays a fast CPU BERT head.

Output: training/data/deontic_{train,val}.jsonl
  {"text": "...", "labels": ["obligation"], "source": "rule_teacher"}

    python training/prepare_deontic_data.py [--corpus DIR] [--llm-teacher] [--dry-run]
"""
from __future__ import annotations

import argparse
import glob
from pathlib import Path

from _common import DATA_DIR, class_balance, log, train_val_split, write_jsonl

_MODALITIES = ["obligation", "permission", "prohibition", "discretion"]


def _seed_sentences() -> list[str]:
    """Fallback corpus when --corpus isn't given: the gold set + a handful of
    representative clauses, enough to smoke the pipeline."""
    from app.eval.gold_set import GOLD_SET

    return [ex["text"] for ex in GOLD_SET] + [
        "The Supplier shall deliver the Goods no later than the Delivery Date.",
        "The Licensee may sublicense the Software to its Affiliates.",
        "Neither party shall disclose the terms of this Agreement to any third party.",
        "The Board may, in its sole discretion, declare a dividend.",
        "This Section describes the parties' respective addresses for notices.",
    ]


def _rule_labels(text: str) -> list[str]:
    from app.services.nlp.deontic import tag_deontic_modality_rule_based

    return sorted({t.modality for t in tag_deontic_modality_rule_based(text)})


def _llm_labels(text: str) -> list[str]:
    """Optional stronger teacher -- a self-hosted LLM via the Model Router.
    Only used with --llm-teacher; keeps a label only if the rule tagger and
    the LLM agree on it (high-precision distillation)."""
    from app.services.model_router import generate_content

    prompt = (
        "List the deontic modalities present in this contract sentence, from "
        "{obligation, permission, prohibition, discretion}. Reply with a comma-"
        f"separated list or 'none'.\n\nSentence: {text}\nModalities:"
    )
    try:
        raw = generate_content(prompt, task="deontic_escalation", sensitivity="public",
                               temperature=0.0, max_output_tokens=20)
    except Exception as e:  # noqa: BLE001
        log.warning("LLM teacher unavailable (%s); rule labels only", e)
        return _rule_labels(text)
    llm = {m for m in _MODALITIES if m in raw.lower()}
    return sorted(set(_rule_labels(text)) & llm) if llm else _rule_labels(text)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", help="directory of *.txt contracts")
    ap.add_argument("--llm-teacher", action="store_true",
                    help="intersect rule labels with a self-hosted LLM's (needs LLM_BASE_URL)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if args.corpus:
        from app.services.nlp.segmentation import split_sentences

        sentences: list[str] = []
        for path in glob.glob(str(Path(args.corpus) / "**" / "*.txt"), recursive=True):
            sentences += split_sentences(Path(path).read_text(encoding="utf-8", errors="ignore"))
    else:
        sentences = _seed_sentences()

    label_fn = _llm_labels if args.llm_teacher else _rule_labels
    rows = [
        {"text": s[:1000], "labels": label_fn(s),
         "source": "llm_distil" if args.llm_teacher else "rule_teacher"}
        for s in sentences if s.strip()
    ]

    log.info("collected %d weakly-labelled sentences", len(rows))
    log.info("modality balance: %s", class_balance(rows, "labels"))

    if args.dry_run:
        log.info("--dry-run: no files written")
        return
    train, val = train_val_split(rows)
    write_jsonl(train, DATA_DIR / "deontic_train.jsonl")
    write_jsonl(val, DATA_DIR / "deontic_val.jsonl")


if __name__ == "__main__":
    main()
