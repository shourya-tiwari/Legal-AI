# Computer Vision Pipeline

V1's `extractor.py` gets text out of a page (PyMuPDF text layer, with `pytesseract` OCR as a soft-dependency fallback when a page has no text layer) but understands nothing about the page's *visual structure*: it doesn't know where a table is, whether a signature block was signed, whether a page is a low-quality scan likely to produce garbage OCR, or whether two scanned versions of a contract differ. V2's CV pipeline sits in front of the NLP pipeline and produces layout-aware, structurally-annotated input instead of a flat text blob.

## Pipeline stages

```
Uploaded file
  → 1. Document quality triage (blur/skew/resolution assessment)
  → 2. Layout analysis (reading order, section/heading/table regions)
  → 3. OCR (text-layer extraction, or true OCR for scans)
  → 4. Table extraction
  → 5. Signature & stamp detection
  → 6. Redaction-region detection
  → 7. Visual version diffing (when comparing two scanned versions)
  → Positioned, structured text blocks + layout metadata → NLP pipeline (NLP.md)
```

### 1. Document quality triage
Cheap, fast checks (blur estimation, skew angle, resolution) run first to decide the processing path: a clean digital PDF goes straight to text-layer extraction (as V1 already does via PyMuPDF); a low-quality scan is routed to the heavier OCR-free understanding path below, and flagged in the UI so the user knows extraction confidence may be lower.

### 2. Layout analysis
**LayoutLMv3** (Microsoft, open weights) determines reading order, section/heading boundaries, and table/figure regions from the page image + text jointly — this is what lets the NLP pipeline's segmentation stage (`NLP.md`) respect actual document structure instead of guessing from whitespace, as V1's `_simple_paragraph_split` regex does.

### 3. OCR
- **Baseline**: Tesseract (open source), kept from V1, for straightforward scans.
- **OCR-free understanding**: **Donut** (open weights, OCR-free document understanding transformer) for degraded scans or complex layouts where traditional OCR-then-parse pipelines degrade badly.
- **Confidence-gated commercial fallback**: only when both open-source paths report low confidence does the pipeline escalate to a commercial Document AI-class API (e.g., Google Document AI or Azure Document Intelligence) for that specific page — a bounded, cost-justified use of a commercial service, not a default dependency. This is the concrete implementation of the platform's "commercial only when it provides a clear advantage" principle for the CV layer specifically.

### 4. Table extraction
**Table Transformer** (Microsoft, open weights) for detecting and structuring tables in digital PDFs (payment schedules, pricing tables, exhibit lists) — a capability V1 has none of; PyMuPDF's block extraction currently treats table cells as arbitrary text blocks with no row/column structure.

### 5. Signature & stamp detection
A fine-tuned open-source object detector (YOLOv8-family) trained to localize signature blocks, initials, notary stamps, and seals — used to (a) verify a contract page is actually executed vs. a draft, and (b) locate where in a document the parties' identifying marks are, useful for the Ingestion & Triage agent's document-status determination (`AGENTS.md`).

### 6. Redaction-region detection
Detects existing black-box/whited-out redactions (to correctly exclude them from text extraction rather than feeding OCR garbage into downstream NLP) and, separately, flags candidate regions that *should* be redacted before a document leaves a sensitive-tier boundary (working with the NER-based PII detection in `NLP.md`/`ARCHITECTURE.md`'s redaction gate).

### 7. Visual version diffing
When two scanned versions of the same contract are compared and a reliable text diff isn't available (re-scans can shift OCR output even when content is identical), a structural/visual diff (image alignment + region-level comparison) flags pages that visually changed, directing the more expensive text-level diff to just those pages.

## Output contract

The CV pipeline's output feeds the NLP pipeline as **positioned text blocks with structure hints** — a strict superset of V1's `{"full_text": str, "blocks": [{"id","text","type","page"}]}`:

```
CVOutput {
  pages: [{
    page_no, quality_score, skew_angle,
    regions: [{ id, bbox, region_type: paragraph|heading|table|signature|stamp|redaction, text, reading_order_index }],
    tables: [{ region_id, rows: [[cell_text, ...], ...] }],
    signatures_detected: bool
  }],
  extraction_confidence: float,
  ocr_engine_used: tesseract|donut|commercial_fallback
}
```

`extraction_confidence` and `ocr_engine_used` are surfaced to the user (closing a gap in V1, where OCR fallback happens silently with no visibility into extraction quality) and are logged for the observability stack (`ARCHITECTURE.md`).
