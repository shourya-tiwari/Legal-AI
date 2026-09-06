"""
scripts/check_sbom_allowlist.py -- the build-level complement to
tests/test_provider_isolation.py's source-level import scan (docs/v2/
ROADMAP.md Phase 7 "Build & supply chain"). This tests the pure-Python
allowlist logic directly; the actual "does the built Docker image have
google-genai installed" question was verified by hand against a real
`docker build` of backend/Dockerfile (both the `core` and `external`
profiles) -- not repeatable in CI without a Docker-in-Docker runner, so
that's the one part of this feature this suite can't re-prove on every run.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from check_sbom_allowlist import FORBIDDEN_DISTRIBUTIONS, check, installed_distributions  # noqa: E402


def test_forbidden_distributions_matches_provider_isolation_roots():
    """Kept in sync by hand with test_provider_isolation.py's FORBIDDEN_ROOTS
    -- this test at least catches one list being edited without the other."""
    from tests.test_provider_isolation import FORBIDDEN_ROOTS

    # A PyPI distribution name and its import root usually match, except:
    # hyphens in the dist name become underscores in the import name
    # (sentence-transformers -> sentence_transformers), and google-genai's
    # import root is just its top-level namespace package, "google".
    expected_roots = {
        "google" if name == "google-genai" else name.replace("-", "_")
        for name in FORBIDDEN_DISTRIBUTIONS
    }
    assert expected_roots == FORBIDDEN_ROOTS


def test_core_profile_fails_if_a_forbidden_package_were_installed(monkeypatch):
    import check_sbom_allowlist

    monkeypatch.setattr(check_sbom_allowlist, "installed_distributions",
                        lambda: {"fastapi": "0.116.1", "google-genai": "1.32.0"})
    violations = check("core")
    assert violations == [("google-genai", "1.32.0")]


def test_core_profile_passes_when_nothing_forbidden_is_installed(monkeypatch):
    import check_sbom_allowlist

    monkeypatch.setattr(check_sbom_allowlist, "installed_distributions",
                        lambda: {"fastapi": "0.116.1", "numpy": "2.2.6"})
    assert check("core") == []


def test_external_profile_skips_the_check_entirely(monkeypatch):
    import check_sbom_allowlist

    monkeypatch.setattr(check_sbom_allowlist, "installed_distributions",
                        lambda: {"google-genai": "1.32.0", "openai": "1.0.0"})
    assert check("external") == []


def test_installed_distributions_reflects_the_real_interpreter():
    # A real, always-installed package proves this reads actual metadata,
    # not a fixture -- fastapi is a hard requirement of the app itself.
    installed = installed_distributions()
    assert "fastapi" in installed
    assert installed["fastapi"]
