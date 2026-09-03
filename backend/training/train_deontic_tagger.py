# backend/training/train_deontic_tagger.py
"""
Fine-tune the deontic-modality tagger (Phase 6/8).

MULTI-label sequence classification (a sentence can carry several of
{obligation, permission, prohibition, discretion}, or none) on a
Legal-BERT / ModernBERT base + LoRA. Config-driven; nothing runs unless
invoked.

    python training/prepare_deontic_data.py [--llm-teacher]
    python training/train_deontic_tagger.py training/configs/deontic_tagger.yaml
    #   --dry-run / --smoke  as in train_clause_classifier.py

The rule tagger (app/services/nlp/deontic.py) stays the Tier-0 pre-filter and
the production path until this beats it on the eval gate.
"""
from __future__ import annotations

import argparse

from _common import DATA_DIR, load_yaml_config, log, read_jsonl

LABELS = ["obligation", "permission", "prohibition", "discretion"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("config")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()
    cfg = load_yaml_config(args.config)

    train_rows = read_jsonl(DATA_DIR / "deontic_train.jsonl")
    val_rows = read_jsonl(DATA_DIR / "deontic_val.jsonl")
    log.info("train=%d val=%d labels=%s", len(train_rows), len(val_rows), LABELS)

    if args.dry_run:
        from collections import Counter

        c = Counter(l for r in train_rows + val_rows for l in r["labels"])
        log.info("label counts: %s", dict(c))
        log.info("--dry-run complete; no training run.")
        return

    import numpy as np
    import torch
    from datasets import Dataset
    from transformers import (AutoModelForSequenceClassification, AutoTokenizer,
                              DataCollatorWithPadding, Trainer, TrainingArguments)

    base = cfg["base_model"]
    tok = AutoTokenizer.from_pretrained(base)
    idx = {l: i for i, l in enumerate(LABELS)}

    def encode(rows):
        def to_row(r):
            vec = [0.0] * len(LABELS)
            for l in r["labels"]:
                if l in idx:
                    vec[idx[l]] = 1.0
            return {"text": r["text"], "labels": vec}

        ds = Dataset.from_list([to_row(r) for r in rows])
        return ds.map(lambda b: tok(b["text"], truncation=True, max_length=cfg.get("max_length", 256)),
                      batched=True)

    train_ds, val_ds = encode(train_rows), encode(val_rows)

    model = AutoModelForSequenceClassification.from_pretrained(
        base, num_labels=len(LABELS), problem_type="multi_label_classification",
        id2label=dict(enumerate(LABELS)), label2id=idx,
    )
    if cfg.get("use_lora", True):
        from peft import LoraConfig, TaskType, get_peft_model

        model = get_peft_model(model, LoraConfig(
            task_type=TaskType.SEQ_CLS, r=cfg.get("lora_r", 16),
            lora_alpha=cfg.get("lora_alpha", 32), lora_dropout=cfg.get("lora_dropout", 0.05),
        ))
        model.print_trainable_parameters()

    def metrics_fn(eval_pred):
        from sklearn.metrics import f1_score

        logits, labels = eval_pred
        preds = (torch.sigmoid(torch.tensor(logits)).numpy() > 0.5).astype(int)
        return {"micro_f1": f1_score(labels, preds, average="micro", zero_division=0),
                "macro_f1": f1_score(labels, preds, average="macro", zero_division=0)}

    targs = TrainingArguments(
        output_dir=cfg.get("output_dir", "training/out/deontic_tagger"),
        learning_rate=cfg.get("lr", 2e-4),
        per_device_train_batch_size=cfg.get("batch_size", 16),
        num_train_epochs=cfg.get("epochs", 8),
        eval_strategy="epoch", save_strategy="epoch",
        load_best_model_at_end=True, metric_for_best_model="micro_f1",
        max_steps=2 if args.smoke else -1, logging_steps=10, report_to=[],
    )
    trainer = Trainer(model=model, args=targs, train_dataset=train_ds, eval_dataset=val_ds,
                      data_collator=DataCollatorWithPadding(tok), compute_metrics=metrics_fn)
    trainer.train()
    log.info("eval: %s", trainer.evaluate())
    if not args.smoke:
        trainer.save_model(targs.output_dir)
        tok.save_pretrained(targs.output_dir)


if __name__ == "__main__":
    main()
