# backend/app/services/model_router/policy.py
"""
The declarative routing policy (docs/v2/AI_STACK.md "The routing policy
engine"). Maps a (task, capability, sensitivity) to an ordered list of
candidate provider names.

Source of truth is app/policies/routing.yaml (versioned in git, eval-gated).
If PyYAML or the file is missing, DEFAULT_POLICY below is used -- identical
content, kept in sync, so the router always has a policy.

Invariants the engine enforces:
  - the default chain for every task is Class A/B only
  - a Class C provider is used from a chain ONLY when
      EXTERNAL_PROVIDERS_ENABLED is true AND the sensitivity tier is in
      class_c_allowed_tiers AND STRICT_LOCAL_ONLY is false
  - Privileged / Confidential never reach Class C
"""
from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Dict, List

from app.config import get_settings

from .types import SensitivityTier

logger = logging.getLogger("legalai.model_router.policy")

# Kept byte-for-byte in sync with app/policies/routing.yaml.
DEFAULT_POLICY: dict = {
    "version": 1,
    "class_c_allowed_tiers": ["public", "internal"],
    "tasks": {
        # generate ---------------------------------------------------------
        "generic": {"capability": "generate", "chain": ["local-llm"], "class_c": ["gemini"]},
        "clause_rewrite": {"capability": "generate", "chain": ["local-llm"], "class_c": ["gemini"]},
        "timeline_extract": {"capability": "generate", "chain": ["local-llm"], "class_c": ["gemini"]},
        "qa": {"capability": "generate", "chain": ["local-llm"], "class_c": ["gemini"]},
        "risk_analysis": {"capability": "generate", "chain": ["local-llm"], "class_c": ["gemini"]},
        "contextualize": {"capability": "generate", "chain": ["local-llm"], "class_c": ["gemini"]},
        "deontic_escalation": {"capability": "generate", "chain": ["local-llm"], "class_c": ["gemini"]},
        "clause_type_escalation": {"capability": "generate", "chain": ["local-llm"], "class_c": ["gemini"]},
        "agent_summary": {"capability": "generate", "chain": ["local-llm"], "class_c": ["gemini"]},
        # embed ------------------------------------------------------------
        "embed_corpus": {"capability": "embed",
                         "chain": ["local-embed-neural", "local-embed-remote", "local-embed-hash"],
                         "class_c": []},
        "embed_query": {"capability": "embed",
                        "chain": ["local-embed-neural", "local-embed-remote", "local-embed-hash"],
                        "class_c": []},
        # rerank ---------------------------------------------------------
        "rerank": {"capability": "rerank",
                   "chain": ["local-rerank-neural", "local-rerank-lexical"],
                   "class_c": []},
    },
}

_VALID_CAPABILITIES = {"generate", "embed", "rerank"}


class RoutingPolicy:
    def __init__(self, data: dict):
        self.version = data.get("version", 1)
        self._tasks: Dict[str, dict] = data.get("tasks", {})
        self.class_c_allowed_tiers = {
            t.lower() for t in data.get("class_c_allowed_tiers", ["public", "internal"])
        }

    def capability_for(self, task: str) -> str:
        entry = self._tasks.get(task) or self._tasks.get("generic", {})
        return entry.get("capability", "generate")

    def candidates(self, task: str, sensitivity: SensitivityTier) -> List[str]:
        """Ordered provider-name candidates for this task, with Class C
        appended only when policy + settings + sensitivity all permit."""
        entry = self._tasks.get(task)
        if entry is None:
            logger.debug("No policy entry for task '%s'; using 'generic'.", task)
            entry = self._tasks.get("generic", {"chain": ["local-llm"], "class_c": ["gemini"]})

        chain: List[str] = list(entry.get("chain", []))

        settings = get_settings()
        allow_c = (
            settings.EXTERNAL_PROVIDERS_ENABLED
            and not settings.STRICT_LOCAL_ONLY
            and sensitivity.value in self.class_c_allowed_tiers
        )
        if allow_c:
            chain += [c for c in entry.get("class_c", []) if c not in chain]
        return chain

    def class_c_names(self) -> set:
        names: set = set()
        for entry in self._tasks.values():
            names.update(entry.get("class_c", []))
        return names


def _load_yaml(path: Path) -> dict | None:
    try:
        import yaml  # type: ignore
    except Exception:
        logger.info("PyYAML not installed; using the built-in DEFAULT_POLICY.")
        return None
    try:
        with path.open("r", encoding="utf-8") as fh:
            return yaml.safe_load(fh)
    except FileNotFoundError:
        return None
    except Exception as e:  # pragma: no cover
        logger.warning("Failed to parse routing policy %s (%s); using DEFAULT_POLICY.", path, e)
        return None


@lru_cache
def get_policy() -> RoutingPolicy:
    settings = get_settings()
    if settings.ROUTING_POLICY_PATH:
        path = Path(settings.ROUTING_POLICY_PATH)
    else:
        path = Path(__file__).resolve().parents[2] / "policies" / "routing.yaml"
    data = _load_yaml(path) or DEFAULT_POLICY
    policy = RoutingPolicy(data)
    logger.info("Routing policy loaded (version %s, source=%s).",
                policy.version, path if data is not DEFAULT_POLICY else "DEFAULT_POLICY")
    return policy
