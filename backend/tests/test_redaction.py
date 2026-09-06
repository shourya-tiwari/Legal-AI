"""
PII/PHI redaction gate (app/services/redaction.py, docs/v2/ARCHITECTURE.md
Security architecture item 3). Covers the regex floor, the GLiNER escalation
merge, and the fail-soft/disabled paths -- no network, entailment/ner calls
mocked at the module's own import of ner_extract.
"""
from __future__ import annotations

import pytest

from app.config import get_settings
from app.services.model_router import ModelRouterError
from app.services.model_router.types import HostingClass, NERResult
from app.services.redaction import redact_pii


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _fake_ner_result(entities):
    return NERResult(entities=entities, provider="local-ner", model="test-model",
                     hosting_class=HostingClass.B)


# --------------------------------------------------------------------------
# regex floor -- always on, no model required
# --------------------------------------------------------------------------

def test_regex_floor_masks_an_ssn(monkeypatch):
    monkeypatch.setattr("app.services.redaction.ner_extract", lambda *a, **k: _fake_ner_result([]))
    result = redact_pii("The tenant's SSN is 123-45-6789 for verification.")
    assert "123-45-6789" not in result.redacted_text
    assert "[REDACTED:SSN]" in result.redacted_text
    assert result.categories_found == {"ssn": 1}


def test_regex_floor_masks_email_and_phone(monkeypatch):
    monkeypatch.setattr("app.services.redaction.ner_extract", lambda *a, **k: _fake_ner_result([]))
    result = redact_pii("Contact jane.doe@example.com or (555) 123-4567 for questions.")
    assert "jane.doe@example.com" not in result.redacted_text
    assert "[REDACTED:EMAIL]" in result.redacted_text
    assert "[REDACTED:PHONE]" in result.redacted_text
    assert result.categories_found == {"email": 1, "phone": 1}


def test_regex_floor_masks_a_credit_card_number(monkeypatch):
    monkeypatch.setattr("app.services.redaction.ner_extract", lambda *a, **k: _fake_ner_result([]))
    result = redact_pii("Card on file: 4111111111111111.")
    assert "4111111111111111" not in result.redacted_text
    assert result.categories_found == {"credit_card": 1}


def test_no_pii_leaves_text_and_counts_empty(monkeypatch):
    monkeypatch.setattr("app.services.redaction.ner_extract", lambda *a, **k: _fake_ner_result([]))
    text = "Either party may terminate this Agreement with 30 days notice."
    result = redact_pii(text)
    assert result.redacted_text == text
    assert result.categories_found == {}


def test_empty_text_passes_through_without_calling_ner(monkeypatch):
    called = {"hit": False}

    def spy(*a, **k):
        called["hit"] = True
        return _fake_ner_result([])

    monkeypatch.setattr("app.services.redaction.ner_extract", spy)
    result = redact_pii("")
    assert result.redacted_text == ""
    assert result.categories_found == {}
    assert called["hit"] is False


# --------------------------------------------------------------------------
# GLiNER escalation -- unstructured PII no regex can catch
# --------------------------------------------------------------------------

def test_ner_escalation_masks_a_person_name(monkeypatch):
    # conftest.py defaults NER_ENABLED=false for the rest of the suite.
    monkeypatch.setenv("NER_ENABLED", "true")
    get_settings.cache_clear()
    monkeypatch.setattr(
        "app.services.redaction.ner_extract",
        lambda *a, **k: _fake_ner_result([{"text": "Jane Doe", "type": "person name", "score": 0.9}]),
    )
    result = redact_pii("The lease was signed by Jane Doe on the effective date.")
    assert "Jane Doe" not in result.redacted_text
    assert "[REDACTED:PERSON]" in result.redacted_text
    assert result.categories_found == {"person": 1}


def test_ner_escalation_masks_a_physical_address(monkeypatch):
    monkeypatch.setenv("NER_ENABLED", "true")
    get_settings.cache_clear()
    monkeypatch.setattr(
        "app.services.redaction.ner_extract",
        lambda *a, **k: _fake_ner_result(
            [{"text": "742 Evergreen Terrace", "type": "physical address", "score": 0.88}]
        ),
    )
    result = redact_pii("Notices shall be sent to 742 Evergreen Terrace.")
    assert "742 Evergreen Terrace" not in result.redacted_text
    assert result.categories_found == {"address": 1}


def test_regex_and_ner_findings_combine(monkeypatch):
    monkeypatch.setenv("NER_ENABLED", "true")
    get_settings.cache_clear()
    monkeypatch.setattr(
        "app.services.redaction.ner_extract",
        lambda *a, **k: _fake_ner_result([{"text": "Jane Doe", "type": "person name", "score": 0.9}]),
    )
    result = redact_pii("Jane Doe can be reached at jane.doe@example.com.")
    assert result.categories_found == {"person": 1, "email": 1}


def test_ner_escalation_ignores_an_unmapped_label(monkeypatch):
    # A GLiNER label outside _PII_NER_LABELS/_NER_CATEGORY_MAP should never
    # happen given the labels we pass, but the merge must not crash if it did.
    monkeypatch.setenv("NER_ENABLED", "true")
    get_settings.cache_clear()
    monkeypatch.setattr(
        "app.services.redaction.ner_extract",
        lambda *a, **k: _fake_ner_result([{"text": "some org", "type": "organization", "score": 0.7}]),
    )
    result = redact_pii("A clause mentioning some org and nothing else sensitive.")
    assert result.categories_found == {}
    assert "some org" in result.redacted_text


# --------------------------------------------------------------------------
# fail-soft + the enabled/disabled switch
# --------------------------------------------------------------------------

def test_ner_unavailable_falls_back_to_regex_only(monkeypatch):
    monkeypatch.setenv("NER_ENABLED", "true")
    get_settings.cache_clear()

    def raise_router_error(*a, **k):
        raise ModelRouterError("no NER provider available")

    monkeypatch.setattr("app.services.redaction.ner_extract", raise_router_error)
    result = redact_pii("Email me at jane.doe@example.com about Jane Doe's lease.")
    assert "[REDACTED:EMAIL]" in result.redacted_text
    assert "Jane Doe" in result.redacted_text  # NER never ran; regex can't catch a bare name
    assert result.categories_found == {"email": 1}


def test_redaction_disabled_returns_text_unchanged(monkeypatch):
    monkeypatch.setenv("PII_REDACTION_ENABLED", "false")
    get_settings.cache_clear()
    called = {"hit": False}

    def spy(*a, **k):
        called["hit"] = True
        return _fake_ner_result([])

    monkeypatch.setattr("app.services.redaction.ner_extract", spy)
    text = "SSN 123-45-6789, email jane.doe@example.com"
    result = redact_pii(text)
    assert result.redacted_text == text
    assert result.categories_found == {}
    assert called["hit"] is False
