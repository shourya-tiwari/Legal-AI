# `backend/training/` — fine-tuning scaffold (Phase 6/8)

Scripts and configs for the in-house token-classification models
(`docs/v2/DEEP_LEARNING.md`, `docs/v2/MODEL_STACK.md`):

| target | base model | task | status |
|---|---|---|---|
| clause / contract-type classifier | `answerdotai/ModernBERT-base` (or `nlpaueb/legal-bert-base-uncased`) | sequence classification | **scaffold only — not trained** |
| deontic modality tagger | same | multi-label sequence classification | **scaffold only — not trained** |
| document sensitivity classifier | TF-IDF + LogisticRegression (scikit-learn, CPU) | 4-class sequence classification | **trained and eval-gated — did not beat the rule baseline, not promoted** (`models/sensitivity_classifier_card.md`, `LEARNING_LOG.md` #43) |

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

## Document sensitivity classifier (CPU-only, already run)

Unlike the two BERT-based scaffolds above, this one needed nothing this
environment lacked — no GPU, no served LLM. `scikit-learn` was already in
`requirements-train.txt`.

```
python training/prepare_sensitivity_data.py       # -> data/sensitivity_{train,val}.jsonl
python training/train_sensitivity_classifier.py   # trains, evaluates, saves
```

No real customer documents exist, so training data is synthetic: real
clause snippets already committed elsewhere in this repo, weak-labelled by
running the *existing* rule classifier over them (the same distillation
approach `prepare_clause_data.py`'s `--weak-corpus` step already uses).
Evaluated against `app/eval/gold_set.py::SENSITIVITY_GOLD` (11 real,
hand-labelled examples, held out of training) — the classical model scored
0.818 there against the rule baseline's 1.000. **Did not pass the gate**;
the rule base stays production. See `models/sensitivity_classifier_card.md`
for the full result and failure analysis, and `LEARNING_LOG.md` #43. The
honest next step this roadmap line names ("fine-tune a transformer only if
classical underperforms") is real, GPU-blocked follow-up work, not skipped
by choice.

## MLflow registry + DVC data versioning (Phase 8, genuinely local — no server)

Both tools run entirely on the local filesystem; neither needed
infrastructure this environment lacks.

**MLflow** (`training/train_sensitivity_classifier.py`) logs every training
run — params (vectorizer config, model type, split sizes), metrics
(`weak_val_accuracy`, `weak_val_macro_f1`, `classical_model_gold_accuracy`,
`rule_baseline_gold_accuracy`, `passed_cutover_gate`), and artifacts (the
eval JSON, the model card) — to a local sqlite-backed store
(`training/mlruns.db` + `training/mlruns/`, both gitignored; sqlite because
MLflow's plain filesystem store is maintenance-mode as of the installed
version). Browse runs with:

```bash
mlflow ui --backend-store-uri sqlite:///training/mlruns.db
```

Skips silently (falls back to just the script's own stdout log line) if
`mlflow` isn't installed — it's a queryable history layered on top of the
eval-gate result, not a dependency of it. This is the pattern every future
trained model in this directory should follow, not something specific to
sensitivity classification.

**DVC** versions the actual data/model blobs `git` deliberately excludes
(`backend/training/data/`, `backend/training/models/*.joblib`) — `git`
keeps the small pointer files (`*.dvc`, content-hash + size), DVC's local
remote (`../dvc-storage` from `.dvc/config`, i.e. `<repo-root>/dvc-storage/`,
gitignored) holds the actual bytes, so a fresh clone can `dvc pull` and get
back the exact training data/model that produced a given eval result,
without either bloating git history with binary blobs or leaving the
result unreproducible.

```bash
dvc pull                                    # from repo root, after a fresh clone
python training/prepare_sensitivity_data.py # or: regenerate from scratch (both work; same seed=13)
dvc add backend/training/data backend/training/models/sensitivity_classifier.joblib
dvc push                                    # after any regeneration that changes the hash
```

**Eval-gated promotion in CI/CD**: not built — there's no CI workflow that
runs `train_sensitivity_classifier.py` and blocks a merge on
`passed_cutover_gate`, matching `app/eval/cutover_gate.py`'s existing
manual-invocation pattern for Model Router tasks (`.github/workflows/
backend-tests.yml` runs `pytest`, not the training scripts). Wiring a
training run into CI is real, buildable follow-up work — not infra-blocked,
just not yet done — tracked as a separate `TASKS.md` line rather than
silently folded into this one.
