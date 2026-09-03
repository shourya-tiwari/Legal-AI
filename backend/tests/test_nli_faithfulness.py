"""
Phase 6: the real NLI faithfulness head (app/services/model_router/providers/
nli_local.py) and the Verifier rewrite (app/agents/verifier.py).

These tests download a ~440 MB transformers model on first run, so they are
gated: skipped entirely when `transformers`/`torch` aren't installed, and they
flip NLI_ENABLED on (conftest.py turns it off for the rest of the suite).
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.filterwarnings("ignore")

transformers = pytest.importorskip("transformers")
torch = pytest.importorskip("torch")


@pytest.fixture(autouse=True)
def _enable_nli(monkeypatch):
    monkeypatch.setenv("NLI_ENABLED", "true")
    from app.config import get_settings
    from app.services.model_router.policy import get_policy
    from app.services.model_router.registry import reset_registry_cache
    from app.services.model_router.router import get_router

    get_settings.cache_clear()
    get_policy.cache_clear()
    get_router.cache_clear()
    reset_registry_cache()
    yield
    get_settings.cache_clear()


def test_entailment_capability_classifies_the_three_relations():
    from app.services.model_router import entailment

    result = entailment([
        ("The deposit is returned within 21 days of move-out.",
         "The deposit comes back within three weeks."),                       # entailment
        ("The deposit is returned within 21 days.",
         "The landlord keeps the entire deposit."),                            # contradiction
        ("This Agreement is governed by Delaware law.",
         "The parties meet every Tuesday."),                                   # neutral
    ])
    assert result.provider == "local-nli"
    assert result.hosting_class.value == "A"
    assert result.labels[0] == "entailment"
    assert result.labels[1] == "contradiction"
    assert result.labels[2] == "neutral"


def test_nli_head_beats_lexical_overlap_on_the_faithfulness_gold_set():
    from app.agents.verifier import _lexical_overlap_faithfulness, _nli_faithfulness
    from app.eval.gold_set import FAITHFULNESS_GOLD

    nli_correct = sum(
        _nli_faithfulness(ex["summary"], ex["sources"])[0] == ex["is_faithful"]
        for ex in FAITHFULNESS_GOLD
    )
    lex_correct = sum(
        _lexical_overlap_faithfulness(ex["summary"], ex["sources"]) == ex["is_faithful"]
        for ex in FAITHFULNESS_GOLD
    )
    n = len(FAITHFULNESS_GOLD)
    # absolute floor + strictly better than the stand-in it replaces
    assert nli_correct >= max(lex_correct + 1, int(0.85 * n)), (
        f"NLI head {nli_correct}/{n} did not clearly beat lexical {lex_correct}/{n}"
    )


def test_verifier_flags_a_fabricated_claim_with_method_nli():
    from app.agents.state import CaseState
    from app.agents.verifier import run_verifier

    state = CaseState(
        document_id=1, org_id=1,
        summary="The security deposit is returned within 90 days of move-out.",
        summary_citation_count=1,
        research_citations={1: [{"text": "The landlord shall return the security deposit "
                                         "within 21 days after the tenant vacates.",
                                 "topic": "landlord_tenant", "citation": None}]},
    )
    update = run_verifier(state)
    assert update["faithfulness_method"] == "nli"
    assert update["faithfulness_ok"] is False
    assert update["needs_human_review"] is True
    assert update["unsupported_claims"]


def test_verifier_passes_a_faithful_summary():
    from app.agents.state import CaseState
    from app.agents.verifier import run_verifier

    state = CaseState(
        document_id=1, org_id=1,
        summary="Either party can end the agreement with sixty days written notice.",
        summary_citation_count=1,
        research_citations={1: [{"text": "This Agreement may be terminated by either party "
                                         "upon sixty (60) days prior written notice.",
                                 "topic": "termination", "citation": None}]},
    )
    update = run_verifier(state)
    assert update["faithfulness_method"] == "nli"
    assert update["faithfulness_ok"] is True
