# backend/app/eval/tasks.py
"""
Graded eval tasks (docs/v2/AI_STACK.md "Eval harness upgrade", ROADMAP Phase 6).

Each task is a plain function returning a `TaskResult` -- runnable with NO
inspect-ai (that's `inspect_tasks.py`, an optional wrapper). Two kinds:

  * model tasks  -- take a `generate_fn(prompt)->str` or `entail_fn(pairs)->EntailResult`
                    so the caller (cutover_gate.py) can bind them to a specific
                    provider (self-hosted vs Gemini) for a head-to-head.
  * rule tasks   -- the existing rule-based classifiers vs the gold set.

CLI:  python -m app.eval.tasks <task> [--limit N] [--split S]
"""
from __future__ import annotations

import argparse
import logging
import re
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from app.eval import metrics

logger = logging.getLogger("legalai.eval.tasks")


@dataclass
class TaskResult:
    name: str
    dataset: str
    metric: str
    score: float
    n: int
    extra: dict = field(default_factory=dict)

    def __str__(self) -> str:
        tail = "  ".join(f"{k}={v}" for k, v in self.extra.items())
        return f"{self.name:26s} {self.dataset:22s} {self.metric:10s} {self.score:.3f}  (n={self.n})  {tail}"


# --------------------------------------------------------------------------
# model task: NLI head, 3-class, on MNLI
# --------------------------------------------------------------------------

def run_nli_head(entail_fn: Callable, *, limit: int = 300, split: str = "validation_matched") -> TaskResult:
    """Grade an entailment provider on real 3-class NLI. `entail_fn(pairs)`
    returns an object with `.labels`."""
    from app.eval.datasets import load_mnli

    ex = load_mnli(split=split, limit=limit)
    pairs = [(e["premise"], e["hypothesis"]) for e in ex]
    golds = [e["label"] for e in ex]
    preds = entail_fn(pairs).labels
    acc = metrics.accuracy(preds, golds)
    mf1 = metrics.macro_f1(preds, golds, labels=["entailment", "neutral", "contradiction"])
    return TaskResult("nli_head_mnli", f"mnli/{split}", "accuracy", acc, len(ex),
                      extra={"macro_f1": round(mf1, 3)})


# --------------------------------------------------------------------------
# model task: LegalBench Yes/No QA (CUAD subtasks, ContractNLI subtasks, ...)
# --------------------------------------------------------------------------

_YESNO_PROMPT = (
    "You are a contract-analysis assistant. Answer the question with exactly one "
    "word: \"Yes\" or \"No\".\n\n{body}\n\nAnswer:"
)
_YES_RE = re.compile(r"\b(yes|true|correct|affirmative)\b", re.IGNORECASE)
_NO_RE = re.compile(r"\b(no|false|incorrect|negative)\b", re.IGNORECASE)


def _norm_yesno(text: str) -> str:
    head = (text or "").strip()[:120]
    if _YES_RE.search(head) and not _NO_RE.search(head):
        return "Yes"
    if _NO_RE.search(head):
        return "No"
    return "?"


def run_legalbench_qa(generate_fn: Callable, *, subtasks: Optional[List[str]] = None,
                      limit_per: int = 25, name: str = "legalbench_qa") -> TaskResult:
    from app.eval.datasets import (CONTRACT_NLI_SUBTASKS, CUAD_SUBTASKS,
                                   load_legalbench)

    subtasks = subtasks or (CUAD_SUBTASKS[:4] + CONTRACT_NLI_SUBTASKS[:2])
    preds: List[str] = []
    golds: List[str] = []
    for st in subtasks:
        try:
            examples = load_legalbench(st, limit=limit_per)
        except Exception as e:
            logger.warning("legalbench/%s skipped (%s)", st, e)
            continue
        for e in examples:
            out = generate_fn(_YESNO_PROMPT.format(body=e["input"][:6000]))
            preds.append(_norm_yesno(out))
            golds.append(e["answer"].strip().capitalize())
    acc = metrics.accuracy(preds, golds)
    unparsed = preds.count("?")
    return TaskResult(name, "legalbench(" + ",".join(s.split("_")[0] for s in dict.fromkeys(subtasks)) + ")",
                      "accuracy", acc, len(golds), extra={"unparsed": unparsed})


# --------------------------------------------------------------------------
# rule tasks: the existing gold-set classifiers
# --------------------------------------------------------------------------

def run_rule_clause_type() -> TaskResult:
    from app.eval.run_eval import run_eval

    r = run_eval()
    return TaskResult("rule_clause_type", "gold_set", "accuracy", r.clause_type_accuracy, r.total)


def run_rule_deontic() -> TaskResult:
    from app.eval.run_eval import run_eval

    r = run_eval()
    return TaskResult("rule_deontic", "gold_set", "recall", r.deontic_recall, r.deontic_recall_total)


# --------------------------------------------------------------------------
# registry + CLI
# --------------------------------------------------------------------------

def _router_generate_fn():
    from app.services.model_router import generate_content

    def fn(prompt: str) -> str:
        try:
            return generate_content(prompt, task="qa", sensitivity="public", temperature=0.0,
                                    max_output_tokens=16)
        except Exception as e:  # noqa: BLE001 - the task records a miss, not a crash
            logger.warning("generate failed: %s", e)
            return ""
    return fn


def _router_entail_fn():
    from app.services.model_router import entailment
    return lambda pairs: entailment(pairs)


TASKS: Dict[str, Callable[[], TaskResult]] = {
    "nli_head_mnli": lambda **kw: run_nli_head(_router_entail_fn(), **kw),
    "legalbench_qa": lambda **kw: run_legalbench_qa(_router_generate_fn(), **kw),
    "rule_clause_type": lambda **kw: run_rule_clause_type(),
    "rule_deontic": lambda **kw: run_rule_deontic(),
}


def main() -> None:
    ap = argparse.ArgumentParser(description="Run a graded eval task.")
    ap.add_argument("task", choices=sorted(TASKS))
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--split", default=None)
    ap.add_argument("--write-db", action="store_true", help="persist an eval_runs row")
    args = ap.parse_args()

    kw: dict = {}
    if args.limit is not None:
        kw["limit"] = args.limit
    if args.split is not None:
        kw["split"] = args.split
    result = TASKS[args.task](**kw)
    print(result)

    if args.write_db:
        from app.eval.eval_store import record_eval_run

        record_eval_run(task=result.name, dataset=result.dataset, provider="router",
                        model="-", metric=result.metric, score=result.score,
                        n_examples=result.n, notes=str(result.extra))
        print("(eval_runs row written)")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    main()
