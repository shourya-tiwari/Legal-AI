from app.services.risk_radar.rules import (
    RISK_CATEGORIES,
    RISK_CATEGORY_NAMES,
    RISKY_TERMS,
    find_keyword_flags,
    normalize_text,
)


def test_normalize_text_strips_punctuation_and_lowercases():
    assert normalize_text("Indemnify, and Hold-Harmless!") == "indemnify and holdharmless"


def test_find_keyword_flags_detects_known_risky_term():
    clause = "The Tenant shall indemnify the Landlord against all claims."
    flags = find_keyword_flags(clause, RISKY_TERMS)

    terms = {f["term"] for f in flags}
    assert "indemnify" in terms
    assert all("predefined_explanation" in f for f in flags)


def test_find_keyword_flags_no_match_returns_empty_list():
    clause = "This is a perfectly ordinary sentence about the weather."
    flags = find_keyword_flags(clause, RISKY_TERMS)

    assert flags == []


def test_find_keyword_flags_matches_multi_word_terms():
    clause = "Failure to pay triggers a late fee under this agreement."
    flags = find_keyword_flags(clause, RISKY_TERMS)

    terms = {f["term"] for f in flags}
    assert "late fee" in terms


def test_find_keyword_flags_does_not_match_substrings_across_word_boundaries():
    # "as is" should not match inside "classic" / "asian" etc.
    clause = "This is a classic asian dish description with no risky terms."
    flags = find_keyword_flags(clause, RISKY_TERMS)

    terms = {f["term"] for f in flags}
    assert "as is" not in terms


def test_find_keyword_flags_matches_the_hyphenated_non_compete_term():
    # Regression test for a real bug (LEARNING_LOG.md #52): normalize_text()
    # strips the hyphen from clause text ("non-compete" -> "noncompete") but
    # the un-normalized term still searched for the literal hyphen, so this
    # term could never match anything -- confirmed it's the only hyphenated
    # entry in RISKY_TERMS, fixed by normalizing the term the same way.
    clause = "This non-compete restricts the Employee from working in the industry."
    flags = find_keyword_flags(clause, RISKY_TERMS)

    terms = {f["term"] for f in flags}
    assert "non-compete" in terms


# --------------------------------------------------------------------------
# RISK_CATEGORIES -- the Risk Dashboard's category taxonomy
# --------------------------------------------------------------------------

def test_every_risky_term_has_exactly_one_category():
    assert set(RISKY_TERMS) == set(RISK_CATEGORIES)


def test_risk_category_names_matches_the_distinct_category_values():
    assert RISK_CATEGORY_NAMES == sorted(set(RISK_CATEGORIES.values()))
