# Deep Learning Pipeline

V1 has zero trained models of its own — every "AI" behavior is a prompt sent to a general-purpose hosted model. V2 introduces a small set of purpose-trained models where a general LLM is the wrong tool: tasks that need to be fast, cheap, run at Class A (fully local, CPU, air-gapped), interpretable, or that benefit from learning directly from an organization's historical data.

## Training pipeline

```
1. Data curation      — org corpora (with consent) + public legal datasets (CUAD, ContractNLI, LegalBench)
2. Weak supervision   — a SELF-HOSTED teacher model (large Class B, e.g. Qwen3-235B-A22B via the Model
                         Router) labels a seed set, orchestrated with distilabel; runs offline/batch.
                         A commercial teacher is an OPTIONAL substitution for this step only — never
                         required, never in the production path, and absent in air-gapped builds.
3. Human review       — legal-expert spot-check and correction in Argilla
4. Distillation       — train small, fast, open-weight-base students to reproduce the reviewed labels
5. Fine-tuning        — LoRA/QLoRA/DoRA fine-tunes (Unsloth for low-VRAM, Axolotl at scale) via TRL
6. Evaluation gate    — must beat the current production model on the held-out gold set + LegalBench
                         tasks (ARCHITECTURE.md), housed in Inspect AI
7. Registry & deploy  — versioned in MLflow + DVC, packaged as a signed KitOps ModelKit, promoted via CI/CD
8. Active learning    — production low-confidence predictions routed to the human review queue,
                         feeding back into step 3
```

This weak-supervision-then-distill pattern gets big-model labelling quality into small, fast, **fully self-hosted** production models. The teacher is self-hosted by default — the pattern has **no commercial dependency at all** unless an operator explicitly opts a commercial model into step 2 for a one-off labelling batch. Production inference for these tasks runs entirely at Class A/B, on the organization's own hardware.

## Models trained in-house

| Model | Task | Base | Training signal | Notes |
|---|---|---|---|---|
| **Legal Clause Embedding Model** | Clause-level semantic + legal-function similarity for RAG and cross-document matching | Contrastive fine-tune of **BGE-M3** or **Qwen3-Embedding** | Clause-equivalence pairs (paraphrases of the same legal effect, and near-miss negatives: similar wording, different effect) | Feeds `AI_STACK.md` retrieval and is the specific embedding objective behind `NOVELTY.md` #3 |
| **Risk Scoring Model** | Structured, interpretable risk score per clause | **LightGBM** (open source gradient boosting) over structured features (clause type, deontic tags, entity counts, embedding-derived features) | Historical risk labels (from V1's keyword rules as a bootstrap signal, refined by expert review) | Chosen over a black-box neural model specifically for **SHAP-based interpretability** — feeds `NOVELTY.md` #5's explanation method |
| **Clause/Contract Type Classifier** | Classify clause type and overall contract type | Fine-tuned small transformer (**ModernBERT** / DeBERTa-v3 / Legal-BERT base) | CUAD labels + internal gold set | Replaces V1's flat risky-term list with a real taxonomy (`NLP.md`) |
| **Deontic Modality Tagger** | Sequence tagging: obligation/permission/prohibition/discretion spans | Distilled small BERT-family model | Weak-supervised from a self-hosted teacher, human-reviewed | Production inference at Class A (CPU), no per-request LLM cost |
| **Redline Acceptance Predictor** | Predict whether a suggested edit matches an org's historical negotiation stance | Fine-tuned sequence classifier + structured features from redline history | An org's own historical accepted/rejected redlines (opt-in, org-scoped — never shared across orgs) | The learned core of `NOVELTY.md` #4's procedural memory |
| **Document Sensitivity Classifier** | Auto-suggest a sensitivity tier at ingestion | Fine-tuned text classifier | Labeled examples of Public/Internal/Confidential/Privileged documents | Assists, does not replace, the uploader's own tier confirmation (`ARCHITECTURE.md`) |

## Infrastructure

All open-source and self-hostable (`MODEL_STACK.md`):

- **Training**: PyTorch + Hugging Face **TRL** (SFT / DPO / KTO / ORPO / GRPO under one API); **Unsloth** for low-VRAM LoRA/QLoRA (2× faster, ~half the VRAM — this is what makes fine-tuning feasible on an RTX-4050-class card in the constrained profile); **Axolotl** / **Llama-Factory** for config-driven multi-GPU runs; DeepSpeed/FSDP for anything bigger than a BERT head.
- **Weak-supervision / synthetic data**: **distilabel** (pipeline framework) with a self-hosted teacher; **skweak**/Snorkel for label-function aggregation.
- **Labelling & review**: **Argilla** (Python-native, LLM-proposes/human-corrects loop) primary; Label Studio for wider modalities.
- **Experiment tracking**: **MLflow** (self-hostable) for params, metrics, artifacts; **ClearML** an alternative if we want tracking + orchestration + data management in one tool.
- **Data versioning**: **DVC** so a model version is always traceable to an exact dataset snapshot — for reproducibility, for answering "what data trained the model that produced this output" if challenged, and as a precondition for any research publication or patent filing.
- **Compute**: on-demand GPU (spot/preemptible where the job tolerates interruption) for fine-tuning; trained-model inference runs on the same GPU pool that serves the Class B LLMs (`ARCHITECTURE.md`), or on CPU for the smaller taggers/classifiers. Per-task and per-org fine-tunes are served as **hot-swappable LoRA adapters** (vLLM multi-LoRA / LoRAX) — one base model, many adapters, no per-fine-tune model copy.
- **Model registry & packaging**: every trained model is versioned, tagged with its eval score, and requires passing the eval gate (`ARCHITECTURE.md`) before promotion — no hot-swap into the Model Router without the gate. Models ship to on-prem/air-gapped deployments as signed **KitOps ModelKit** OCI artifacts through Harbor, on the same supply chain as the code.

## Governance

- **Model cards** for every trained model: intended use, training data provenance, known limitations, eval scores, and — critically for legal-domain models — the specific jurisdictions/contract types the training data actually covers, so the system doesn't silently overgeneralize (e.g., a risk model trained mostly on US commercial leases should not be presented as equally reliable for another jurisdiction's employment contracts without evidence).
- **Bias/fairness checks**: for models touching entity recognition of parties/roles, evaluate for systematic disparities in extraction quality across naming conventions/languages present in the training data.
- **Org data isolation**: the Redline Acceptance Predictor and any other model trained on an org's own historical data is trained and served per-org (or per an explicit opt-in shared pool), never pooled across organizations without consent — this is a hard requirement, not a configuration default, given the confidentiality of negotiation history.
