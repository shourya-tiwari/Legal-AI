"""
The provider-isolation contract (docs/v2/AI_STACK.md, ROADMAP Phase 5):

    No module outside app/services/model_router/providers/ may import a
    model-provider SDK.

This is the mechanical guarantee behind "no vendor in the business logic" --
a service that wants a model calls the Model Router by task/capability; only
a provider adapter touches a vendor SDK. If this test fails, a vendor import
leaked into the app; move the call behind the Model Router.
"""
from __future__ import annotations

import ast
import pathlib

import pytest

APP_ROOT = pathlib.Path(__file__).resolve().parents[1] / "app"
PROVIDERS_DIR = APP_ROOT / "services" / "model_router" / "providers"

# Top-level package names that are model-provider SDKs.
FORBIDDEN_ROOTS = {
    "google",            # google.genai
    "openai",
    "anthropic",
    "cohere",
    "mistralai",
    "vllm",
    "sentence_transformers",
    "transformers",
    "gliner",
    "fastcoref",          # not shipped (torch<2.6 / CVE blocker) -- guard is forward-looking
    "litellm",
    "ollama",
}


def _imported_roots(tree: ast.AST):
    roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module:
                roots.add(node.module.split(".")[0])
    return roots


def _app_modules_outside_providers():
    for path in APP_ROOT.rglob("*.py"):
        if PROVIDERS_DIR in path.parents:
            continue
        yield path


def test_no_provider_sdk_imported_outside_providers_package():
    violations = []
    for path in _app_modules_outside_providers():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        leaked = _imported_roots(tree) & FORBIDDEN_ROOTS
        if leaked:
            rel = path.relative_to(APP_ROOT.parent)
            violations.append(f"{rel}: imports {sorted(leaked)}")

    assert not violations, (
        "Model-provider SDK imported outside app/services/model_router/providers/:\n  "
        + "\n  ".join(violations)
        + "\n\nRoute the call through the Model Router instead (docs/v2/AI_STACK.md)."
    )


def test_providers_package_is_the_only_google_genai_importer():
    gemini_adapter = PROVIDERS_DIR / "gemini.py"
    assert gemini_adapter.exists()
    tree = ast.parse(gemini_adapter.read_text(encoding="utf-8"))
    assert "google" in _imported_roots(tree), "gemini.py should be the one place google.genai is imported"
