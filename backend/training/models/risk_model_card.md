# Model card: Risk Scoring Model (classical, TF-IDF + LightGBM)

**NOT PROMOTED.** Trained and eval-gated for real (`LEARNING_LOG.md` #45); did not
beat the keyword-count heuristic it was distilled from on the hand-labelled gold
set, so `app/services/risk_radar/` stays fully rule/LLM-based (keyword flags +
the Model Router's `risk_analysis` task) with no severity-score model in the
loop. Kept here as a real, honest record of the attempt — this is docs/v2/
ROADMAP.md Phase 8's "Train the Risk Scoring Model (LightGBM, CPU)" line,
tried and reported, not skipped.

## Overview
- **Task:** per-clause risk-severity classification (`low` | `medium` | `high`)
- **Model:** `TfidfVectorizer(ngram_range=(1,2), max_features=3000)` → `LGBMClassifier(class_weight="balanced", n_estimators=200, max_depth=4)`, LightGBM (CPU, gradient-boosted trees — not a neural model, needs nothing this environment lacked)
- **Training script:** `training/train_risk_model.py`
- **Would replace/augment:** nothing currently in production — there is no severity-score model or field anywhere in `app/services/risk_radar/`; this would have been genuinely new capability, not a replacement, had it passed

## Intended use (had it passed)
- A per-clause severity score (low/medium/high) to sit alongside the existing keyword flags and AI risk pass, e.g. for a future Risk Dashboard chart (`docs/v2/TASKS.md`'s still-unbuilt "Risk Dashboard spider/radar chart" line) that needs a numeric/categorical axis, not just a flag count.
- **Out of scope even if promoted:** no real customer documents or real human-adjudicated severity labels were used anywhere in this pipeline (see Training data) — a promoted model would still need re-validation against real-world documents and real reviewer judgments before being trusted in production.

## Training data
- **No real per-clause severity labels exist to train on** — this codebase has never computed or stored a severity score anywhere; the closest existing signal is `risk_radar/rules.py`'s `RISKY_TERMS` keyword-flag list (55 terms, already production, used by the live `/api/risk/scan` endpoint) and the count of flags a clause triggers.
- **Sources:** 250 synthetic clauses (`training/prepare_risk_data.py`), each built by combining 1–2 real (not fabricated) clause snippets already committed in this repo (`app/eval/gold_set.py`'s `GOLD_SET`/`RISK_GOLD`/`TIMELINE_GOLD`, `app/services/rag/corpus.py`'s `LEGAL_KNOWLEDGE_BASE`) — the identical source pool `prepare_sensitivity_data.py` already draws from.
- **Label process:** weak supervision via a **newly-invented-for-this-script** heuristic (`severity_from_flag_count`), NOT an existing production classifier — bucket the existing `find_keyword_flags()` count: 0 → `low`, 1–2 → `medium`, ≥3 → `high`. This differs from the sensitivity classifier's precedent (which distilled an already-trusted production rule, `classify_sensitivity()`) in one important way: there is no existing "this is how severity works" rule in this codebase to distill, so the heuristic itself is unvalidated scaffolding, not a trusted signal being generalized past.
- **Splits:** 213 train / 37 val (seed 13, 15% val), both weak-labelled, from `training/data/risk_{train,val}.jsonl`. Class balance is uneven (`medium`≈144, `low`≈85, `high`≈21 before splitting) — a real property of the source clause pool, not corrected by oversampling, though `class_weight="balanced"` compensates during training.
- **Held out entirely from training:** `app/eval/gold_set.py::RISK_SEVERITY_GOLD` (14 hand-labelled, real examples) — severity judged directly against real contract-risk conventions (uncapped liability, one-sided rights, harsh restrictive covenants = high; vague/subjective or capped mutual terms = medium; routine boilerplate = low), deliberately **not** derived from the keyword-count heuristic, so this evaluation is a real test of whether the trained model generalizes past both the heuristic and its own training distribution — not a tautology.

## Evaluation

| metric | this model | keyword-count heuristic | delta |
|---|---:|---:|---:|
| accuracy on weak-labelled val split (n=37) | 0.892 | — (n/a, the heuristic generated these labels) | — |
| **accuracy on `RISK_SEVERITY_GOLD` (n=14, real, held out)** | **0.500** | **0.571** | **−0.071** |

**Result: FAIL.** The classical model did not meet or beat the heuristic baseline on
the real gold set — see `training/models/risk_model_eval.json` for the full
per-example breakdown and SHAP explanations. The clearest failure pattern:
every `high`-severity gold example involving a **one-sided or open-ended
right** ("may unilaterally amend... without notifying", "non-compete...
anywhere in the world for ten years") was scored `low` or `medium` by both
the model and the heuristic — because none of those specific phrases appear
in `RISKY_TERMS`' 55-term keyword list at all. This is not a model-training
failure; it is the weak-supervision heuristic's own ceiling showing through
exactly where `LEARNING_LOG.md` #43 predicted it would ("weak supervision
... cannot, by construction, teach the model anything the rules don't
already know") — except here the "rules" are a heuristic invented for this
script, not an already-validated production classifier, so the ceiling is
lower and hit sooner. SHAP's top contributing tokens for these misses
(`"terms"`, `"any"`, `"shall"` — generic contract boilerplate words, not the
substantive one-sided-right language) confirm the model latched onto
superficial n-grams correlated with the heuristic's keyword hits, not the
underlying legal-risk concept.

## Honest limitations
- **The weak-supervision source itself is unvalidated** (unlike the sensitivity classifier's, which distilled an existing, already-trusted production rule) — a bigger risk factor here than model capacity or training-data volume.
- Class imbalance in the weak-labelled corpus (`high` is the rarest class, both in training and reflecting that most everyday contract language isn't extreme) means the model has the least practice on exactly the class the gold set weights most heavily toward being interesting.
- 14 examples is a very small gold set; the result here is directionally honest (classical underperformed) but not a statistically robust estimate of the true accuracy gap.
- The `.joblib` artifact is not committed to git (gitignored, DVC-tracked instead) — reproducible via `python training/prepare_risk_data.py && python training/train_risk_model.py` and isn't loaded by any production code path, since it wasn't promoted.

## Next step
Before any further model attempt on this line, the weak-supervision source needs
fixing, not the model architecture: expand `RISKY_TERMS` (or design a genuinely
better severity heuristic — e.g. weighting one-sided/absolute-language markers
like "unilaterally", "sole discretion", "without notice", "anywhere in the
world" more heavily than a flat keyword count) so the training labels
actually encode the concept the gold set is testing for. A real fix needs
either an expert-reviewed rule set (the still-unbuilt "Legal-expert review
of weak labels in Argilla" line) or actual labelled data — both correctly
tracked as separate, still-open roadmap lines, not silently assumed solved
by this attempt.

## Maintenance
- **Owner:** n/a (not promoted, no production consumer)
- **Retrain trigger:** n/a — retraining without first fixing the weak-supervision heuristic (see Next step) would likely reproduce the same ceiling
