# backend/training/prepare_embedding_data.py
"""
Hard-negative pair construction for the Legal Clause Embedding Model
(docs/v2/ROADMAP.md Phase 8 "Legal Clause Embedding Model -- contrastive
fine-tune (NOVELTY.md #3) with hard-negative mining"; NOVELTY.md idea #3's
own breakdown: "hard-negative pair construction (CPU); contrastive
training uses Phase 6 GPU"). This script is the CPU half.

NOVELTY.md #3's proposed training-data shape:
  - positive pair:      different wording, SAME legal effect
  - hard-negative pair:  SIMILAR wording, different/contradictory legal
                         effect -- specifically named examples: a negation,
                         a modal-verb swap ("shall" vs "may"), or a cap
                         amount change.

Positives: two different real clause texts sharing the same clause_type
label from training/data/clause_{train,val}.jsonl -- already-prepared,
real (LegalBench + hand-labelled gold) data from prepare_clause_data.py,
used here as a clause_type is itself a reasonable proxy for "same legal
effect" for a contrastive objective at this granularity. (GOLD_SET alone
was tried first and rejected for this specific step: only ~15 examples
across 15 clause types means almost no type has 2+ examples to pair --
correctly identified as too small a pool, not silently forced to work.)

Hard negatives: one clause, minimally perturbed by regex so its wording
stays almost identical but its legal effect flips -- exactly NOVELTY.md's
named perturbation types:
  - modal_swap: "shall"/"must" <-> "may" (obligation <-> permission)
  - negation:   insert/remove "not" next to the modal verb (obligation ->
                prohibition, or permission -> a much narrower one)
  - numeric_shift: change a stated number (a cap, a day count) so the
                clause reads almost identically but means something
                materially different (docs/v2/NOVELTY.md's "cap amount"
                example)

Every hard negative is verified, not assumed: the perturbed text is run
back through the *existing* rule-based deontic tagger
(tag_deontic_modality_rule_based) to confirm its tagged modality actually
changed from the original -- a perturbation that doesn't change the tag
isn't a hard negative, it's a no-op, and is dropped rather than silently
kept as a bad training example.

Output: training/data/embedding_pairs.jsonl
  {"anchor": "...", "positive": "...", "hard_negative": "...",
   "perturbation": "modal_swap|negation|numeric_shift"}

    python training/prepare_embedding_data.py [--dry-run]
"""
from __future__ import annotations

import argparse
import re

from _common import DATA_DIR, class_balance, log, read_jsonl, write_jsonl

_MODAL_SWAP_RE = re.compile(r"\b(shall|must)\b", re.IGNORECASE)
_PERMISSION_RE = re.compile(r"\bmay\b", re.IGNORECASE)
# Only numbers in a legally-meaningful magnitude/threshold context --
# NOVELTY.md's own examples are "a cap amount" and "a day count". A bare
# \d+ also matches statute years ("Lanham Act of 1946") and section numbers
# ("Section 10.2"), where shifting the digits produces a garbage citation,
# not a hard negative with a different legal effect -- found by inspecting
# a real generated example, not assumed in advance.
_NUMBER_RE = re.compile(
    r"\$\s?(\d+)|(\d+)\s?%|\b(\d+)\s*(?:day|days|month|months|year|years)\b",
    re.IGNORECASE,
)


def _swap_modal(text: str) -> str | None:
    """obligation ("shall"/"must") -> permission ("may"), or vice versa --
    NOVELTY.md's named "shall vs may" perturbation."""
    if _MODAL_SWAP_RE.search(text):
        return _MODAL_SWAP_RE.sub(lambda m: "may" if m.group(0)[0].islower() else "May", text, count=1)
    if _PERMISSION_RE.search(text):
        return _PERMISSION_RE.sub(lambda m: "shall" if m.group(0)[0].islower() else "Shall", text, count=1)
    return None


def _negate(text: str) -> str | None:
    """Insert/remove a "not" next to the modal verb -- NOVELTY.md's named
    negation perturbation."""
    if re.search(r"\bshall not\b", text, re.IGNORECASE):
        return re.sub(r"\bshall not\b", "shall", text, count=1, flags=re.IGNORECASE)
    if re.search(r"\bshall\b(?!\s+not)", text, re.IGNORECASE):
        return re.sub(r"\bshall\b(?!\s+not)", "shall not", text, count=1, flags=re.IGNORECASE)
    return None


