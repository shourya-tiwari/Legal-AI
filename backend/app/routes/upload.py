from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session

from ..auth import OrgContext
from ..db import get_db
from ..db_models import Document
from ..guard import api_guard
from ..services.extractor import extract_text_and_blocks

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

    try:
        file_bytes = await file.read()
        result = extract_text_and_blocks(
            file_bytes=file_bytes,
            filename=file.filename,
            content_type=file.content_type,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Extraction failed: {e}")

    # Normalize to clauses list expected by UI
    clauses = [{"id": b["id"], "text": b["text"], "rewritten": None} for b in result["blocks"]]

    document = Document(
        org_id=org.id,
        filename=file.filename,
        content_type=file.content_type,
        full_text=result["full_text"],
        blocks=result["blocks"],
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
    }
    if "quality" in result:
        response["quality"] = result["quality"]
    return response
