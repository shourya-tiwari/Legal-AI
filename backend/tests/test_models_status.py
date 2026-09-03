"""
GET /api/models/status -- the operator's view of the Model Router's provider
layer (docs/v2/AI_STACK.md, ROADMAP Phase 5/7 "Model status panel").
"""
from __future__ import annotations


def test_models_status_lists_the_class_a_floor_providers(client):
    resp = client.get("/api/models/status")
    assert resp.status_code == 200
    body = resp.json()

    names = {p["name"] for p in body["providers"]}
    # The always-available Class A providers must always be present + available.
    assert "local-embed-hash" in names
    assert "local-rerank-lexical" in names

    by_name = {p["name"]: p for p in body["providers"]}
    assert by_name["local-embed-hash"]["available"] is True
    assert by_name["local-embed-hash"]["hosting_class"] == "A"
    assert by_name["local-rerank-lexical"]["available"] is True

    assert isinstance(body["policy_version"], int)
    assert "external_providers_enabled" in body
    assert "strict_local_only" in body


def test_models_status_every_entry_has_the_documented_shape(client):
    body = client.get("/api/models/status").json()
    for p in body["providers"]:
        assert set(p) >= {
            "name", "hosting_class", "capabilities", "available",
            "leaves_perimeter", "models", "note",
        }
        assert p["hosting_class"] in {"A", "B", "C"}
        assert set(p["capabilities"]) <= {"generate", "embed", "rerank"}
        # only a Class C provider may leave the deployment perimeter
        if p["leaves_perimeter"]:
            assert p["hosting_class"] == "C"


def test_models_status_shows_the_self_hosted_server_providers_unavailable_offline(client):
    # Nothing served in tests -> the TEI/Ollama-backed providers register but
    # report themselves unavailable (no *_BASE_URL configured).
    by_name = {p["name"]: p for p in client.get("/api/models/status").json()["providers"]}
    assert by_name["local-llm"]["available"] is False
    assert by_name["local-embed-remote"]["available"] is False
    assert by_name["local-rerank-remote"]["available"] is False
    assert by_name["local-rerank-remote"]["capabilities"] == ["rerank"]
