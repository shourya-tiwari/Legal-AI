# Model card: Document Sensitivity Classifier (classical, TF-IDF + logistic regression)

**NOT PROMOTED.** Trained and eval-gated for real (`LEARNING_LOG.md` #43); did not
beat the existing rule-based classifier on the hand-labelled gold set, so
the rule base (`app/services/sensitivity/classifier.py`) remains production.
Kept here as a real, honest record of the attempt — this is docs/v2/
ROADMAP.md Phase 8's "Document Sensitivity Classifier — classical first"
line, tried and reported, not skipped.

## Overview
- **Task:** document-level sensitivity tier classification (`public` | `internal` | `confidential` | `privileged`)
- **Model:** `TfidfVectorizer(ngram_range=(1,2), max_features=5000)` → `LogisticRegression(class_weight="balanced")`, scikit-learn
- **Training script:** `training/train_sensitivity_classifier.py`
- **Would replace/augment:** `app/services/sensitivity/classifier.py`'s rule base — did not, see Evaluation below

## Intended use (had it passed)
- A learned alternative to the regex rule base, potentially generalizing past exact trigger-phrase matches.
- **Out of scope even if promoted:** no real customer documents were used anywhere in this pipeline (see Training data) — a promoted model would still need re-validation against real-world documents before being trusted in production.

## Training data
- **No real customer documents exist to train on.** This is the honest reason this line of the roadmap was previously unbuilt (not "blocked on infra" — the reason was missing data, correctly distinguished from an infrastructure blocker per `LEARNING_LOG.md` #38/#39's re-audit of what "blocked" actually means in this project's docs).
- **Sources:** 300 synthetic "documents" (`training/prepare_sensitivity_data.py`), each built by combining 1–3 real (not fabricated) clause snippets already committed in this repo (`app/eval/gold_set.py`'s `GOLD_SET`/`RISK_GOLD`/`TIMELINE_GOLD`, `app/services/rag/corpus.py`'s `LEGAL_KNOWLEDGE_BASE`), with a ~40% chance of a real trigger phrase (drawn from the rule classifier's own regex patterns) inserted.
- **Label process:** weak supervision — every synthetic document's label comes from running the *existing* rule-based `classify_sensitivity()` over it (the same "distill the rules into a model" methodology `training/prepare_clause_data.py` already established for clause typing, not a new technique invented for this model).
- **Splits:** 255 train / 45 val (seed 13, 15% val) — both weak-labelled, from `training/data/sensitivity_{train,val}.jsonl`.
- **Held out entirely from training:** `app/eval/gold_set.py::SENSITIVITY_GOLD` (11 hand-labelled, genuinely human-authored examples) — reserved purely for evaluation below, so the one real signal available never leaked into training.

## Evaluation

| metric | this model | rule baseline | delta |
|---|---:|---:|---:|
| accuracy on weak-labelled val split (n=45) | 0.911 | — (n/a, the rules generated these labels) | — |
| **accuracy on `SENSITIVITY_GOLD` (n=11, real, held out)** | **0.818** | **1.000** | **−0.182** |

**Result: FAIL.** The classical model did not meet or beat the rule baseline on the
real gold set — see `training/models/sensitivity_classifier_eval.json` for
the full per-example breakdown. Both misses were `confidential` documents
predicted as `internal`:
- `"Employee record: SSN 123-45-6789, ..."` — a bag-of-words/n-gram
  representation handles a specific numeric ID pattern (an SSN's exact
  digit-group shape) far worse than a purpose-built regex does; this is a
  structural limitation of TF-IDF for this signal, not a training-data
  quantity problem.
- `"MUTUAL NON-DISCLOSURE AGREEMENT. The parties will exchange Confidential
  Information."` — milder confidentiality language than the training
  corpus's `"strictly confidential"` / `"trade secret"` trigger phrases;
  the synthetic corpus's confidential examples didn't cover this register,
  so the model never learned it.

Both are legible, explainable failure modes, not a mysterious regression —
which is itself useful: a future transformer fine-tune (this roadmap
line's own "if classical underperforms" next step) would need training
data that specifically covers milder confidentiality phrasing and
structured-PII patterns, not just more of the same trigger-phrase style
this synthetic corpus used.

## Honest limitations
- Trained entirely on synthetic, rule-labelled data — no independent human review of any label (Argilla-based expert review, `docs/v2/TASKS.md`'s "Legal-expert review of weak labels" line, is separately not-yet-built for the same reason: no legal expert available in this environment to do it).
- 11 examples is a very small gold set to draw a strong conclusion from; the result here is directionally honest (classical underperformed) but not a statistically robust estimate of the true accuracy gap.
- The `.joblib` artifact is not committed to git (gitignored) — it's reproducible via `python training/prepare_sensitivity_data.py && python training/train_sensitivity_classifier.py` and isn't loaded by any production code path, since it wasn't promoted.

## Next step
A transformer fine-tune (`docs/v2/ROADMAP.md`'s own "fine-tune a transformer only if [classical] underperforms" — which it did) is the honest next step for this line, and it needs the same A4000 GPU time already named as the blocker for the clause/deontic heads in `backend/training/README.md` — genuinely blocked on hardware, not skipped by choice.
