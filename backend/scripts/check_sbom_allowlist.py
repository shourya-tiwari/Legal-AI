#!/usr/bin/env python
"""
SBOM allowlist enforcement (docs/v2/ROADMAP.md Phase 7 "Build & supply
chain", docs/v2/ARCHITECTURE.md Security architecture item 2).

`tests/test_provider_isolation.py` proves no *source file* outside
`app/services/model_router/providers/` imports a commercial-provider SDK --
a source-level guarantee. This is the build-level complement: it inspects
what's actually *installed* in the running interpreter (via
`importlib.metadata`, no network call, no external tool) and fails if a
forbidden package is present at all, regardless of whether anything
imports it. The two checks catch different failure modes -- a forbidden
package could arrive as a transitive dependency of something innocuous,
never imported directly anywhere, and the source scan would miss it.

Usage (inside the built image -- this is the actual CI/build-time check,
docs/v2/Dockerfile's `core` profile is what this validates):
    python scripts/check_sbom_allowlist.py
    python scripts/check_sbom_allowlist.py --json report.json   # machine-readable SBOM-lite

Exit code 0 = clean, 1 = a forbidden package is installed.
"""
from __future__ import annotations

import argparse
import json
import sys
from importlib.metadata import distributions

# Same vendor-SDK set tests/test_provider_isolation.py forbids at the source
# level -- PyPI distribution names, which don't always match the import root
# (e.g. dist "google-genai" -> import "google.genai"; kept in sync by hand,
# there are few enough of these that a shared constant would be more
# indirection than it's worth).
FORBIDDEN_DISTRIBUTIONS = {
    "google-genai",
    "openai",
    "anthropic",
    "cohere",
    "mistralai",
    "vllm",
    "sentence-transformers",
    "transformers",
    "gliner",
    "fastcoref",
    "litellm",
    "ollama",
}


def _normalize(name: str) -> str:
    return name.lower().replace("_", "-")


def installed_distributions() -> dict[str, str]:
    """{normalized distribution name: version} for everything importlib.metadata
    can see in the current interpreter -- this is what's actually on disk,
    not what a requirements.txt file merely lists."""
    out: dict[str, str] = {}
    for dist in distributions():
        name = dist.metadata.get("Name")
        if name:
            out[_normalize(name)] = dist.version
    return out


def check(profile: str = "core") -> list[tuple[str, str]]:
    """Returns [(distribution, version), ...] for every forbidden package
    found installed. Empty list = clean. `profile='external'` skips the
    check entirely -- that build is expected to carry google-genai."""
    if profile == "external":
        return []
    installed = installed_distributions()
    return [
        (name, installed[name])
        for name in sorted(FORBIDDEN_DISTRIBUTIONS)
        if name in installed
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--profile", default=None,
        help="'core' (default) or 'external'. Falls back to /app/.provider_profile "
             "(written by the Dockerfile) if present, else 'core'.",
    )
    parser.add_argument("--json", metavar="PATH", help="Write a JSON report to this path.")
    args = parser.parse_args()

    profile = args.profile
    if profile is None:
        try:
            with open("/app/.provider_profile", encoding="utf-8") as fh:
                profile = fh.read().strip()
        except OSError:
            profile = "core"

    violations = check(profile)
    report = {
        "profile": profile,
        "forbidden_distributions_checked": sorted(FORBIDDEN_DISTRIBUTIONS),
        "violations": [{"distribution": name, "version": version} for name, version in violations],
        "installed_count": len(installed_distributions()),
        "passed": not violations,
    }

    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2)

    if violations:
        print(f"SBOM allowlist FAILED (profile={profile}): forbidden package(s) installed:")
        for name, version in violations:
            print(f"  - {name}=={version}")
        return 1

    print(f"SBOM allowlist OK (profile={profile}): no forbidden vendor SDK installed "
         f"({report['installed_count']} packages checked).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
