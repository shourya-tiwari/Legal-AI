"""
Phase 6: GLiNER zero-shot NER (providers/gliner_local.py) merged into
nlp/entities.py. Model-gated -- skipped without `gliner` installed.
"""
from __future__ import annotations

import pytest

pytest.importorskip("gliner")


@pytest.fixture(autouse=True)
def _enable_ner(monkeypatch):
    monkeypatch.setenv("NER_ENABLED", "true")
    from app.config import get_settings
    from app.services.model_router.registry import reset_registry_cache
    from app.services.nlp.entities import _ner_available

    get_settings.cache_clear()
    reset_registry_cache()
    _ner_available.cache_clear()
    yield
    get_settings.cache_clear()
    _ner_available.cache_clear()


def test_gliner_provider_extracts_typed_spans():
    from app.services.model_router import ner_extract

    r = ner_extract(
        "Acme Corp and Globex LLC agree that this Agreement is governed by the laws "
        "of the State of Delaware; a fee of $50,000 is payable within 30 days.",
        ["organization", "monetary amount", "duration", "governing law jurisdiction"],
    )
    assert r.provider == "local-ner"
    assert r.hosting_class.value == "B"
    types = {e["type"] for e in r.entities}
    assert "governing law jurisdiction" in types
    assert "monetary amount" in types


def test_entities_merges_gliner_with_regex_floor():
    from app.services.nlp.entities import extract_entities

    ents = extract_entities(
        "The parties, Acme Corp and Globex LLC, agree the deposit of $2,000 is due "
        "within 21 days under the laws of the State of California."
    )
    by_type = {}
    for e in ents:
        by_type.setdefault(e.type, []).append(e.text)
    # regex floor
    assert any("2,000" in t for t in by_type.get("money", []))
    assert "California" in by_type.get("jurisdiction", []) or any(
        "California" in t for t in by_type.get("jurisdiction", [])
    )
    # gliner adds at least one party/duration
    assert by_type.get("party") or by_type.get("duration")
