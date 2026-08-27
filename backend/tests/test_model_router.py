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
        assert set(card.capabilities) <= {"generate", "embed", "rerank"}
        # a Class C provider is the only kind that may leave the perimeter
        if card.leaves_perimeter:
            assert card.hosting_class == HostingClass.C


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
