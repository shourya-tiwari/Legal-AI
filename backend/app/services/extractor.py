from __future__ import annotations

import io
import os
import re
from typing import Dict, Any, List

# Try importing local extraction libraries
try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

try:
    import docx  # python-docx
except ImportError:
    docx = None

try:
    from PIL import Image
    import pytesseract
except ImportError:
    Image = None
    pytesseract = None

from .cv.quality import assess_image_quality
from .cv.utils import pixmap_to_array

PDF_MIME = "application/pdf"
TXT_MIME = "text/plain"
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
SUPPORTED_IMAGE_MIMES = {"image/jpeg", "image/jpg", "image/png", "image/tiff", "image/gif", "image/webp"}

def _cleanup_text(s: str) -> str:
    if not s:
        return ""
    # de-hyphenate at line breaks
    s = re.sub(r"(\w)-\n(\w)", r"\1\2", s)
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n{2,}", "\n", s)
    return s.strip()

def _simple_paragraph_split(text: str) -> List[str]:
    chunks = re.split(r"\n\s*\n", text)
    result = []
    for c in chunks:
        cleaned = _cleanup_text(c)
        if cleaned:
            result.append(cleaned)
    return result

def _simple_blocks(text: str) -> List[Dict[str, Any]]:
    paragraphs = _simple_paragraph_split(text)
    return [{"id": i, "text": p, "type": "paragraph", "page": 1} for i, p in enumerate(paragraphs, 1)]

def _extract_pdf(file_bytes: bytes) -> Dict[str, Any]:
    if fitz is None:
        raise RuntimeError("PyMuPDF (fitz) is not installed. Please install via 'pip install PyMuPDF'")

    blocks: List[Dict[str, Any]] = []
    full_text_parts: List[str] = []
    page_quality_reports: List[Dict[str, Any]] = []
    block_id = 1

    doc = fitz.open(stream=file_bytes, filetype="pdf")
    for page_idx in range(len(doc)):
        page = doc[page_idx]
        page_num = page_idx + 1
        page_text = page.get_text("text") or ""

        # Empty text layer usually means a scanned page. Render it once and
        # (a) run a lightweight CV quality check (blur/skew/resolution — see
        # services/cv/quality.py) so extraction confidence is visible, and
        # (b) OCR it if pytesseract is available.
        if not page_text.strip():
            pix = None
            try:
                pix = page.get_pixmap()
            except Exception:
                pass

            if pix is not None:
                try:
                    quality = assess_image_quality(pixmap_to_array(pix))
                    quality["page"] = page_num
                    page_quality_reports.append(quality)
                except Exception:
                    pass

                if pytesseract is not None and Image is not None:
                    try:
                        img = Image.open(io.BytesIO(pix.tobytes()))
                        page_text = pytesseract.image_to_string(img) or ""
                    except Exception:
                        pass

        cleaned_page_text = _cleanup_text(page_text)
        if cleaned_page_text:
            full_text_parts.append(cleaned_page_text)

        # Extract blocks per page
        page_blocks = page.get_text("blocks")
        if page_blocks:
            for b in page_blocks:
                # b format: (x0, y0, x1, y1, "text", block_no, block_type)
                if len(b) >= 5 and b[6] == 0:  # text block
                    txt = _cleanup_text(b[4])
                    if txt:
                        blocks.append({"id": block_id, "text": txt, "type": "paragraph", "page": page_num})
                        block_id += 1
        elif cleaned_page_text:
            # Split page text if no blocks returned
            for p in _simple_paragraph_split(cleaned_page_text):
                blocks.append({"id": block_id, "text": p, "type": "paragraph", "page": page_num})
                block_id += 1

    doc.close()
    full_text = "\n\n".join(full_text_parts)
    result: Dict[str, Any] = {"full_text": full_text, "blocks": blocks}
    if page_quality_reports:
        result["quality"] = {
            "pages_assessed": len(page_quality_reports),
            "low_quality_pages": [q["page"] for q in page_quality_reports if q["is_low_quality"]],
            "pages": page_quality_reports,
        }
    return result

def _extract_docx(file_bytes: bytes) -> Dict[str, Any]:
    if docx is None:
        raise RuntimeError("python-docx is not installed. Please install via 'pip install python-docx'")

    doc = docx.Document(io.BytesIO(file_bytes))
    blocks: List[Dict[str, Any]] = []
    full_text_parts: List[str] = []
    block_id = 1

    for p in doc.paragraphs:
        txt = _cleanup_text(p.text)
        if txt:
            full_text_parts.append(txt)
            blocks.append({"id": block_id, "text": txt, "type": "paragraph", "page": 1})
            block_id += 1

    full_text = "\n\n".join(full_text_parts)
    return {"full_text": full_text, "blocks": blocks}

def _extract_image(file_bytes: bytes) -> Dict[str, Any]:
    if pytesseract is None or Image is None:
        text = "[Image file uploaded. Install pytesseract and tesseract-ocr to enable image OCR extraction.]"
        return {"full_text": text, "blocks": _simple_blocks(text)}

    try:
        img = Image.open(io.BytesIO(file_bytes))
        raw_text = pytesseract.image_to_string(img)
        text = _cleanup_text(raw_text) or "[No text detected in image]"
        return {"full_text": text, "blocks": _simple_blocks(text)}
    except Exception as e:
        text = f"[Image OCR processing error: {e}]"
        return {"full_text": text, "blocks": _simple_blocks(text)}

def extract_text_and_blocks(file_bytes: bytes, filename: str, content_type: str | None) -> Dict[str, Any]:
    """
    Local document text extraction for PDF, DOCX, TXT, and Images.
    Cloud-independent, no Document AI required.
    Returns dict with full_text and normalized blocks for the frontend schema.
    """
    ext = (os.path.splitext(filename)[1] or "").lower()
    mime = (content_type or "").lower()

    if ext == ".pdf":
        mime = PDF_MIME
    elif ext == ".txt":
        mime = TXT_MIME
    elif ext == ".docx":
        mime = DOCX_MIME
    elif ext in [".jpg", ".jpeg", ".png", ".tif", ".tiff", ".gif", ".webp"]:
        mime = "image/" + ext.lstrip(".")

    # TXT handling
    if mime == TXT_MIME or ext == ".txt":
        text = file_bytes.decode("utf-8", errors="replace")
        # Split into paragraphs on the raw text first: _cleanup_text collapses
        # blank-line paragraph separators, so pre-cleaning before splitting
        # would merge every paragraph into a single block.
        blocks = _simple_blocks(text)
        full_text = "\n\n".join(b["text"] for b in blocks)
        return {"full_text": full_text, "blocks": blocks}

    # DOCX handling
    if mime == DOCX_MIME or ext == ".docx":
        return _extract_docx(file_bytes)

    # PDF handling
    if mime == PDF_MIME or ext == ".pdf":
        return _extract_pdf(file_bytes)

    # Image handling
    if mime in SUPPORTED_IMAGE_MIMES or ext in [".jpg", ".jpeg", ".png", ".tif", ".tiff", ".gif", ".webp"]:
        return _extract_image(file_bytes)

    # Fallback default: try PDF, then plain text
    try:
        return _extract_pdf(file_bytes)
    except Exception:
        text = file_bytes.decode("utf-8", errors="replace")
        # Split into paragraphs on the raw text first: _cleanup_text collapses
        # blank-line paragraph separators, so pre-cleaning before splitting
        # would merge every paragraph into a single block.
        blocks = _simple_blocks(text)
        full_text = "\n\n".join(b["text"] for b in blocks)
        return {"full_text": full_text, "blocks": blocks}
