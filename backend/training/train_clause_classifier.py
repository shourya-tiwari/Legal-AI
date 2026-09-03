# backend/training/train_clause_classifier.py
"""
Fine-tune a clause / contract-type classifier (Phase 6/8, docs/v2/NLP.md §8).

Single-label sequence classification on a Legal-BERT / ModernBERT base with a
PEFT LoRA adapter. Config-driven; nothing runs unless you invoke it.

    python training/prepare_clause_data.py
    python training/train_clause_classifier.py training/configs/clause_classifier.yaml
    #   --dry-run : load + validate data, print label map, exit (no training)
    #   --smoke   : 2 optimizer steps, prove the loop runs

Promotion is manual and eval-gated: run app/eval/tasks.py against the trained
head vs classify_clause_type_rule_based(); only register it in the routing
policy if it beats the rule baseline. Write a model card
(training/model_card_template.md).
"""
from __future__ import annotations

import argparse

from _common import DATA_DIR, load_yaml_config, log, read_jsonl


def _build_label_map(rows) -> dict:
    labels = sorted({r["label"] for r in rows})
    return {lab: i for i, lab in enumerate(labels)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("config")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()
    cfg = load_yaml_config(args.config)

    train_rows = read_jsonl(DATA_DIR / "clause_train.jsonl")
    val_rows = read_jsonl(DATA_DIR / "clause_val.jsonl")
    label2id = _build_label_map(train_rows + val_rows)
    id2label = {i: l for l, i in label2id.items()}
    log.info("train=%d val=%d labels=%d %s", len(train_rows), len(val_rows), len(label2id), list(label2id))

    if args.dry_run:
        log.info("--dry-run complete; no training run.")
        return

    import numpy as np
    from datasets import Dataset
    from transformers import (AutoModelForSequenceClassification, AutoTokenizer,
                              DataCollatorWithPadding, Trainer, TrainingArguments)

    base = cfg["base_model"]
    tok = AutoTokenizer.from_pretrained(base)

    def encode(rows):
        ds = Dataset.from_list([{"text": r["text"], "label": label2id[r["label"]]} for r in rows])
        return ds.map(lambda b: tok(b["text"], truncation=True, max_length=cfg.get("max_length", 512)),
                      batched=True)

    train_ds, val_ds = encode(train_rows), encode(val_rows)

    model = AutoModelForSequenceClassification.from_pretrained(
        base, num_labels=len(label2id), id2label=id2label, label2id=label2id
    )
    if cfg.get("use_lora", True):
        from peft import LoraConfig, TaskType, get_peft_model

        model = get_peft_model(model, LoraConfig(
            task_type=TaskType.SEQ_CLS, r=cfg.get("lora_r", 16),
            lora_alpha=cfg.get("lora_alpha", 32), lora_dropout=cfg.get("lora_dropout", 0.05),
        ))
        model.print_trainable_parameters()

    def metrics_fn(eval_pred):
        from sklearn.metrics import accuracy_score, f1_score

        logits, labels = eval_pred
        preds = np.argmax(logits, axis=-1)
        return {"accuracy": accuracy_score(labels, preds),
                "macro_f1": f1_score(labels, preds, average="macro")}

    targs = TrainingArguments(
        output_dir=cfg.get("output_dir", "training/out/clause_classifier"),
        learning_rate=cfg.get("lr", 2e-4),
        per_device_train_batch_size=cfg.get("batch_size", 16),
        per_device_eval_batch_size=cfg.get("batch_size", 16),
        num_train_epochs=cfg.get("epochs", 6),
        eval_strategy="epoch", save_strategy="epoch",
        load_best_model_at_end=True, metric_for_best_model="macro_f1",
        max_steps=2 if args.smoke else -1,
        logging_steps=10, report_to=[],
    )
    trainer = Trainer(model=model, args=targs, train_dataset=train_ds, eval_dataset=val_ds,
                      data_collator=DataCollatorWithPadding(tok), compute_metrics=metrics_fn)
    trainer.train()
    log.info("eval: %s", trainer.evaluate())
    if not args.smoke:
        trainer.save_model(targs.output_dir)
        tok.save_pretrained(targs.output_dir)
        log.info("saved -> %s  (now eval-gate it against the rule baseline before promoting)", targs.output_dir)


if __name__ == "__main__":
    main()
