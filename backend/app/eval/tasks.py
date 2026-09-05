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
import json
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
# model task: clause rewrite -- plain-English retention + jargon removal
# (docs/v2/ROADMAP.md Phase 6 cutover gate: `clause_rewrite` had no graded
# eval before this; delta_report.py's qualitative view is not a gate.)
# --------------------------------------------------------------------------

_REWRITE_PROMPT = """
You are an expert legal editor.

Rewrite the following legal clause into simple English.

Rules:

- Preserve the exact legal meaning.
- Do NOT remove important details.
- Do NOT add information.
- Make it understandable for a normal person.
- Return ONLY the rewritten text.

Clause:

{clause}
"""


def run_rewrite_gold(generate_fn: Callable, *, name: str = "rewrite_retention") -> TaskResult:
    """Grade a rewrite against REWRITE_GOLD. There's no single reference
    paraphrase for free text, so this checks the two properties a correct
    rewrite provably has: it keeps the operative facts (`must_retain`, exact
    substring match) and it actually drops the legalese it was asked to
    plain-English (`banned_jargon` must NOT still appear). Per-example score
    is 1.0 (both hold), 0.5 (one holds), or 0.0 (neither)."""
    from app.eval.gold_set import REWRITE_GOLD

    scores: List[float] = []
    retained_fails = 0
    jargon_fails = 0
    for ex in REWRITE_GOLD:
        out = (generate_fn(_REWRITE_PROMPT.format(clause=ex["text"])) or "").lower()
        retained = all(term.lower() in out for term in ex["must_retain"])
        clean = not any(term.lower() in out for term in ex["banned_jargon"])
        retained_fails += 0 if retained else 1
        jargon_fails += 0 if clean else 1
        scores.append(1.0 if (retained and clean) else (0.5 if (retained or clean) else 0.0))
    score = sum(scores) / len(scores) if scores else 0.0
    return TaskResult(name, "gold_set", "retention_score", score, len(REWRITE_GOLD),
                      extra={"retained_fails": retained_fails, "jargon_fails": jargon_fails})


# --------------------------------------------------------------------------
# model task: timeline extraction -- per-event best-match token-F1
# --------------------------------------------------------------------------

_TIMELINE_PROMPT_HEAD = (
    "Extract all key dates, deadlines, and time-based obligations from the text. "
    'Return JSON array: [{"date_description": str, "event": str}].'
    "\n\nReturn only valid JSON array, no prose.\n\n<text>\n"
)
_TIMELINE_PROMPT_TAIL = "\n</text>"


def run_timeline_extract_gold(generate_fn: Callable, *, name: str = "timeline_extraction") -> TaskResult:
    """Grade timeline extraction against TIMELINE_GOLD. For each gold event,
    take the best token-F1 (over date_description + event text combined)
    against any predicted event, then average across all gold events in the
    set -- a squad_f1-style "did the model find something close to this"
    metric, tolerant of wording, not of missing or wrong dates/obligations."""
    from app.eval.gold_set import TIMELINE_GOLD
    from app.services.timeline import _parse_json_list

    per_gold_scores: List[float] = []
    for ex in TIMELINE_GOLD:
        raw = generate_fn(_TIMELINE_PROMPT_HEAD + ex["text"] + _TIMELINE_PROMPT_TAIL)
        predicted = _parse_json_list(raw)
        pred_strs = [f"{p.get('date_description', '')} {p.get('event', '')}" for p in predicted if isinstance(p, dict)]
        for gold_ev in ex["expected_events"]:
            gold_str = f"{gold_ev['date_description']} {gold_ev['event']}"
            best = max((metrics.token_f1(pred, gold_str) for pred in pred_strs), default=0.0)
            per_gold_scores.append(best)
    score = sum(per_gold_scores) / len(per_gold_scores) if per_gold_scores else 0.0
    return TaskResult(name, "gold_set", "event_f1", score, len(per_gold_scores))


# --------------------------------------------------------------------------
# model task: risk-flag recall
# --------------------------------------------------------------------------

_RISK_PROMPT = (
    "Highlight potential high-risk terms in this clause and return JSON only.\n"
    'Format: {{"flags":[{{"term":"...","explanation":"..."}}]}}\n'
    'Clause: "{clause}"'
)


def run_risk_analysis_gold(generate_fn: Callable, *, name: str = "risk_flag_recall") -> TaskResult:
    """Grade the AI risk pass against RISK_GOLD as recall: of the phrases
    that make each clause genuinely risky, how many does the model's
    {"flags":[...]} JSON actually surface (substring match over the combined
    term+explanation text of every returned flag)?"""
    from app.eval.gold_set import RISK_GOLD
    from app.services.timeline import _strip_code_fences

    hits = 0
    total = 0
    for ex in RISK_GOLD:
        raw = generate_fn(_RISK_PROMPT.format(clause=ex["text"])) or ""
        try:
            parsed = json.loads(_strip_code_fences(raw))
            flags = parsed.get("flags", []) if isinstance(parsed, dict) else []
        except Exception:
            flags = []
        blob = " ".join(
            f"{f.get('term', '')} {f.get('explanation', '')}" for f in flags if isinstance(f, dict)
        ).lower()
        for expected_term in ex["expected_terms"]:
            total += 1
            if expected_term.lower() in blob:
                hits += 1
    recall = hits / total if total else 0.0
    return TaskResult(name, "gold_set", "recall", recall, total)


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

def _router_generate_fn(*, task: str = "qa", temperature: float = 0.0, max_output_tokens: int = 16):
    from app.services.model_router import generate_content

    def fn(prompt: str) -> str:
        try:
            return generate_content(prompt, task=task, sensitivity="public", temperature=temperature,
                                    max_output_tokens=max_output_tokens)
        except Exception as e:  # noqa: BLE001 - the task records a miss, not a crash
            logger.warning("generate failed: %s", e)
            return ""
    return fn


def _router_entail_fn():
    from app.services.model_router import entailment
    return lambda pairs: entailment(pairs)


TASKS: Dict[str, Callable[[], TaskResult]] = {
    "nli_head_mnli": lambda **kw: run_nli_head(_router_entail_fn(), **kw),
    "legalbench_qa": lambda **kw: run_legalbench_qa(_router_generate_fn(task="qa", max_output_tokens=16), **kw),
    "rewrite_retention": lambda **kw: run_rewrite_gold(
        _router_generate_fn(task="clause_rewrite", temperature=0.3, max_output_tokens=400), **kw),
    "timeline_extraction": lambda **kw: run_timeline_extract_gold(
        _router_generate_fn(task="timeline_extract", temperature=0.2, max_output_tokens=500), **kw),
    "risk_flag_recall": lambda **kw: run_risk_analysis_gold(
        _router_generate_fn(task="risk_analysis", temperature=0.2, max_output_tokens=400), **kw),
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
