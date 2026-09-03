# `backend/training/` — fine-tuning scaffold (Phase 6/8)

Scripts and configs for the in-house token-classification models
(`docs/v2/DEEP_LEARNING.md`, `docs/v2/MODEL_STACK.md`):

| target | base model | task | status |
|---|---|---|---|
| clause / contract-type classifier | `answerdotai/ModernBERT-base` (or `nlpaueb/legal-bert-base-uncased`) | sequence classification | **scaffold only — not trained** |
| deontic modality tagger | same | multi-label sequence classification | **scaffold only — not trained** |

**Nothing here has been run.** This session (Phase 6) delivered the pipeline —
data prep, config-driven training, eval hooks — so the training runs are a
`python training/train_*.py training/configs/*.yaml` away, not a from-scratch
build. The rule-based classifiers (`app/services/nlp/clause_classifier.py`,
`deontic.py`) stay the Tier-0 pre-filter and the production path until a
trained model **beats them on the eval gate** (`app/eval/`).

## Hardware

The dev box (1× RTX A4000, 16 GB) fits all of this comfortably:
- Full fine-tune of a BERT-base (~110 M params): ~3 GB, minutes per epoch.
- QLoRA of a small LLM (≤ 8 B) for the deontic *teacher*: ~10 GB with `unsloth`.

## Pipeline

```
1. prepare_clause_data.py   -> data/clause_{train,val}.jsonl
     - LegalBench cuad_* subtasks (clause-presence -> weak clause-type labels)
     - app/eval/gold_set.py GOLD_SET (hand labels)
     - weak supervision: classify_clause_type_rule_based() over an unlabeled
       contract corpus (pass --weak-corpus path/to/*.txt)

2. prepare_deontic_data.py  -> data/deontic_{train,val}.jsonl
     - weak supervision: tag_deontic_modality_rule_based() over a sentence
       corpus (the teacher step; an LLM teacher via the Model Router is the
       Phase 6 upgrade -- see docs/v2/MODEL_STACK.md "Weak-supervision teacher")

3. train_clause_classifier.py training/configs/clause_classifier.yaml
   train_deontic_tagger.py   training/configs/deontic_tagger.yaml
     - HF Trainer + PEFT LoRA, eval each epoch, early stop on macro-F1
     - --dry-run : load + validate data, print class balance, exit
     - --smoke   : 2 optimizer steps, prove the loop runs

4. Promotion (manual, eval-gated):
     - run app/eval/tasks.py against the trained head vs the rule baseline
     - only if it beats the baseline: register in the routing policy as the
       primary for clause_type / deontic, rule base demoted to pre-filter
     - write a model card from model_card_template.md
```

## Install

```
pip install -r backend/requirements-train.txt
# optional 2x-faster / lower-VRAM LoRA:
pip install unsloth
```
