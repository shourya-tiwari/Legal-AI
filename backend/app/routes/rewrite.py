import logging

from fastapi import APIRouter, Depends
from ..auth import OrgContext
from ..guard import api_guard
from ..models import RewriteRequest, RewriteResponse
from ..services.rewriter import rewrite_text

logger = logging.getLogger("legalai.routes.rewrite")

router = APIRouter()

@router.post("/rewrite", response_model=RewriteResponse)
def rewrite(req: RewriteRequest, org: OrgContext = Depends(api_guard)):
    out, meta = rewrite_text(req.text, req.mode)
    logger.info("Rewrite completed: %s", meta)

    return RewriteResponse(
        rewritten_text=out,
        meta=meta,
    )