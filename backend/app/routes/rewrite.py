import logging

from fastapi import APIRouter, Depends
from ..auth import OrgContext
from ..guard import api_guard
from ..models import RewriteRequest, RewriteResponse
from ..services.rewriter import rewrite_text
from ..services.sensitivity import classify_sensitivity

logger = logging.getLogger("legalai.routes.rewrite")

router = APIRouter()

@router.post("/rewrite", response_model=RewriteResponse)
def rewrite(req: RewriteRequest, org: OrgContext = Depends(api_guard)):
    tier = classify_sensitivity(req.text).tier
    out, meta = rewrite_text(req.text, req.mode, sensitivity=tier)
    logger.info("Rewrite completed: %s", meta)

    return RewriteResponse(
        rewritten_text=out,
        meta=meta,
    )