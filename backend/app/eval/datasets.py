# backend/app/eval/datasets.py
"""
Legal-domain benchmark corpora for the eval harness (docs/v2/AI_STACK.md
"Legal-domain benchmarks", ROADMAP Phase 5/6).

These are the corpora the self-hosted default is tracked against continuously
once GPU serving lands (Phase 6). For now they back:
  - the Inspect AI suite seed (inspect_tasks.py)
  - ad-hoc "is the self-hosted model good enough for this task yet" checks

Loading is lazy and behind the optional `datasets` dependency
(requirements-eval.txt) -- nothing here is imported by the app or the fast
CI eval gate.
"""
from __future__ import annotations

import logging
from functools import lru_cache
from typing import List, TypedDict

logger = logging.getLogger("legalai.eval.datasets")

_PIP_HINT = "pip install -r requirements-eval.txt  (adds the `datasets` package)"


def _require_datasets():
    try:
        import datasets  # noqa: F401
    except Exception as e:  # pragma: no cover - exercised only without the extra
        raise RuntimeError(
            f"The `datasets` package is required to load benchmark corpora. {_PIP_HINT}"
        ) from e
    return datasets


class QAExample(TypedDict):
    question: str
    context: str
    answers: List[str]          # empty list == "not present in the contract"


class NLIExample(TypedDict):
    premise: str
    hypothesis: str
    label: str                  # entailment | contradiction | neutral


@lru_cache(maxsize=2)
def load_cuad(split: str = "test", limit: int = 200) -> List[QAExample]:
    """CUAD (Contract Understanding Atticus Dataset) -- 41 clause-extraction
    question types over commercial contracts. Used for the extraction /
    clause-Q&A tasks."""
    ds = _require_datasets().load_dataset("theatticusproject/cuad-qa", split=split)
    out: List[QAExample] = []
    for row in ds:
        if limit and len(out) >= limit:
            break
        out.append(
            QAExample(
                question=row["question"],
                context=row["context"],
                answers=list(row["answers"]["text"]),
            )
        )
    logger.info("Loaded %d CUAD examples (split=%s).", len(out), split)
    return out


@lru_cache(maxsize=2)
def load_contractnli(split: str = "test", limit: int = 200) -> List[NLIExample]:
    """ContractNLI -- document-level NLI over NDAs. The reference corpus for
    the Verifier's real faithfulness/entailment head (Phase 6 follow-up)."""
    ds = _require_datasets().load_dataset("kiddothe2b/contract-nli", split=split)
    label_names = ds.features["label"].names if hasattr(ds.features["label"], "names") else None
    out: List[NLIExample] = []
    for row in ds:
        if limit and len(out) >= limit:
            break
        label = row["label"]
        if label_names and isinstance(label, int):
            label = label_names[label]
        out.append(
            NLIExample(
                premise=row.get("premise") or row.get("text") or "",
                hypothesis=row.get("hypothesis") or "",
                label=str(label),
            )
        )
    logger.info("Loaded %d ContractNLI examples (split=%s).", len(out), split)
    return out
