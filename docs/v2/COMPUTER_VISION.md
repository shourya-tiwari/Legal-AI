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
**Docling** (IBM, MIT) is the primary PDF/DOCX → structured-document pipeline: reading order, section/heading boundaries, tables, and a clean document model that maps directly onto `Clause` segmentation (`NLP.md`). For image-only pages, **PaddleOCR PP-StructureV3** (Apache-2.0) or **Qwen2.5-VL** (open VLM) determine layout from the page image + text jointly. LayoutLMv3 remains a documented option for a fine-tuned layout head. This is what lets the NLP pipeline respect actual document structure instead of guessing from whitespace, as V1's `_simple_paragraph_split` regex does. (`MODEL_STACK.md` — OCR & document parsing.)

### 3. OCR
- **Baseline**: Tesseract 5 (Apache-2.0), kept from V1, for clean scans — zero licence risk, the floor everything improves on.
- **Layout + multilingual OCR**: **PaddleOCR PP-OCRv4** (Apache-2.0) — mature, CPU-acceptable, layout + table + formula.
- **OCR-free / hard-scan understanding**: **olmOCR** (AllenAI, Apache-2.0) or the standard open VLM (**Qwen2.5-VL**) for degraded scans, rotations, handwritten annotations, and complex layouts where OCR-then-parse degrades badly.
- **Confidence-gated escalation is between open models**: clean PDF → Docling; image page with a usable scan → PaddleOCR; page both flag low-confidence → olmOCR / Qwen2.5-VL. Every stage records `extraction_confidence` and which engine ran.
- **Commercial Document AI (Google / Azure)** is an **optional Class C plugin only** — available for the cloud SaaS profile where a customer specifically wants it, **never installed in on-prem/air-gapped builds, and never the default even in cloud**. The open stack above is the product.

### 4. Table extraction
**Table Transformer** (Microsoft, open weights) or **PaddleOCR PP-Structure** for detecting and structuring tables in digital PDFs (payment schedules, pricing tables, exhibit lists) — a capability V1 has none of; PyMuPDF's block extraction currently treats table cells as arbitrary text blocks with no row/column structure. Qwen2.5-VL handles table structure directly for the hard-scan path.

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
  ocr_engine_used: docling|tesseract|paddleocr|olmocr|qwen-vl|commercial_plugin
}
```

`extraction_confidence` and `ocr_engine_used` are surfaced to the user (closing a gap in V1, where OCR fallback happens silently with no visibility into extraction quality) and are logged for the observability stack (`ARCHITECTURE.md`). `commercial_plugin` only ever appears in a cloud deployment that has opted into the optional Class C OCR connector; it is impossible in on-prem/air-gapped builds.

## Phasing

Phase 2 shipped the CPU-only slice: OpenCV quality triage (Laplacian blur + Hough skew) and a geometric redaction-detection heuristic, wired into `extractor.py`'s PDF path. Docling, the VLM/OCR escalation stack, Table Transformer, and a trained signature detector land in **Phase 6** (`ROADMAP.md`), each re-evaluated against the Phase 2 heuristic it replaces before becoming the default.
