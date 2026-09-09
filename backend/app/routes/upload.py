import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.auth import OrgContext
from app.db import get_db
from app.db_models import Document
from app.guard import api_guard
from app.services.extractor import extract_text_and_blocks
from app.services.file_store import store_bytes
from app.services.model_router import is_external_permitted
from app.services.sensitivity import classify_sensitivity

logger = logging.getLogger("legalai.routes.upload")

router = APIRouter()

@router.post("/upload")
async def upload_contract(
    file: UploadFile = File(...),
    org: OrgContext = Depends(api_guard),
    db: Session = Depends(get_db),
):
    # Basic validation
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    file_bytes = await file.read()
    try:
        result = extract_text_and_blocks(
            file_bytes=file_bytes,
            filename=file.filename,
            content_type=file.content_type,
        )
    except Exception as e:
        # Almost always a bad input (unsupported type, corrupt/encrypted file)
        # -> a 4xx, not a 5xx. The exception text can carry local paths /
        # library internals, so it's logged server-side, not returned.
        logger.warning("extraction failed for %s: %s", file.filename, e)
        raise HTTPException(
            status_code=422,
            detail="Could not extract text from the uploaded file (unsupported type, or a corrupt/encrypted document).",
        ) from e

    # Normalize to clauses list expected by UI
    clauses = [{"id": b["id"], "text": b["text"], "rewritten": None} for b in result["blocks"]]

    assessment = classify_sensitivity(result["full_text"], filename=file.filename)

    # Persist the original file bytes (Phase 7, services/file_store.py).
    # Best-effort: extraction has already succeeded and the Document row is
    # the primary artifact, so a storage failure records "not stored" rather
    # than failing the upload.
    blob = store_bytes(file_bytes)

    document = Document(
        org_id=org.id,
        filename=file.filename,
        content_type=file.content_type,
        full_text=result["full_text"],
        blocks=result["blocks"],
        sensitivity_tier=assessment.tier,
        sensitivity_source=assessment.source,
        sensitivity_signals=[s.model_dump() for s in assessment.signals],
        quality=result.get("quality"),
        original_sha256=blob.sha256 if blob else None,
        original_size=blob.size if blob else None,
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    # ===== Return JSON Object =====
    # document_id/quality are additive — existing consumers reading
    # filename/full_text/clauses/count (the V1 response contract) are
    # unaffected. quality is only present for PDFs with scanned pages
    # (see services/cv/quality.py) — omitted otherwise.
    response = {
        "document_id": document.id,
        "filename": file.filename,
        "content_type": file.content_type,
        "full_text": result["full_text"],
        "clauses": clauses,
        "count": len(clauses),
        "sensitivity": {
            "tier": assessment.tier,
            "source": assessment.source,
            "rationale": assessment.rationale,
            "external_providers_permitted": is_external_permitted(assessment.tier),
        },
    }
    if "quality" in result:
        response["quality"] = result["quality"]
    return response
