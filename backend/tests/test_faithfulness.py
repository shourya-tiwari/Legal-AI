"""
app/services/faithfulness.py -- the shared faithfulness (hallucination)
check extracted from app/agents/verifier.py so app/services/chatbot.py's
`/api/ask` path can reuse the exact same logic. These tests exercise the
public `check_faithfulness()` entrypoint against a controllable fake
`entailment()`, covering both the real-NLI path and the lexical-overlap
fallback -- see tests/test_nli_faithfulness.py for the real (non-mocked)
NLI head, gated on `transformers` being installed.
"""
from __future__ import annotations

from app.services.faithfulness import (
    FaithfulnessResult,
    _lexical_overlap_faithfulness,
    check_faithfulness,
)
from app.services.model_router.types import EntailResult, HostingClass


def _fake_entail_result(labels: list[str], scores: list[float]) -> EntailResult:
    return EntailResult(labels=labels, scores=scores, provider="local-nli",
                        model="test-model", hosting_class=HostingClass.A)


def test_check_faithfulness_uses_nli_when_available(monkeypatch):
    monkeypatch.setattr(
        "app.services.faithfulness.entailment",
        lambda pairs: _fake_entail_result(["entailment"] * len(pairs), [0.9] * len(pairs)),
    )

    result = check_faithfulness(
        "The deposit is returned within twenty-one days of move-out.",
        ["The landlord shall return the security deposit within 21 days after the tenant vacates."],
    )

    assert isinstance(result, FaithfulnessResult)
    assert result.method == "nli"
    assert result.ok is True
    assert result.unsupported_claims == []


def test_check_faithfulness_flags_a_contradicted_claim_via_nli(monkeypatch):
    monkeypatch.setattr(
        "app.services.faithfulness.entailment",
        lambda pairs: _fake_entail_result(["contradiction"] * len(pairs), [0.9] * len(pairs)),
    )

    result = check_faithfulness(
        "The deposit is returned within ninety days of move-out.",
        ["The landlord shall return the security deposit within 21 days after the tenant vacates."],
    )

    assert result.method == "nli"
    assert result.ok is False
    assert result.unsupported_claims


def test_check_faithfulness_falls_back_to_lexical_when_nli_unavailable(monkeypatch):
    from app.services.model_router import ModelRouterError

    def raise_unavailable(pairs):
        raise ModelRouterError("no entail provider configured")

    monkeypatch.setattr("app.services.faithfulness.entailment", raise_unavailable)

    result = check_faithfulness(
        "Security deposits are refundable less lawful deductions.",
        ["Security deposits are refundable less lawful deductions for damages."],
    )

    assert result.method == "lexical_fallback"
    assert result.ok is True
    assert result.unsupported_claims == []  # the lexical fallback never populates this


def test_check_faithfulness_lexical_fallback_flags_unrelated_text(monkeypatch):
    from app.services.model_router import ModelRouterError

    def raise_unavailable(pairs):
        raise ModelRouterError("no entail provider configured")

    monkeypatch.setattr("app.services.faithfulness.entailment", raise_unavailable)

    result = check_faithfulness(
        "Bananas grow on trees in tropical climates.",
        ["Security deposits are refundable less lawful deductions for damages."],
    )

    assert result.method == "lexical_fallback"
    assert result.ok is False


def test_check_faithfulness_never_raises_when_no_sources():
    # No sources to check against -- both paths treat this as "nothing to
    # verify" rather than a failure (matches the pre-extraction behavior).
    result = check_faithfulness("Any text at all.", [])
    assert result.ok is True


def test_lexical_overlap_faithfulness_true_with_shared_vocabulary():
    assert _lexical_overlap_faithfulness(
        "Security deposits are refundable less lawful deductions.",
        ["Security deposits are refundable less lawful deductions for damages."],
    ) is True


def test_lexical_overlap_faithfulness_false_with_no_shared_vocabulary():
    assert _lexical_overlap_faithfulness(
        "Bananas grow on trees in tropical climates.",
        ["Security deposits are refundable less lawful deductions for damages."],
    ) is False
