import logging

from fastapi import APIRouter, Depends

from app.auth import OrgContext
from app.guard import api_guard
from app.models import RewriteRequest, RewriteResponse
from app.services.rewriter import rewrite_text
from app.services.sensitivity import classify_sensitivity

logger = logging.getLogger("legalai.routes.rewrite")

router = APIRouter()


@router.post("/rewrite", response_model=RewriteResponse, summary="Plain-English rewrite")
def rewrite(req: RewriteRequest, org: OrgContext = Depends(api_guard)) -> RewriteResponse:
    tier = classify_sensitivity(req.text).tier
    out, meta = rewrite_text(req.text, req.mode, sensitivity=tier)
    logger.info("Rewrite completed: %s", meta)
    return RewriteResponse(rewritten_text=out, meta=meta)
