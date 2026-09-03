"""
Model Router (docs/v2/AI_STACK.md, ROADMAP Phase 5): the provider-agnostic
routing layer. These tests exercise the interface, the policy engine, hosting
classes, Class C gating, and the back-compatible generate_content/embed_content
shims -- with no network access.
"""
from __future__ import annotations

import numpy as np
import pytest

from app.config import get_settings
from app.services.model_router import (
    HostingClass,
    ModelRouterError,
    SensitivityTier,
    embed_content,
    generate_content,
    get_registry,
    rerank,
    reset_registry_cache,
)
from app.services.model_router.policy import RoutingPolicy, get_policy
from app.services.model_router.router import get_router
from app.services.model_router.types import EmbedRequest, GenerateRequest, RerankRequest


@pytest.fixture(autouse=True)
def _fresh_router_caches():
    get_settings.cache_clear()
    get_policy.cache_clear()
    get_router.cache_clear()
    reset_registry_cache()
    yield
    get_settings.cache_clear()
    get_policy.cache_clear()
    get_router.cache_clear()
    reset_registry_cache()


# --------------------------------------------------------------------------
# embeddings: self-hosted by default, no Gemini
# --------------------------------------------------------------------------

def test_embed_content_uses_class_a_hashing_provider_by_default():
    result = embed_content(["security deposit refund", "termination notice period"])
    assert len(result.embeddings) == 2
    assert result.hosting_class == HostingClass.A
    assert result.provider == "hashing-embed"
    dim = len(result.embeddings[0].values)
    assert dim > 0
    # deterministic
    again = embed_content(["security deposit refund"])
    assert again.embeddings[0].values == result.embeddings[0].values


def test_hashing_embeddings_are_l2_normalized_and_capture_lexical_overlap():
    v_a = np.array(embed_content(["the tenant shall pay a security deposit"]).embeddings[0].values)
    v_b = np.array(embed_content(["a security deposit is paid by the tenant"]).embeddings[0].values)
    v_c = np.array(embed_content(["bananas grow in tropical climates"]).embeddings[0].values)
    assert np.isclose(np.linalg.norm(v_a), 1.0, atol=1e-5)
    assert float(v_a @ v_b) > float(v_a @ v_c)


# --------------------------------------------------------------------------
# reranking
# --------------------------------------------------------------------------

def test_rerank_lexical_orders_by_query_overlap():
    docs = [
        "Force majeure clauses excuse performance during extraordinary events.",
        "The security deposit shall be returned within 21 days of move-out.",
        "Confidential information must not be disclosed to third parties.",
    ]
    result = rerank("how long to return the security deposit", docs)
    assert result.hosting_class == HostingClass.A
    assert result.ranking[0] == 1


# --------------------------------------------------------------------------
# generation routing + Class C gating
# --------------------------------------------------------------------------

def test_generate_raises_cleanly_when_no_self_hosted_llm_and_external_disabled(monkeypatch):
    monkeypatch.setenv("EXTERNAL_PROVIDERS_ENABLED", "false")
    monkeypatch.setenv("LLM_BASE_URL", "")
    get_settings.cache_clear(); get_policy.cache_clear(); get_router.cache_clear()

    with pytest.raises(ModelRouterError) as exc:
        generate_content("Rewrite this clause.", task="clause_rewrite")
    assert "No provider available" in str(exc.value) or "failed" in str(exc.value)


def test_privileged_sensitivity_never_gets_a_class_c_candidate(monkeypatch):
    monkeypatch.setenv("EXTERNAL_PROVIDERS_ENABLED", "true")
    get_settings.cache_clear(); get_policy.cache_clear()
    policy = get_policy()

    pub = policy.candidates("clause_rewrite", SensitivityTier.PUBLIC)
    priv = policy.candidates("clause_rewrite", SensitivityTier.PRIVILEGED)
    conf = policy.candidates("clause_rewrite", SensitivityTier.CONFIDENTIAL)

    assert "gemini" in pub          # allowed for public
    assert "gemini" not in priv     # never for privileged
    assert "gemini" not in conf     # never for confidential


def test_strict_local_only_removes_class_c_even_for_public(monkeypatch):
    monkeypatch.setenv("EXTERNAL_PROVIDERS_ENABLED", "true")
    monkeypatch.setenv("STRICT_LOCAL_ONLY", "true")
    get_settings.cache_clear(); get_policy.cache_clear()

    assert "gemini" not in get_policy().candidates("qa", SensitivityTier.PUBLIC)


