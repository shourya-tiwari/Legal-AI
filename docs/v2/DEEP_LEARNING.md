# Deep Learning Pipeline

V1 has zero trained models of its own — every "AI" behavior is a prompt sent to a general-purpose hosted model. V2 introduces a small set of purpose-trained models where a general LLM is the wrong tool: tasks that need to be fast, cheap, run at Tier 0 (fully local/air-gapped), interpretable, or that benefit from learning directly from an organization's historical data.

## Training pipeline

```
1. Data curation      — org corpora (with consent) + public legal datasets (CUAD, ContractNLI)
2. Weak supervision   — frontier-LLM labeling of a seed set (Tier 2 model, used offline/batch — not a
                         per-request dependency, so this is an acceptable, bounded use of a commercial API)
3. Human review       — legal-expert spot-check and correction of weakly-labeled data
4. Distillation       — train small, fast, open-weight-base models to reproduce the reviewed labels
5. Fine-tuning        — LoRA/QLoRA fine-tunes of open-weight base models on the curated dataset
6. Evaluation gate    — must beat the current production model on the held-out gold set (ARCHITECTURE.md)
7. Registry & deploy  — versioned in MLflow (open source), promoted via CI/CD (ARCHITECTURE.md)
8. Active learning    — production low-confidence predictions routed to the human review queue,
                         feeding back into step 3
```

This weak-supervision-then-distill pattern is the specific mechanism by which V2 gets the benefit of a frontier model's labeling quality (step 2) without depending on that model in the production request path — production inference for these tasks runs entirely at Tier 0/1.

## Models trained in-house

| Model | Task | Base | Training signal | Notes |
|---|---|---|---|---|
| **Legal Clause Embedding Model** | Clause-level semantic + legal-function similarity for RAG and cross-document matching | Contrastive fine-tune of **BGE-M3** | Clause-equivalence pairs (paraphrases of the same legal effect, and near-miss negatives: similar wording, different effect) | Feeds `AI_STACK.md` retrieval and is the specific embedding objective behind `NOVELTY.md` #3 |
| **Risk Scoring Model** | Structured, interpretable risk score per clause | **LightGBM** (open source gradient boosting) over structured features (clause type, deontic tags, entity counts, embedding-derived features) | Historical risk labels (from V1's keyword rules as a bootstrap signal, refined by expert review) | Chosen over a black-box neural model specifically for **SHAP-based interpretability** — feeds `NOVELTY.md` #5's explanation method |
| **Clause/Contract Type Classifier** | Classify clause type and overall contract type | Fine-tuned small transformer (e.g., a DeBERTa-v3-base-scale open model) | CUAD labels + internal gold set | Replaces V1's flat risky-term list with a real taxonomy (`NLP.md`) |
| **Deontic Modality Tagger** | Sequence tagging: obligation/permission/prohibition/discretion spans | Distilled small BERT-family model | Weak-supervised from frontier LLM, human-reviewed | Production inference at Tier 0, no per-request LLM cost |
| **Redline Acceptance Predictor** | Predict whether a suggested edit matches an org's historical negotiation stance | Fine-tuned sequence classifier + structured features from redline history | An org's own historical accepted/rejected redlines (opt-in, org-scoped — never shared across orgs) | The learned core of `NOVELTY.md` #4's procedural memory |
| **Document Sensitivity Classifier** | Auto-suggest a sensitivity tier at ingestion | Fine-tuned text classifier | Labeled examples of Public/Internal/Confidential/Privileged documents | Assists, does not replace, the uploader's own tier confirmation (`ARCHITECTURE.md`) |

## Infrastructure

- **Experiment tracking**: MLflow (open source, self-hostable) for every training run's params, metrics, and artifacts.
- **Data versioning**: DVC (open source) so a model version is always traceable to an exact dataset snapshot — important for both reproducibility and for being able to answer "what data trained the model that produced this output" if ever challenged.
- **Compute**: on-demand GPU (spot/preemptible where the training job tolerates interruption) for fine-tuning runs; inference for trained models runs on the same GPU pool that serves the Tier 1 LLMs (`ARCHITECTURE.md`), or on CPU for the smaller taggers/classifiers where latency budgets allow.
- **Model registry**: every trained model is versioned, tagged with the eval score it achieved, and requires passing the eval gate (`ARCHITECTURE.md`) before promotion to production — no model is hot-swapped into the Model Router without going through this gate.

## Governance

- **Model cards** for every trained model: intended use, training data provenance, known limitations, eval scores, and — critically for legal-domain models — the specific jurisdictions/contract types the training data actually covers, so the system doesn't silently overgeneralize (e.g., a risk model trained mostly on US commercial leases should not be presented as equally reliable for another jurisdiction's employment contracts without evidence).
- **Bias/fairness checks**: for models touching entity recognition of parties/roles, evaluate for systematic disparities in extraction quality across naming conventions/languages present in the training data.
- **Org data isolation**: the Redline Acceptance Predictor and any other model trained on an org's own historical data is trained and served per-org (or per an explicit opt-in shared pool), never pooled across organizations without consent — this is a hard requirement, not a configuration default, given the confidentiality of negotiation history.