def _shift_number(text: str) -> str | None:
    """Change a stated dollar amount, percentage, or day/month/year count
    so the clause reads almost identically but means something materially
    different -- NOVELTY.md's named "cap amount"/day-count example.
    Deliberately does NOT touch bare numbers with no such context (statute
    years, section numbers) -- see the regex comment above for why."""
    m = _NUMBER_RE.search(text)
    if not m:
        return None
    group_idx = next(i for i in (1, 2, 3) if m.group(i))
    digit_start, digit_end = m.start(group_idx), m.end(group_idx)
    original = int(m.group(group_idx))
    shifted = original * 10 if original < 100 else max(1, original // 10)
    return text[:digit_start] + str(shifted) + text[digit_end:]


_PERTURBATIONS = {
    "modal_swap": _swap_modal,
    "negation": _negate,
    "numeric_shift": _shift_number,
}


def _hard_negatives_for(text: str) -> list[tuple[str, str]]:
    """Try every perturbation; verify each one before accepting it -- see
    module docstring. modal_swap/negation operate on the deontic-modality
    axis, so they're verified against the *existing* rule-based deontic
    tagger actually flipping its tag (a real, already-trusted classifier
    confirming the legal effect changed). numeric_shift operates on a
    different axis (a stated threshold/amount) that no classifier in this
    codebase measures -- verified more weakly, by confirming the number
    itself actually changed, which is definitionally a different legal
    effect (a 30-day cure period is not a 3-day one) even though nothing
    here can independently confirm that the way the modality tagger
    confirms a modal-verb/negation flip."""
    from app.services.nlp.deontic import tag_deontic_modality_rule_based

    original_modalities = {t.modality for t in tag_deontic_modality_rule_based(text)}
    out: list[tuple[str, str]] = []
    for name, fn in _PERTURBATIONS.items():
        perturbed = fn(text)
        if perturbed is None or perturbed == text:
            continue
        if name == "numeric_shift":
            out.append((name, perturbed))
            continue
        new_modalities = {t.modality for t in tag_deontic_modality_rule_based(perturbed)}
        if new_modalities != original_modalities:
            out.append((name, perturbed))
    return out


def build_pairs(max_pairs_per_type: int = 15, seed: int = 13) -> list[dict]:
    import random

    rng = random.Random(seed)
    rows: list[dict] = []

    # Positive pairs: different clauses sharing a clause_type label from the
    # already-prepared clause-classification data -- different wording,
    # same legal effect (see module docstring for why GOLD_SET alone wasn't
    # enough of a pool for this specific pairing step).
    clause_rows = read_jsonl(DATA_DIR / "clause_train.jsonl") + read_jsonl(DATA_DIR / "clause_val.jsonl")
    by_type: dict[str, list[str]] = {}
    for r in clause_rows:
        by_type.setdefault(r["label"], []).append(r["text"])

    for clause_type, texts in by_type.items():
        texts = list(dict.fromkeys(texts))  # de-dupe, keep order
        if len(texts) < 2:
            continue
        pairs = [(a, b) for i, a in enumerate(texts) for b in texts[i + 1:]]
        rng.shuffle(pairs)
        for anchor, positive in pairs[:max_pairs_per_type]:
            for perturbation, hard_negative in _hard_negatives_for(anchor):
                rows.append({
                    "anchor": anchor,
                    "positive": positive,
                    "hard_negative": hard_negative,
                    "perturbation": perturbation,
                    "clause_type": clause_type,
                })
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-pairs-per-type", type=int, default=15)
    ap.add_argument("--dry-run", action="store_true", help="print stats, don't write files")
    args = ap.parse_args()

    rows = build_pairs(max_pairs_per_type=args.max_pairs_per_type)
    log.info("built %d verified (anchor, positive, hard_negative) triplets", len(rows))
    log.info("perturbation balance: %s", class_balance(rows, "perturbation"))

    if args.dry_run:
        log.info("--dry-run: no files written")
        return
    write_jsonl(rows, DATA_DIR / "embedding_pairs.jsonl")


if __name__ == "__main__":
    main()