def test_class_c_is_never_in_the_plain_chain_only_appended_conditionally():
    # The policy's raw chain for a generate task is Class A/B only.
    policy = RoutingPolicy(
        {
            "class_c_allowed_tiers": ["public"],
            "tasks": {"x": {"capability": "generate", "chain": ["local-llm"], "class_c": ["gemini"]}},
        }
    )
    # class_c never leaks into a sensitive-tier resolution
    assert policy.candidates("x", SensitivityTier.PRIVILEGED) == ["local-llm"]


def test_generate_routes_to_class_c_when_enabled_and_public(monkeypatch):
    monkeypatch.setenv("EXTERNAL_PROVIDERS_ENABLED", "true")
    monkeypatch.setenv("LLM_BASE_URL", "")  # no self-hosted LLM -> falls through
    get_settings.cache_clear(); get_policy.cache_clear(); get_router.cache_clear()
    reset_registry_cache()

    registry = get_registry()
    if "gemini" not in registry:
        pytest.skip("providers-external not installed in this environment")

    captured = {}

    def fake_generate(req):
        from app.services.model_router.types import GenerateResult
        captured["task"] = req.task
        return GenerateResult(text="ok", provider="gemini", model="gemini-x",
                              hosting_class=HostingClass.C)

    monkeypatch.setattr(registry["gemini"], "generate", fake_generate)
    monkeypatch.setattr(registry["gemini"], "is_available", lambda: True)

    out = generate_content("Summarize.", task="qa", sensitivity="public")
    assert out == "ok"
    assert captured["task"] == "qa"


# --------------------------------------------------------------------------
# provider interface
# --------------------------------------------------------------------------

def test_every_registered_provider_implements_the_interface():
    from app.services.model_router.base import ModelProvider

    for name, provider in get_registry().items():
        assert isinstance(provider, ModelProvider), name
        card = provider.describe()
        assert card.name
        assert card.hosting_class in HostingClass
        assert set(card.capabilities) <= {"generate", "embed", "rerank", "entail", "ner"}
        # a Class C provider is the only kind that may leave the perimeter
        if card.leaves_perimeter:
            assert card.hosting_class == HostingClass.C


# --------------------------------------------------------------------------
# self-hosted reranker server (Phase 5/6): local-rerank-remote
# --------------------------------------------------------------------------

def test_rerank_remote_provider_is_registered_and_implements_the_interface():
    from app.services.model_router.base import ModelProvider

    provider = get_registry()["local-rerank-remote"]
    assert isinstance(provider, ModelProvider)
    card = provider.describe()
    assert card.capabilities == ["rerank"]
    assert card.hosting_class == HostingClass.B
    assert card.leaves_perimeter is False


def test_rerank_remote_is_unavailable_without_a_base_url_and_falls_to_class_a(monkeypatch):
    monkeypatch.setenv("RERANKER_BASE_URL", "")
    get_settings.cache_clear(); get_policy.cache_clear(); get_router.cache_clear()
    reset_registry_cache()

    assert get_registry()["local-rerank-remote"].is_available() is False
    # the router walks the chain and lands on the Class A lexical reranker
    result = rerank("return the security deposit", ["deposit returned in 21 days", "force majeure"])
    assert result.hosting_class == HostingClass.A
    assert result.provider == "lexical-rerank"


def test_rerank_remote_parses_a_tei_rerank_response(monkeypatch):
    monkeypatch.setenv("RERANKER_BASE_URL", "http://tei-rerank:80")
    get_settings.cache_clear(); get_policy.cache_clear(); get_router.cache_clear()
    reset_registry_cache()

    import app.services.model_router.providers.openai_compat as oc

    class _Resp:
        def raise_for_status(self): ...
        def json(self):
            # TEI /rerank shape: unordered [{index, score}, ...]
            return [{"index": 0, "score": 0.11}, {"index": 2, "score": 0.97}, {"index": 1, "score": 0.42}]

    monkeypatch.setattr(oc.httpx, "post", lambda *a, **k: _Resp())

    result = rerank("q", ["doc a", "doc b", "doc c"], top_k=2)
    assert result.hosting_class == HostingClass.B
    assert result.provider == "local-rerank-remote"
    assert result.ranking == [2, 1]           # best-first, truncated to top_k
    assert result.scores == [0.97, 0.42]


def test_policy_chain_order_puts_the_dedicated_server_first():
    policy = get_policy()
    for task in ("embed_query", "embed_corpus"):
        chain = policy.candidates(task, SensitivityTier.INTERNAL)
        assert chain[0] == "local-embed-remote"
        assert chain[-1] == "local-embed-hash"
    rerank_chain = policy.candidates("rerank", SensitivityTier.INTERNAL)
    assert rerank_chain[0] == "local-rerank-remote"
    assert rerank_chain[-1] == "local-rerank-lexical"


