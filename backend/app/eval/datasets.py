# backend/app/eval/datasets.py
"""
Legal-domain benchmark corpora for the eval harness (docs/v2/MODEL_STACK.md
"Legal-domain benchmarks", ROADMAP Phase 6).

Everything routes through **LegalBench** (`nguha/legalbench`, MIT/CC) plus
**MNLI** (`nyu-mll/multi_nli`) for grading the NLI head's core ability:

  - LegalBench `cuad_*`      -> clause-presence QA (Yes/No)  -> proxy for CUAD extraction
  - LegalBench `contract_nli_*` -> NDA entailment (Yes/No)
  - LegalBench `consumer_contracts_qa` -> contract QA (Yes/No)
  - MNLI validation          -> 3-class NLI (entailment/neutral/contradiction)

(The original SQuAD-format CUAD and ContractNLI datasets are script-based and
no longer loadable by `datasets` >= 3; LegalBench's reformatted subtasks are
the maintained path. See LEARNING_LOG.md.)

Loading is lazy behind the optional `datasets` dependency (requirements-eval.txt)
-- nothing here is imported by the app or the fast CI eval gate.
"""
from __future__ import annotations

import logging
from functools import lru_cache
from typing import List, TypedDict

logger = logging.getLogger("legalai.eval.datasets")

_PIP_HINT = "pip install -r requirements-eval.txt  (adds the `datasets` package)"

# A representative slice -- not all 162 LegalBench tasks. Extend as needed.
CUAD_SUBTASKS = [
    "cuad_governing_law", "cuad_anti-assignment", "cuad_audit_rights",
    "cuad_cap_on_liability", "cuad_termination_for_convenience",
    "cuad_uncapped_liability", "cuad_non-compete", "cuad_exclusivity",
]
CONTRACT_NLI_SUBTASKS = [
    "contract_nli_confidentiality_of_agreement", "contract_nli_limited_use",
    "contract_nli_sharing_with_third-parties", "contract_nli_return_of_confidential_information",
    "contract_nli_permissible_copy", "contract_nli_survival_of_obligations",
]

_MNLI_LABELS = {0: "entailment", 1: "neutral", 2: "contradiction"}


class QAExample(TypedDict):
    input: str            # the question / clause text presented to the model
    answer: str           # "Yes" | "No" (LegalBench convention)
    subtask: str


class NLIExample(TypedDict):
    premise: str
    hypothesis: str
    label: str            # entailment | neutral | contradiction


def _require_datasets():
    try:
        import datasets  # noqa: F401
    except Exception as e:  # pragma: no cover - exercised only without the extra
        raise RuntimeError(
            f"The `datasets` package is required to load benchmark corpora. {_PIP_HINT}"
        ) from e
    return datasets


@lru_cache(maxsize=64)
def load_legalbench(subtask: str, split: str = "test", limit: int = 200) -> List[QAExample]:
    """One LegalBench subtask as Yes/No QA examples."""
    ds = _require_datasets().load_dataset("nguha/legalbench", subtask, split=split)
    cols = set(ds.column_names)
    q_col = next((c for c in ("question", "text", "contract") if c in cols), None)
    out: List[QAExample] = []
    for row in ds:
        if limit and len(out) >= limit:
            break
        parts = []
        if "contract" in cols and q_col != "contract":
            parts.append(str(row["contract"]))
        parts.append(str(row[q_col]) if q_col else "")
        out.append(QAExample(input="\n\n".join(p for p in parts if p),
                             answer=str(row["answer"]).strip(), subtask=subtask))
    logger.info("Loaded %d examples from legalbench/%s (%s).", len(out), subtask, split)
    return out


def load_cuad_subtasks(limit_per: int = 40) -> List[QAExample]:
    out: List[QAExample] = []
    for st in CUAD_SUBTASKS:
        try:
            out.extend(load_legalbench(st, limit=limit_per))
        except Exception as e:  # a single missing subtask shouldn't kill the run
            logger.warning("legalbench/%s skipped (%s)", st, e)
    return out


def load_contractnli_subtasks(limit_per: int = 40) -> List[QAExample]:
    out: List[QAExample] = []
    for st in CONTRACT_NLI_SUBTASKS:
        try:
            out.extend(load_legalbench(st, limit=limit_per))
        except Exception as e:
            logger.warning("legalbench/%s skipped (%s)", st, e)
    return out


@lru_cache(maxsize=2)
def load_mnli(split: str = "validation_matched", limit: int = 500) -> List[NLIExample]:
    """MNLI validation -- grades the NLI head's raw 3-class ability. General
    domain, but that's what the head is; the legal signal is measured by
    running the head inside `contractnli_entailment` instead."""
    ds = _require_datasets().load_dataset("nyu-mll/multi_nli", split=split)
    out: List[NLIExample] = []
    for row in ds:
        if limit and len(out) >= limit:
            break
        label = row["label"]
        if isinstance(label, int):
            if label < 0:
                continue
            label = _MNLI_LABELS.get(label, str(label))
        out.append(NLIExample(premise=row["premise"], hypothesis=row["hypothesis"], label=str(label)))
    logger.info("Loaded %d MNLI examples (%s).", len(out), split)
    return out
