# backend/app/eval/delta_report.py
"""
The self-hosted-vs-external delta report (docs/v2/AI_STACK.md "Eval harness
upgrade": "for each task, measure what (if anything) Class C would add. This
report gates every future decision to enable Class C.").

It runs a fixed prompt fixture through TWO specific providers on identical
inputs -- the self-hosted `local-llm` (Ollama/vLLM) and the external
`gemini` -- and prints a side-by-side table with cheap, deterministic
proxy metrics (no LLM judge required):

  * latency (ms)
  * output length ratio vs. the other provider
  * token-F1 agreement between the two outputs (how much they converge)

This is intentionally a *decision aid*, not a leaderboard: a large divergence
on a task is the signal to run a real Inspect AI eval (inspect_tasks.py)
before trusting -- or before dropping -- either provider for that task.

Usage (from backend/, with .env configured and EXTERNAL_PROVIDERS_ENABLED=true):
    python -m app.eval.delta_report
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import List, Optional

from app.services.model_router.registry import get_provider
from app.services.model_router.types import (
    GenerateRequest,
    ProviderUnavailable,
    SensitivityTier,
)

# (task, prompt) fixture -- one representative prompt per generative task.
FIXTURE: List[tuple[str, str]] = [
    ("clause_rewrite",
     "Rewrite this contract clause in plain English for a non-lawyer, one short paragraph:\n"
     "'Tenant shall indemnify, defend and hold Landlord harmless from and against any and all "
     "claims, damages, losses and expenses arising out of Tenant's use of the Premises.'"),
    ("qa",
     "Contract context: 'Either party may terminate this Agreement for convenience upon "
     "sixty (60) days prior written notice.' Question: How much notice is needed to terminate, "
     "and can either side do it?"),
    ("risk_analysis",
     "Identify the single biggest risk to the customer in this clause and why, in two sentences:\n"
     "'The Provider may modify the fees at any time in its sole discretion, effective immediately "
     "upon posting to the Provider website.'"),
    ("contextualize",
     "A tenant in California asks what this means for them. Two sentences, cautious tone:\n"
     "'Landlord shall return the security deposit, less lawful deductions, within 21 days after "
     "the tenant vacates.'"),
]

_WORD_RE = re.compile(r"[a-z0-9']+")


def _tokens(text: str) -> List[str]:
    return _WORD_RE.findall(text.lower())


def _token_f1(a: str, b: str) -> float:
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return 0.0
    sa, sb = set(ta), set(tb)
    tp = len(sa & sb)
    if tp == 0:
        return 0.0
    precision = tp / len(sa)
    recall = tp / len(sb)
    return 2 * precision * recall / (precision + recall)


@dataclass
class Row:
    task: str
    local_ms: Optional[int]
    external_ms: Optional[int]
    local_len: int
    external_len: int
    agreement_f1: float
    local_error: Optional[str] = None
    external_error: Optional[str] = None


def _run_one(provider_name: str, req: GenerateRequest):
    provider = get_provider(provider_name)
    if provider is None:
        return None, f"{provider_name}: not registered"
    if not provider.is_available():
        return None, f"{provider_name}: not available (check config / server)"
    start = time.perf_counter()
    try:
        result = provider.generate(req)
    except (ProviderUnavailable, NotImplementedError, RuntimeError) as e:
        return None, f"{provider_name}: {e}"
    return (result.text, int((time.perf_counter() - start) * 1000)), None


def build_report() -> List[Row]:
    rows: List[Row] = []
    for task, prompt in FIXTURE:
        req = GenerateRequest(prompt=prompt, task=task, sensitivity=SensitivityTier.PUBLIC,
                              temperature=0.2, max_output_tokens=400)
        local, local_err = _run_one("local-llm", req)
        external, external_err = _run_one("gemini", req)
        local_text = local[0] if local else ""
        external_text = external[0] if external else ""
        rows.append(Row(
            task=task,
            local_ms=local[1] if local else None,
            external_ms=external[1] if external else None,
            local_len=len(_tokens(local_text)),
            external_len=len(_tokens(external_text)),
            agreement_f1=round(_token_f1(local_text, external_text), 3),
            local_error=local_err,
            external_error=external_err,
        ))
    return rows


def render_markdown(rows: List[Row]) -> str:
    lines = [
        "# Self-hosted vs. external delta report",
        "",
        "| task | local ms | gemini ms | local toks | gemini toks | agreement F1 | notes |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for r in rows:
        notes = "; ".join(filter(None, [r.local_error, r.external_error])) or "-"
        lines.append(
            f"| {r.task} | {r.local_ms if r.local_ms is not None else '-'} "
            f"| {r.external_ms if r.external_ms is not None else '-'} "
            f"| {r.local_len} | {r.external_len} | {r.agreement_f1} | {notes} |"
        )
    lines += [
        "",
        "_agreement F1_ = token-set F1 between the two outputs. Low F1 with both providers "
        "succeeding = the task where Class C might still be adding (or losing) something; "
        "run `python -m app.eval.inspect_tasks` for a real graded eval before acting on it.",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    print(render_markdown(build_report()))