# --------------------------------------------------------------------------
# routing-decision telemetry (model_calls table) -- fail-soft
# --------------------------------------------------------------------------

def test_model_call_logging_writes_a_row_and_is_fail_soft(client, db_session, monkeypatch):
    # `client` runs init_db() so the model_calls table exists.
    from app.db_models import ModelCall

    monkeypatch.setenv("MODEL_CALL_LOGGING", "true")
    get_settings.cache_clear()

    before = db_session.query(ModelCall).count()
    embed_content(["a security deposit clause"])
    rows = db_session.query(ModelCall).order_by(ModelCall.id.desc()).all()
    assert len(rows) == before + 1
    assert rows[0].provider == "hashing-embed"
    assert rows[0].hosting_class == "A"
    assert rows[0].ok is True
    assert rows[0].task == "embed_corpus"


def test_model_call_logging_can_be_disabled(client, db_session, monkeypatch):
    from app.db_models import ModelCall

    monkeypatch.setenv("MODEL_CALL_LOGGING", "false")
    get_settings.cache_clear()

    before = db_session.query(ModelCall).count()
    embed_content(["another clause"])
    assert db_session.query(ModelCall).count() == before


# --------------------------------------------------------------------------
# Phase 6: entail (NLI) + ner capabilities, and the escalation ladder
# --------------------------------------------------------------------------

def test_entail_and_ner_providers_are_registered_and_typed():
    from app.services.model_router.base import ModelProvider

    reg = get_registry()
    assert reg["local-nli"].describe().capabilities == ["entail"]
    assert reg["local-nli"].describe().hosting_class == HostingClass.A
    assert reg["local-ner"].describe().capabilities == ["ner"]
    for name in ("local-nli", "local-ner", "local-llm-large"):
        assert isinstance(reg[name], ModelProvider), name


def test_verify_nli_and_ner_extract_policy_chains():
    policy = get_policy()
    assert policy.candidates("verify_nli", SensitivityTier.INTERNAL) == ["local-nli"]
    assert policy.candidates("ner_extract", SensitivityTier.INTERNAL) == ["local-ner"]
    # entail/ner never get a Class C candidate, even for public
    assert policy.candidates("verify_nli", SensitivityTier.PUBLIC) == ["local-nli"]


def test_entailment_raises_cleanly_when_the_head_is_disabled(monkeypatch):
    monkeypatch.setenv("NLI_ENABLED", "false")
    get_settings.cache_clear(); get_policy.cache_clear(); get_router.cache_clear()
    reset_registry_cache()
    from app.services.model_router import entailment

    with pytest.raises(ModelRouterError):
        entailment([("a premise", "a hypothesis")])


def test_hard_flag_prepends_the_escalation_model(monkeypatch):
    monkeypatch.setenv("EXTERNAL_PROVIDERS_ENABLED", "false")
    get_settings.cache_clear(); get_policy.cache_clear()
    policy = get_policy()

    normal = policy.candidates("clause_rewrite", SensitivityTier.INTERNAL, hard=False)
    escalated = policy.candidates("clause_rewrite", SensitivityTier.INTERNAL, hard=True)
    assert normal == ["local-llm"]
    assert escalated == ["local-llm-large", "local-llm"]


def test_hard_escalation_target_is_never_class_c(monkeypatch):
    monkeypatch.setenv("EXTERNAL_PROVIDERS_ENABLED", "true")
    get_settings.cache_clear(); get_policy.cache_clear()
    escalated = get_policy().candidates("qa", SensitivityTier.PUBLIC, hard=True)
    # gemini may be appended (public tier), but only AFTER the self-hosted chain
    assert escalated[0] == "local-llm-large"
    assert escalated.index("local-llm-large") < escalated.index("local-llm")
    if "gemini" in escalated:
        assert escalated.index("gemini") == len(escalated) - 1


def test_registry_runs_without_external_providers(monkeypatch):
    # Simulate the on-prem / air-gapped install: no gemini provider.
    import app.services.model_router.registry as reg

    monkeypatch.setattr(reg, "load_gemini_provider", lambda: None)
    reset_registry_cache()

    registry = reg.get_registry()
    assert "gemini" not in registry
    # embeddings + reranking still resolve to local providers
    assert embed_content(["hello world"]).hosting_class == HostingClass.A
    assert rerank("q", ["a doc", "another"]).hosting_class == HostingClass.A
