# backend/app/services/nlp/json_utils.py
"""Defensive JSON parsing for LLM output, shared by the AI-escalation paths
in deontic.py and clause_classifier.py. Mirrors the pattern already used in
services/timeline.py — kept small and duplicated-in-spirit rather than
imported cross-module, since it's a few lines and timeline.py's version is
private to that module."""
from __future__ import annotations

import json
from typing import Any


def strip_code_fences(text: str) -> str:
    stripped = (text or "").strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()
    if stripped.lower().startswith("json"):
        stripped = stripped[4:].lstrip()
    return stripped


def parse_json_safely(text: str) -> Any:
    try:
        return json.loads(strip_code_fences(text))
    except Exception:
        return None
