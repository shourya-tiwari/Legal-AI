from fastapi import APIRouter, Depends

from app.auth import OrgContext
from app.guard import api_guard
from app.models import MapRequest, MapResponse
from app.services.sensitivity import classify_sensitivity
from app.services.timeline import generate_map

router = APIRouter(tags=["timeline"])


@router.post("/map", response_model=MapResponse, summary="Get Contract Map")
def get_contract_map(req: MapRequest, org: OrgContext = Depends(api_guard)) -> MapResponse:
    """Accepts {"contract_text": "..."} and returns structure[] and timeline[]."""
    return generate_map(req.contract_text, sensitivity=classify_sensitivity(req.contract_text).tier)
