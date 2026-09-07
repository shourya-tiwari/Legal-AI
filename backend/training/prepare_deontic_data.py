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

    python training/prepare_deontic_data.py [--corpus DIR] [--legalbench] [--llm-teacher] [--dry-run]

`--legalbench` (Phase 8, docs/v2/ROADMAP.md "Curate training data ... +
CUAD/ContractNLI"): pulls real contract text from LegalBench's
`contract_nli_*` subtasks (`app/eval/datasets.py::load_contractnli_subtasks`
-- previously defined but never actually called anywhere in this repo) as
additional sentences for the rule teacher to tag. Not using ContractNLI's
own Yes/No entailment *labels* here -- those answer "is X true of this
NDA" questions that don't map onto deontic modality without inventing a
forced correspondence; what's genuinely useful from ContractNLI for THIS
task is its underlying real (not synthetic) contract text as more sentence
volume for the existing rule-based teacher to tag, the same role `_corpus`
already plays, just sourced from a real external benchmark instead of a
hand-picked local directory.
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


def _llm_labels(text: str, *, sensitivity: str) -> list[str]:
    """Optional stronger teacher -- a self-hosted LLM via the Model Router,
    with the Model Router's existing sensitivity gate deciding whether an
    external (Class C) fallback is even reachable for this text. Only used
    with --llm-teacher; keeps a label only if the rule tagger and the LLM
    agree on it (high-precision distillation).

    `sensitivity` is NOT hardcoded to "public" -- doing that unconditionally
    was a real bug (LEARNING_LOG.md #47): with no self-hosted endpoint
    configured (`LLM_BASE_URL` unset), the Model Router's policy chain for
    `deontic_escalation` falls through to Gemini (Class C) for any
    public/internal-tier text, so a hardcoded "public" would have let
    --corpus'd real (possibly confidential) local contract files reach an
    external API under a false sensitivity tag -- the exact failure mode
    the sensitivity-tiering system exists to prevent. Callers must classify
    their own text's real tier (see main()'s per-source handling below)."""
    from app.services.model_router import generate_content

    prompt = (
        "List the deontic modalities present in this contract sentence, from "
        "{obligation, permission, prohibition, discretion}. Reply with a comma-"
        f"separated list or 'none'.\n\nSentence: {text}\nModalities:"
    )
    try:
        raw = generate_content(prompt, task="deontic_escalation", sensitivity=sensitivity,
                               temperature=0.0, max_output_tokens=20)
    except Exception as e:  # noqa: BLE001
        log.warning("LLM teacher unavailable (%s); rule labels only", e)
        return _rule_labels(text)
    llm = {m for m in _MODALITIES if m in raw.lower()}
    return sorted(set(_rule_labels(text)) & llm) if llm else _rule_labels(text)


def _legalbench_sentences(limit_per: int = 40) -> list[str]:
    """Real contract text from LegalBench's contract_nli_* subtasks, split
    into sentences for the rule teacher -- see module docstring for why
    only the text (not the entailment labels) is used here."""
    from app.eval.datasets import load_contractnli_subtasks
    from app.services.nlp.segmentation import split_sentences

    sentences: list[str] = []
    for ex in load_contractnli_subtasks(limit_per=limit_per):
        sentences += split_sentences(ex["input"])
    return sentences


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", help="directory of *.txt contracts")
    ap.add_argument("--legalbench", action="store_true",
                    help="add real contract_nli_* contract text (needs requirements-eval.txt)")
    ap.add_argument("--llm-teacher", action="store_true",
                    help="intersect rule labels with a self-hosted LLM's (needs LLM_BASE_URL)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    # (text, sensitivity) pairs -- sensitivity travels with each sentence so
    # --llm-teacher never has to guess (or worse, assume "public") what tier
    # a piece of text actually belongs to.
    sentences: list[tuple[str, str]] = []

    if args.corpus:
        from app.services.nlp.segmentation import split_sentences
        from app.services.sensitivity import classify_sensitivity

        for path in glob.glob(str(Path(args.corpus) / "**" / "*.txt"), recursive=True):
            text = Path(path).read_text(encoding="utf-8", errors="ignore")
            # Real, arbitrary local files -- classify each one for real
            # rather than assuming a tier, the same on-the-fly classification
            # V1 routes already do for uploaded contract text.
            tier = classify_sensitivity(text).tier
            sentences += [(s, tier) for s in split_sentences(text)]
    else:
        # The hand-picked seed set + GOLD_SET are genuinely public
        # (hand-authored for this repo's own eval harness), not an assumption.
        sentences += [(s, "public") for s in _seed_sentences()]

    if args.legalbench:
        try:
            # LegalBench is a public benchmark dataset -- "public" here is
            # actually true, unlike the old hardcoded default for ALL text.
            sentences += [(s, "public") for s in _legalbench_sentences()]
        except RuntimeError as exc:  # `datasets` not installed
            log.warning("--legalbench requested but unavailable (%s); continuing without it", exc)

    rows = [
        {
            "text": s[:1000],
            "labels": _llm_labels(s, sensitivity=tier) if args.llm_teacher else _rule_labels(s),
            "source": "llm_distil" if args.llm_teacher else "rule_teacher",
        }
        for s, tier in sentences if s.strip()
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
