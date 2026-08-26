from __future__ import annotations

import re
import time
from typing import List, Tuple

from app.config import get_settings
from .model_router import generate_content

_CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]")

MAX_CHARS = 8000
CHUNK_OVERLAP = 200

def _clean(text: str) -> str:
    if not text:
        return ""
    return _CONTROL_RE.sub("", text)

def _split_with_overlap(
    text: str,
    max_len: int = MAX_CHARS,
    overlap: int = CHUNK_OVERLAP,
) -> List[str]:
    text = (text or "").strip()
    if len(text) <= max_len:
        return [text]

    chunks = []
    i = 0
    while i < len(text):
        end = min(i + max_len, len(text))
        chunks.append(text[i:end])
        if end == len(text):
            break
        i = end - overlap

    return chunks

SYSTEM_PROMPT = """
You are an expert legal editor.

Rewrite the following legal clause into simple English.

Rules:

- Preserve the exact legal meaning.
- Do NOT remove important details.
- Do NOT add information.
- Make it understandable for a normal person.
- Return ONLY the rewritten text.
"""

def _rewrite_chunk(chunk: str) -> str:
    prompt = f"""
{SYSTEM_PROMPT}

Clause:

{chunk}
"""
    result = generate_content(
        prompt,
        temperature=0.3,
    )
    return result

def rewrite_text(
    text: str,
    mode: str = "layman",
):
    start = time.time()
    cleaned = _clean(text)

    if not cleaned.strip():
        return "", {
            "latency_ms": 0,
            "chunks": 0,
        }

    chunks = _split_with_overlap(cleaned)
    outputs = []

    for chunk in chunks:
        outputs.append(_rewrite_chunk(chunk))

    rewritten = "\n\n".join(outputs).strip()
    configured_model = get_settings().GENAI_MODEL

    meta = {
        "model": configured_model,
        "latency_ms": int((time.time() - start) * 1000),
        "input_len": len(cleaned),
        "output_len": len(rewritten),
        "chunks": len(chunks),
        "chunked": len(chunks) > 1,
    }

    return rewritten, meta