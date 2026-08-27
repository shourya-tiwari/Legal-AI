from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Tuple

from .model_router import generate_content
from ..models import MapResponse, DocumentSection, TimelineEvent

# Limits aligned with other services
MAX_CHARS = 8000
OVERLAP = 200

_CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]")

def _clean(s: str) -> str:
    return _CONTROL_RE.sub("", s or "").strip()

def _split_with_overlap(text: str, max_len: int = MAX_CHARS, overlap: int = OVERLAP) -> List[str]:
    t = (text or "").strip()
    if len(t) <= max_len:
        return [t]
    # hierarchical split: paragraphs -> sentences -> whitespace
    for pattern in (r"\n\n+", r"(?<=[.!?])\s+", r"\s+"):
        parts = re.split(pattern, t)
        if len(parts) == 1:
            continue
        chunks: List[str] = []
        buf = ""
        for part in parts:
            cand = (buf + (" " if buf else "") + part).strip()
            if len(cand) <= max_len:
                buf = cand
            else:
                if buf:
                    chunks.append(buf)
                if len(part) > max_len:
                    # recurse down if a single part still exceeds
                    chunks.extend(_split_with_overlap(part, max_len, overlap))
                    buf = ""
                else:
                    buf = part
        if buf:
            chunks.append(buf)
        if len(chunks) > 1 and overlap > 0:
            with_ov: List[str] = []
            for i, c in enumerate(chunks):
                if i == 0:
                    with_ov.append(c)
                else:
                    prev_tail = chunks[i - 1][-overlap:]
                    with_ov.append((prev_tail + c)[:max_len])
            return with_ov
        return chunks
    # fallback sliding window
    out: List[str] = []
    i = 0
    while i < len(t):
        end = min(i + max_len, len(t))
        out.append(t[i:end])
        if end == len(t):
            break
        i = end - overlap if overlap > 0 else end
        if i < 0:
            i = 0
    return out

def _strip_code_fences(s: str) -> str:
    txt = (s or "").strip()
    if txt.startswith("```"):
        # remove first line fence
        lines = txt.splitlines()
        if lines and lines[0].startswith("```"):   
            lines = lines[1:]
        # drop trailing fence if present
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        txt = "\n".join(lines).strip()
    # leading 'json' label
    if txt.lower().startswith("json"):
        txt = txt[4:].lstrip()
    return txt

def _parse_json_list(s: str) -> List[Dict[str, Any]]:
    body = _strip_code_fences(s)
    try:
        data = json.loads(body)
        return data if isinstance(data, list) else []
    except Exception:
        return []

def _gen_json(prompt: str, context: str, temperature: float = 0.2) -> List[Dict[str, Any]]:
    full = f"{prompt}\n\nReturn only valid JSON array, no prose.\n\n<text>\n{context}\n</text>"
    raw_text = generate_content(full, task="timeline_extract", temperature=temperature)
    return _parse_json_list(raw_text)

def _dedupe_structure(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    out: List[Dict[str, Any]] = []
    for it in items:
        title = _clean(str(it.get("title", "")))
        key = title.lower()
        if not title or key in seen:
            continue
        seen.add(key)
        # normalize subsections
        subs = it.get("subsections") or []
        subs_norm: List[Dict[str, Any]] = []
        for sub in subs if isinstance(subs, list) else []:
            st = _clean(str(sub.get("title", "")))
            if not st:
                continue
            subs_norm.append({"title": st, "content_summary": _clean(str(sub.get("content_summary", "")))})
        out.append({"title": title, "content_summary": _clean(str(it.get("content_summary", ""))), "subsections": subs_norm})
    return out

def _dedupe_timeline(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    out: List[Dict[str, Any]] = []
    for it in items:
        dd = _clean(str(it.get("date_description", "")))
        ev = _clean(str(it.get("event", "")))
        if not ev:
            continue
        key = (dd.lower(), ev.lower())
        if key in seen:
            continue
        seen.add(key)
        out.append({"date_description": dd, "event": ev})
    return out

def generate_map(full_text: str) -> MapResponse:
    """
    Extracts document structure and timeline events using Gemini and returns Pydantic models.
    """
    text = _clean(full_text)
    if not text:
        return MapResponse(structure=[], timeline=[])
    chunks = _split_with_overlap(text, MAX_CHARS, OVERLAP)

    structure_prompt = (
        "Analyze the contract text and extract its hierarchical structure. "
        'Return JSON array: [{"title": str, "content_summary": str, "subsections": [{"title": str, "content_summary": str}]}].'
    )
    timeline_prompt = (
        "Extract all key dates, deadlines, and time-based obligations from the text. "
        'Return JSON array: [{"date_description": str, "event": str}].'
    )

    struct_raw: List[Dict[str, Any]] = []
    time_raw: List[Dict[str, Any]] = []

    for ch in chunks:
        struct_raw.extend(_gen_json(structure_prompt, ch))
        time_raw.extend(_gen_json(timeline_prompt, ch))

    struct_norm = _dedupe_structure(struct_raw)
    time_norm = _dedupe_timeline(time_raw)

    structure = [DocumentSection(**s) for s in struct_norm]
    timeline = [TimelineEvent(**t) for t in time_norm]
    return MapResponse(structure=structure, timeline=timeline)
