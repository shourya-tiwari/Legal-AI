# Model card: <model name>

_Fill in when a trained model is promoted (docs/v2/MODEL_STACK.md "model cards
for every trained model"). Until then this is a template._

## Overview
- **Task:** <clause-type classification | deontic modality tagging | ...>
- **Base model:** <answerdotai/ModernBERT-base | nlpaueb/legal-bert-base-uncased>
- **Adapter:** <full fine-tune | LoRA r=..., alpha=...>
- **Version / commit:** <git sha>  **Date:** <yyyy-mm-dd>
- **Replaces / augments:** <app/services/nlp/clause_classifier.py rule base as Tier-0 pre-filter>

## Intended use
- <e.g. classify a segmented contract clause into one of N types, behind the
  keyword rule base which stays the fast pre-filter>
- **Out of scope:** <jurisdictions / contract types not represented in training data>

## Training data
- **Sources:** gold set (n=), LegalBench cuad_* (n=), weak supervision (n=, teacher=)
- **Provenance / consent:** <...>
- **Label process:** <rule teacher | LLM teacher via Model Router | human review in Argilla>
- **Splits:** train / val (seed 13, 15% val)

## Evaluation
| metric | this model | rule baseline | delta |
|---|---:|---:|---:|
| accuracy | | | |
| macro-F1 | | | |

- **Eval harness:** `python -m app.eval.tasks <task>`
- **Promotion gate:** must beat the rule baseline on macro-F1; `eval_runs` row id <...>

## Limitations & risks
- <class imbalance, weak-label noise, domain shift, calibration>
- Not a substitute for legal review.

## Maintenance
- **Owner:** <team>  **Retrain trigger:** <drift monitor threshold, new corpus>
