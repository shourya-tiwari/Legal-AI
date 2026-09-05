# backend/app/eval/cutover_gate.py
"""
The Phase 6 cutover gate (docs/v2/ROADMAP.md Phase 6: "a self-hosted model
becomes default for a task only after meeting or beating the Gemini baseline
on that task's eval").

For each cutover candidate it runs the task's graded eval TWICE -- once bound
to the `baseline` provider (gemini), once to the `candidate` provider
(local-llm) -- on identical inputs, then:

    passed = candidate_score >= baseline_score * min_ratio

It prints a markdown table and writes one `eval_runs` row per (task, provider)
with the candidate row carrying `baseline_score` + `passed`. A candidate that
can't run (no self-hosted LLM served yet) reports "cannot evaluate", never a
false PASS.

CLI:  python -m app.eval.cutover_gate [--task qa] [--limit-per N]

Requires `EXTERNAL_PROVIDERS_ENABLED=true` + a GOOGLE_API_KEY +
`pip install -r requirements-external.txt` for the baseline column.
"""
from __future__ import annotations

import argparse
import logging
from dataclasses import dataclass
from typing import Callable, List, Optional

from app.eval import tasks as eval_tasks
from app.eval.eval_store import record_eval_run
from app.services.model_router.registry import get_provider
from app.services.model_router.types import (GenerateRequest, ProviderUnavailable,
                                             SensitivityTier)

logger = logging.getLogger("legalai.eval.cutover")


@dataclass
class Candidate:
    task: str                    # the routing-policy task this gates
    eval_name: str
    run: Callable                # (generate_fn) -> TaskResult
    min_ratio: float = 1.0
    graded: bool = True
    temperature: float = 0.0
    max_output_tokens: int = 16


CUTOVER_CANDIDATES: List[Candidate] = [
    Candidate(
        task="qa",
        eval_name="legalbench_qa",
        run=lambda gen: eval_tasks.run_legalbench_qa(gen, limit_per=25),
        min_ratio=1.0,
    ),
    Candidate(
        task="clause_rewrite",
        eval_name="rewrite_retention",
        run=lambda gen: eval_tasks.run_rewrite_gold(gen),
        min_ratio=1.0,
        temperature=0.3,
        max_output_tokens=400,
    ),
    Candidate(
        task="timeline_extract",
        eval_name="timeline_extraction",
        run=lambda gen: eval_tasks.run_timeline_extract_gold(gen),
        min_ratio=1.0,
        temperature=0.2,
        max_output_tokens=500,
    ),
    Candidate(
        task="risk_analysis",
        eval_name="risk_flag_recall",
        run=lambda gen: eval_tasks.run_risk_analysis_gold(gen),
        min_ratio=1.0,
        temperature=0.2,
        max_output_tokens=400,
    ),
    # contextualize / agent_summary have no gold eval set yet -- open-ended
    # generation with citations has no clean automatic reference; see
    # app/eval/delta_report.py for the agreement-with-baseline view instead.
]


def _provider_generate_fn(provider_name: str, *, task: str = "qa", temperature: float = 0.0,
                          max_output_tokens: int = 16) -> Callable[[str], str]:
    provider = get_provider(provider_name)

    def fn(prompt: str) -> str:
        if provider is None or not provider.is_available():
            raise ProviderUnavailable(f"{provider_name} unavailable")
        req = GenerateRequest(prompt=prompt, task=task, sensitivity=SensitivityTier.PUBLIC,
                              temperature=temperature, max_output_tokens=max_output_tokens)
        return provider.generate(req).text

    return fn


def _score_or_none(run: Callable, gen_fn: Callable):
    try:
        # probe: does the provider answer at all?
        gen_fn("Reply with the single word: Yes")
    except Exception as e:  # noqa: BLE001
        return None, f"cannot evaluate ({e})"
    try:
        result = run(gen_fn)
        return result, None
    except Exception as e:  # noqa: BLE001
        return None, f"eval error ({e})"


def run_cutover_gate(candidates: Optional[List[Candidate]] = None, *,
                     baseline_provider: str = "gemini",
                     candidate_provider: str = "local-llm",
                     write_db: bool = True) -> List[dict]:
    candidates = candidates or CUTOVER_CANDIDATES
    rows: List[dict] = []
    for c in candidates:
        base_fn = _provider_generate_fn(baseline_provider, task=c.task, temperature=c.temperature,
                                        max_output_tokens=c.max_output_tokens)
        cand_fn = _provider_generate_fn(candidate_provider, task=c.task, temperature=c.temperature,
                                        max_output_tokens=c.max_output_tokens)
        base_res, base_err = _score_or_none(c.run, base_fn)
        cand_res, cand_err = _score_or_none(c.run, cand_fn)

        base_score = base_res.score if base_res else None
        cand_score = cand_res.score if cand_res else None
        passed: Optional[bool] = None
        if base_score is not None and cand_score is not None:
            passed = cand_score >= base_score * c.min_ratio

        rows.append({
            "task": c.task, "eval": c.eval_name, "metric": (cand_res or base_res).metric if (cand_res or base_res) else "-",
            "baseline": base_score, "candidate": cand_score, "min_ratio": c.min_ratio,
            "passed": passed, "baseline_err": base_err, "candidate_err": cand_err,
            "n": (cand_res or base_res).n if (cand_res or base_res) else 0,
        })

        if write_db and base_res:
            record_eval_run(task=c.eval_name, dataset=base_res.dataset, provider=baseline_provider,
                            model="-", metric=base_res.metric, score=base_res.score,
                            n_examples=base_res.n, notes="cutover baseline")
        if write_db and cand_res:
            record_eval_run(task=c.eval_name, dataset=cand_res.dataset, provider=candidate_provider,
                            model="-", metric=cand_res.metric, score=cand_res.score,
                            n_examples=cand_res.n, baseline_score=base_score, passed=passed,
                            notes="cutover candidate")
    return rows


def render_markdown(rows: List[dict]) -> str:
    out = [
        "# Cutover gate: self-hosted vs. Gemini baseline",
        "",
        "| task | eval | metric | gemini | local-llm | ×ratio | verdict |",
        "|---|---|---|---:|---:|---:|---|",
    ]
    for r in rows:
        b = f"{r['baseline']:.3f}" if r["baseline"] is not None else (r["baseline_err"] or "-")
        c = f"{r['candidate']:.3f}" if r["candidate"] is not None else (r["candidate_err"] or "-")
        if r["passed"] is True:
            verdict = "✅ PASS — safe to cut over"
        elif r["passed"] is False:
            verdict = "❌ FAIL — keep baseline"
        else:
            verdict = "⚠️ cannot evaluate"
        out.append(f"| {r['task']} | {r['eval']} | {r['metric']} | {b} | {c} | {r['min_ratio']} | {verdict} |")
    out += ["", "_A task cuts over to the self-hosted default only on ✅. "
            "Tasks without a graded eval set are not listed — run `python -m app.eval.delta_report` "
            "for their agreement-with-baseline view._"]
    return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser(description="Run the Phase 6 cutover gate.")
    ap.add_argument("--task", help="gate a single task by name (default: all)")
    ap.add_argument("--no-db", action="store_true", help="don't write eval_runs rows")
    args = ap.parse_args()

    cands = CUTOVER_CANDIDATES
    if args.task:
        cands = [c for c in cands if c.task == args.task]
        if not cands:
            raise SystemExit(f"no cutover candidate for task '{args.task}'")
    rows = run_cutover_gate(cands, write_db=not args.no_db)
    print(render_markdown(rows))


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
    main()
