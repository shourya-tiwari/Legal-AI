# backend/app/agents/summary.py
"""
Summary agent: the one node in this pipeline that actually generates
natural-language output (via the Model Router / Gemini) -- everything
upstream is deterministic extraction/retrieval. Citations are numbered
globally across all flagged clauses' retrieved sources (not per-clause) so
the model can cite any of them by a single consistent [N], and the Verifier
agent can check those numbers the same way services/rag/citation_validator.py
already does for the Contextualizer.
"""
from __future__ import annotations

from typing import List, Tuple

from app.services.model_router import generate_content

from .state import AgentStep, CaseState

_PROMPT_TEMPLATE = """You are summarizing risk findings for a legal contract for a non-lawyer reader.

Risk findings:
{findings_block}

Numbered sources available to cite (cite by number in brackets, e.g. [1], only when you use a fact from one):
{sources_block}

Write a short (3-6 sentence) plain-English risk summary. Only state something as a rule/limit if it is
supported by a numbered source above; otherwise say it varies and should be verified locally. Do not
invent a citation number that isn't listed above.
"""


def _build_sources_block(state: CaseState) -> Tuple[str, List[str]]:
    all_sources: List[str] = []
    for clause_id in sorted(state.research_citations):
        for entry in state.research_citations[clause_id]:
            all_sources.append(entry["text"])

    if not all_sources:
        return "(none retrieved)", []

    numbered = "\n".join(f"[{i}] {text}" for i, text in enumerate(all_sources, start=1))
    return numbered, all_sources


def run_summary(state: CaseState) -> dict:
    if not state.risk_findings and not state.kg_conflicts:
        step = AgentStep(agent_name="summary", input_summary="no risk findings", output_summary="skipped")
        return {"summary": "No notable risk findings.", "summary_citation_count": 0, "trace": state.trace + [step]}

    findings_lines = [f"- {f.term}: {f.explanation}" for f in state.risk_findings]
    findings_lines += [
        f"- Potential conflict on term '{c.term}' between an obligation and a prohibition across documents"
        for c in state.kg_conflicts
    ]
    sources_block, all_sources = _build_sources_block(state)

    prompt = _PROMPT_TEMPLATE.format(findings_block="\n".join(findings_lines), sources_block=sources_block)
    summary_text = generate_content(prompt, task="agent_summary", temperature=0.2)

    step = AgentStep(
        agent_name="summary",
        input_summary=f"{len(findings_lines)} findings, {len(all_sources)} candidate sources",
        output_summary=f"{len(summary_text)} char summary generated",
    )

    return {"summary": summary_text, "summary_citation_count": len(all_sources), "trace": state.trace + [step]}
