# `backend/training/` — fine-tuning scaffold (Phase 6/8)

Scripts and configs for the in-house token-classification models
(`docs/v2/DEEP_LEARNING.md`, `docs/v2/MODEL_STACK.md`):

| target | base model | task | status |
|---|---|---|---|
| clause / contract-type classifier | `answerdotai/ModernBERT-base` (or `nlpaueb/legal-bert-base-uncased`) | sequence classification | **pipeline verified end-to-end (`--dry-run` + `--smoke`), full fine-tune GPU-blocked** (`LEARNING_LOG.md` #46) |
| deontic modality tagger | same | multi-label sequence classification | **pipeline verified end-to-end (`--dry-run` + `--smoke`), full fine-tune GPU-blocked** (`LEARNING_LOG.md` #46) |
| document sensitivity classifier | TF-IDF + LogisticRegression (scikit-learn, CPU) | 4-class sequence classification | **trained and eval-gated — did not beat the rule baseline, not promoted** (`models/sensitivity_classifier_card.md`, `LEARNING_LOG.md` #43) |
| risk scoring model | TF-IDF + LightGBM (CPU) | 3-class severity classification (low/medium/high) | **trained and eval-gated — did not beat the weak-supervision heuristic, not promoted** (`models/risk_model_card.md`, `LEARNING_LOG.md` #45) |

Every row above has now actually been *run*, not just scaffolded — the
distinction that matters is what each run could actually complete.
The sensitivity classifier and risk model are classical (CPU-seconds)
models, so they trained and eval-gated for real, start to finish. The
clause/deontic heads are BERT-scale fine-tunes: `--dry-run` (data/label
validation) and `--smoke` (2 real optimizer steps against a downloaded
`answerdotai/ModernBERT-base` checkpoint, loss genuinely decreasing) both
now run clean on CPU in this environment — this surfaced and fixed a real
bug (see below) — but a full multi-epoch fine-tune to a genuinely
promotable model is a multi-hour CPU job with `torch.cuda.is_available()`
confirmed `False` here, not merely assumed unavailable; the A4000 in
"Hardware" below is this project's intended path for that step, not
provisioned in this execution environment. The rule-based classifiers
(`app/services/nlp/clause_classifier.py`, `deontic.py`,
`app/services/sensitivity/classifier.py`, `app/services/risk_radar/rules.py`)
stay the Tier-0 pre-filter and the production path until a trained model
**beats them on the eval gate** (`app/eval/`), which no attempt has yet.

**A real bug fixed while running the smoke tests for the first time**: both
scripts' `LoraConfig(...)` call had no `target_modules`, which the
installed `peft` version (0.20.0) no longer auto-infers for
`ModernBertForSequenceClassification` — `get_peft_model()` raised
`ValueError: Please specify 'target_modules' or 'target_parameters' in
'peft_config'` before a single training step could run, on **both**
scripts, unconditionally. Fixed by passing
`target_modules=cfg.get("lora_target_modules", "all-linear")` — peft's
architecture-agnostic wildcard, which also stays correct if `base_model`
is switched to `nlpaueb/legal-bert-base-uncased` (a different module
naming scheme) via the yaml config's existing comment. This bug would have
blocked the very first fine-tuning attempt on this stack regardless of
whether it ran on this CPU box or the intended A4000 — a real,
previously-undiscovered defect in code that had never actually been
executed before now.

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
     - --legalbench : adds real contract_nli_* contract text (LegalBench)
       as additional sentences for the rule teacher -- grows the corpus from
       ~15 hand-picked seed sentences to 389 real ones (331/58 train/val)

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

## Curate training data (Phase 8, docs/v2/ROADMAP.md "org corpora with consent + CUAD/ContractNLI")

The CUAD/ContractNLI half is real and already wired in: `prepare_clause_data.py`
pulls LegalBench's `cuad_*` subtasks (real, externally-sourced contract
clauses, not synthetic) for clause-type weak labels; `prepare_deontic_data.py
--legalbench` (added `LEARNING_LOG.md` #47) pulls `contract_nli_*` contract
text the same way for deontic weak labels — using `app/eval/datasets.py`'s
`load_contractnli_subtasks()`, which existed since Phase 6 but had never
actually been called by anything until now. **"Org corpora with consent" is
genuinely blocked**, not skipped: this product has no real paying
organizations yet, so there is no real customer contract corpus to curate
and no consent flow to build it around — a product-stage blocker, not an
infrastructure one, and one no amount of additional engineering in this
repo can manufacture around.

## Legal-expert review in Argilla (Phase 8, verified live)

```bash
docker compose -f training/argilla-compose.yml up -d
python training/push_to_argilla.py       # -> real Argilla dataset, rule-teacher suggestions pre-filled
# UI: http://localhost:6900  (login: argilla / 12345678)
docker compose -f training/argilla-compose.yml down -v   # when done
```

`push_to_argilla.py` pushes weak-labelled deontic examples into an Argilla
dataset (`modalities` multi-label question, one `Suggestion` per record
from the existing rule teacher) so a reviewer confirms/corrects instead of
labelling from scratch. Verified live end-to-end (`LEARNING_LOG.md` #48):
20 records pushed to a real, locally-run Argilla v2 server, read back with
suggestions and metadata intact. Two real infra gaps found only by
actually running it, not by reading docs: the commonly-documented
single-container `argilla/argilla-quickstart` image serves a stale,
API-incompatible v1.29.1 server (the current `argilla` Python client is a
full v2 rewrite); the real v2 server (`argilla/argilla-server`) additionally
needs a Redis connection for its webhook/task queue even single-node,
which isn't obvious from Argilla's own docs but is a hard startup failure
without it — `argilla-compose.yml` is the verified-working three-container
setup (server + Elasticsearch + Redis). **What stays genuinely blocked**:
no legal expert exists in this environment to open the UI and actually
adjudicate a suggestion — a human-availability gap, unrelated to whether
the infrastructure itself works (it does).

## Legal Clause Embedding Model — hard-negative pair construction (CPU-only, already run)

```bash
python training/prepare_embedding_data.py   # -> data/embedding_pairs.jsonl
```

The CPU half of `docs/v2/ROADMAP.md`'s "Legal Clause Embedding Model —
contrastive fine-tune (`NOVELTY.md` #3) with hard-negative mining"; the
actual contrastive fine-tune step needs a GPU (Phase 6 infra), same as the
clause/deontic heads. Builds 122 verified (anchor, positive,
hard_negative) triplets: positives are different real clauses sharing a
clause_type label (from the already-prepared `clause_{train,val}.jsonl`);
hard negatives are regex perturbations matching NOVELTY.md's own named
examples (modal-verb swap "shall"/"may", negation, a day-count/dollar/
percentage shift) — each is **verified**, not assumed, before being kept:
modal_swap/negation are confirmed by the *existing* rule-based deontic
tagger actually flipping its tag; numeric_shift is scoped to only
magnitude/threshold numbers (day/month/year counts, `$` amounts,
percentages), after an early, broader version was caught corrupting
statute-year and section-number citations (e.g. "Lanham Act of 1946" →
"...of 194") into garbage rather than a legally-meaningful hard negative.
See `LEARNING_LOG.md` #49.

## Deontic-Structure-Aware Counterfactual Ablation (`NOVELTY.md` #5, CPU-only, already run)

```bash
python training/deontic_ablation.py [--n 5]   # -> models/deontic_ablation_report.json
```

Explains a Risk Scoring Model prediction by perturbing one legally-
meaningful span at a time (a deontic modal marker, an extracted entity, a
defined term — all reused from the *existing* NLP pipeline's own output,
no new parser) and measuring the shift in predicted-class probability.
Run against the not-promoted `risk_model.joblib` (#45) — deliberately: this
validates the *ablation technique*, not the model. Found that removing the
actual deontic marker barely moves this model's predictions on the real
gold set (near-zero deltas), independently corroborating
`risk_model_card.md`'s own SHAP-based finding that the model learned
superficial n-grams, not legal structure — while a separately-constructed
richer example confirmed all three span types (`deontic_marker`, `entity:*`,
`defined_term`) work correctly end to end. Full result in
`models/deontic_ablation_notes.md` and `LEARNING_LOG.md` #54.

## Temporal Trigger Simulation (`NOVELTY.md` #2, CPU-only, already run)

```bash
python training/temporal_trigger_simulation.py   # 5/5 hand-modelled scenarios pass
```

`app/services/simulation.py`'s shipped baseline only schedules clauses
with an *absolute* resolved date. This prototype does the piece its own
docstring names as the real gap: extracts "N days/months/years after/of/
following <trigger phrase>" patterns (a genuinely new regex target, not a
re-run of `temporal.py`'s absolute-date extraction) and, given a small
hand-provided dict of known anchor-event dates, derives the downstream
date. Deliberately single-document scope with hand-provided anchors, not
the full portfolio `TRIGGERED_BY`-graph vision — that needs
`Obligation`/`TRIGGERED_BY` KG nodes that don't exist yet, the same
structural blocker `simulation.py`'s own docstring already names. Validated
against 5 hand-modelled scenarios (expected dates computed by hand, not by
running the code) — all pass, including a negative case (no matching
anchor → honestly skipped, not guessed). See `LEARNING_LOG.md` #55.

## Redline Attribution (`NOVELTY.md` #4, CPU-only, already run)

```bash
python training/redline_attribution.py [--dry-run]   # -> models/redline_attribution_report.json
```

The CPU half of `NOVELTY.md` idea #4 ("Adaptive Negotiation Playbook
Learning from Redline History"): **counterfactual fingerprint-delta
attribution** — given a redline (`before` → `after`), a word-level diff is
split into atomic legal changes (modal swap / negation / numeric shift /
jurisdiction swap / other reword), and each change's contribution to the
"legal-semantic fingerprint" movement is measured by reconstructing the
counterfactual "`after`, but with every op of that kind reverted" and
embedding it. Plus a **background distribution** (each kind's marginal
delta as a percentile across all observed proposed edits) and a classical
**Redline Acceptance Predictor** (LogisticRegression over the per-kind
marginal-delta features).

**Two blockers, both named plainly**: (1) no redline history exists
anywhere in this codebase (`LEARNING_LOG.md` #51's audit) — the
`(before, after, outcome)` data is synthetic (`gold_set.py` clauses,
NOVELTY.md-named perturbations both directions, outcome label *generated*
from a hand-specified prior, same #43/#45 ceiling); (2) idea #4's
fingerprint is idea #3's contrastive embedding, GPU-blocked (#49) — this
uses the Model Router's current `embed_content` (Class-A hashing here) as
the stand-in.

**Results**: all 4 single-change attribution scenarios pass (the change is
known by construction), the no-change case correctly produces no
attribution, and the boilerplate-reword scenario is a documented soft fail
(on the hashing floor the reword dominates the legal change — exactly why
idea #4 needs idea #3's fingerprint). The **acceptance predictor does NOT
beat its majority baseline** (0.514 vs 0.514) — a precise negative result:
unsigned fingerprint-delta *magnitude* can't encode edit *direction*
(`shall→may` accepted, `may→shall` rejected, same `|delta|`), which needs
the *signed* delta in idea #3's learned subspace. Full write-up:
`models/redline_attribution_notes.md`, `LEARNING_LOG.md` #57.

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
