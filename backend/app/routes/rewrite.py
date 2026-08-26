import logging

from fastapi import APIRouter
from ..models import RewriteRequest, RewriteResponse
from ..services.rewriter import rewrite_text

logger = logging.getLogger("legalai.routes.rewrite")

router = APIRouter()

@router.post("/rewrite", response_model=RewriteResponse)
def rewrite(req: RewriteRequest):
    out, meta = rewrite_text(req.text, req.mode)
    logger.info("Rewrite completed: %s", meta)

    return RewriteResponse(
        rewritten_text=out,
        meta=meta,
    )