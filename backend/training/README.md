# `backend/training/` — fine-tuning scaffold (Phase 6/8)

Scripts and configs for the in-house token-classification models
(`docs/v2/DEEP_LEARNING.md`, `docs/v2/MODEL_STACK.md`):

| target | base model | task | status |
|---|---|---|---|
| clause / contract-type classifier | `answerdotai/ModernBERT-base` (or `nlpaueb/legal-bert-base-uncased`) | sequence classification | **scaffold only — not trained** |
| deontic modality tagger | same | multi-label sequence classification | **scaffold only — not trained** |
| document sensitivity classifier | TF-IDF + LogisticRegression (scikit-learn, CPU) | 4-class sequence classification | **trained and eval-gated — did not beat the rule baseline, not promoted** (`models/sensitivity_classifier_card.md`, `LEARNING_LOG.md` #43) |
| risk scoring model | TF-IDF + LightGBM (CPU) | 3-class severity classification (low/medium/high) | **trained and eval-gated — did not beat the weak-supervision heuristic, not promoted** (`models/risk_model_card.md`, `LEARNING_LOG.md` #45) |

The clause/deontic heads above are the only ones still genuinely
**not run** (GPU-blocked). The sensitivity classifier and risk model *have*
been run — data prep, config-driven training, eval hooks all executed for
real — the rule-based classifiers (`app/services/nlp/clause_classifier.py`,
`deontic.py`, `app/services/sensitivity/classifier.py`,
`app/services/risk_radar/rules.py`) stay the Tier-0 pre-filter and the
production path until a trained model **beats them on the eval gate**
(`app/eval/`), which neither classical attempt has yet.

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

## Risk Scoring Model (CPU-only, already run)

```bash
python training/prepare_risk_data.py       # -> data/risk_{train,val}.jsonl
python training/train_risk_model.py        # trains, evaluates, saves, SHAP-explains
```

Same shape as the sensitivity classifier, one important difference: there is
no existing *production* risk-severity classifier to distill (unlike
`classify_sensitivity()`), so training labels come from a heuristic
(`severity_from_flag_count`) invented for this script on top of the
already-production `risk_radar/rules.py` keyword-flag list. Evaluated
against `app/eval/gold_set.py::RISK_SEVERITY_GOLD` (14 real, hand-labelled
examples, judged directly against risk conventions, held out of training)
— scored 0.500 there against the heuristic's own 0.571. **Did not pass the
gate**; `app/services/risk_radar/` stays fully rule/LLM-based, no severity
score in production. SHAP (`shap.TreeExplainer`, exact for gradient-boosted
trees) explains the top contributing TF-IDF tokens for a few gold
predictions, written into `models/risk_model_eval.json` — the roadmap's
"integrate SHAP" line, satisfied as a diagnostic layer regardless of
promotion outcome. See `models/risk_model_card.md` for the full result,
including the specific failure pattern (one-sided/open-ended-right clauses
scored too low because none of their language appears in the 55-term
keyword list the heuristic was built on) and `LEARNING_LOG.md` #45.

## Eval-gated promotion in CI/CD

**Not built** — there's no CI workflow that runs a training script (either
`train_sensitivity_classifier.py` or `train_risk_model.py`) and blocks a
merge on `passed_cutover_gate`, matching `app/eval/cutover_gate.py`'s
existing manual-invocation pattern for Model Router tasks
(`.github/workflows/backend-tests.yml` runs `pytest`, not the training
scripts). Wiring a training run into CI is real, buildable follow-up work —
not infra-blocked, just not yet done — tracked as a separate `TASKS.md`
line rather than silently folded into either model's entry.
