"""
Rule-based document sensitivity classifier (app/services/sensitivity/).
Pure regex -- no network, no models.
"""
from __future__ import annotations

import pytest

from app.services.sensitivity import classify_sensitivity


@pytest.mark.parametrize(
    "text, expected",
    [
        ("This memorandum is protected by the attorney-client privilege.", "privileged"),
        ("Prepared in anticipation of litigation; attorney work product.", "privileged"),
        ("PRIVILEGED AND CONFIDENTIAL — do not forward.", "privileged"),
        ("MUTUAL NON-DISCLOSURE AGREEMENT between the parties.", "confidential"),
        ("The Receiving Party shall keep such trade secret information secret.", "confidential"),
        ("This information is proprietary and confidential to the Company.", "confidential"),
        ("FOR IMMEDIATE RELEASE — Acme Corp announces earnings.", "public"),
        ("As disclosed in our Form 10-K filed with the SEC.", "public"),
        ("This Master Services Agreement governs the provision of consulting services.", "internal"),
        ("", "internal"),
    ],
)
def test_tier_markers(text, expected):
    assert classify_sensitivity(text).tier == expected


def test_pii_density_bumps_to_confidential():
    text = "SSN 123-45-6789. Federal EIN 12-3456789. Date of birth on file."
    assert classify_sensitivity(text).tier == "confidential"


def test_a_single_confidentiality_clause_stays_internal():
    # A normal contract with one Confidentiality heading must NOT tip over.
    text = (
        "5. Confidentiality. Each party shall protect the other party's confidential "
        "information using reasonable care. This Section survives termination."
    )
    assert classify_sensitivity(text).tier == "internal"


def test_repeated_confidential_mentions_do_bump():
    text = "confidential " * 5 + "material provided under this agreement."
    assert classify_sensitivity(text).tier == "confidential"


def test_public_marker_does_not_override_a_sensitivity_marker():
    text = "Press release draft — PRIVILEGED AND CONFIDENTIAL, prepared by outside counsel."
    assert classify_sensitivity(text).tier == "privileged"


def test_filename_hint():
    a = classify_sensitivity("Ordinary contract text with no markers.", filename="2024_NDA_acme.pdf")
    assert a.tier == "confidential"
    assert any(s.category == "filename" for s in a.signals)


def test_rationale_and_signals_are_populated():
    a = classify_sensitivity("This is subject to the attorney-client privilege.")
    assert a.tier == "privileged"
    assert a.rationale
    assert a.source == "auto"
    assert a.signals and a.signals[0].category == "privilege"


def test_disabled_returns_the_default(monkeypatch):
    monkeypatch.setenv("SENSITIVITY_ENABLED", "false")
    from app.config import get_settings

    get_settings.cache_clear()
    try:
        a = classify_sensitivity("attorney-client privilege everywhere")
        assert a.tier == "internal"
        assert "disabled" in a.rationale
    finally:
        get_settings.cache_clear()
