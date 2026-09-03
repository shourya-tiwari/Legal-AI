# backend/app/services/sensitivity/__init__.py
"""
Document sensitivity classification (docs/v2/AI_STACK.md "Hosting classes",
docs/v2/ARCHITECTURE.md security section).

The tier a document is assigned (`public` | `internal` | `confidential` |
`privileged`) is what the Model Router's Class-C gate keys on: a
`privileged` or `confidential` document is never routed to an external
provider. Before this milestone every call site passed `sensitivity="internal"`
implicitly, so the gate protected nothing.

Rule-based (Tier-0), same pattern as `services/risk_radar/rules.py` and the
NLP classifiers. A classical / transformer model (`DEEP_LEARNING.md`) is the
documented upgrade once labelled data exists; it slots in behind the same
`classify_sensitivity()` interface.
"""
from .classifier import (
    SensitivityAssessment,
    SensitivitySignal,
    classify_sensitivity,
    is_enabled,
)

__all__ = [
    "SensitivityAssessment",
    "SensitivitySignal",
    "classify_sensitivity",
    "is_enabled",
]
