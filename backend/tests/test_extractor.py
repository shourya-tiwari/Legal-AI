import io

import docx
import pytest

from app.services.extractor import extract_text_and_blocks


def test_txt_extraction_returns_full_text_and_blocks():
    content = b"Paragraph one.\n\nParagraph two."
    result = extract_text_and_blocks(content, "contract.txt", "text/plain")

    assert "Paragraph one." in result["full_text"]
    assert "Paragraph two." in result["full_text"]
    assert len(result["blocks"]) == 2
    assert result["blocks"][0]["id"] == 1
    assert result["blocks"][0]["type"] == "paragraph"
    assert result["blocks"][0]["page"] == 1


def test_txt_extraction_empty_input_returns_no_blocks():
    result = extract_text_and_blocks(b"", "empty.txt", "text/plain")

    assert result["full_text"] == ""
    assert result["blocks"] == []


def test_docx_extraction_returns_paragraphs():
    document = docx.Document()
    document.add_paragraph("This Agreement is made on January 1, 2025.")
    document.add_paragraph("The Tenant shall pay rent monthly.")
    buf = io.BytesIO()
    document.save(buf)

    result = extract_text_and_blocks(
        buf.getvalue(), "lease.docx",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )

    assert "This Agreement is made on January 1, 2025." in result["full_text"]
    assert len(result["blocks"]) == 2
    assert all(b["page"] == 1 for b in result["blocks"])


def test_unknown_extension_falls_back_to_plain_text_decode():
    content = b"Just some plain content with no known extension."
    result = extract_text_and_blocks(content, "notes.xyz", None)

    assert "Just some plain content" in result["full_text"]
    assert len(result["blocks"]) == 1


def test_scanned_pdf_page_reports_quality_and_redacted_regions():
    """A no-text-layer PDF page triggers the CV path: blur/skew quality *and*
    the geometric redaction-box screen (services/cv/redaction.py), both
    surfaced under result["quality"] -- the wiring docs/v2/COMPUTER_VISION.md
    describes."""
    fitz = pytest.importorskip("fitz")
    doc = fitz.open()
    page = doc.new_page(width=600, height=800)
    page.draw_rect(fitz.Rect(100, 100, 400, 160), color=(0, 0, 0), fill=(0, 0, 0))
    pdf_bytes = doc.tobytes()
    doc.close()

    result = extract_text_and_blocks(pdf_bytes, "scan.pdf", "application/pdf")

    quality = result["quality"]
    assert quality["pages_assessed"] == 1
    assert quality["pages_with_redactions"] == [1]
    assert quality["pages"][0]["redacted_regions"]  # at least one black box found
