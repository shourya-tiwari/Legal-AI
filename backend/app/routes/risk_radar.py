from fastapi import APIRouter, Depends
from app.auth import OrgContext
from app.guard import api_guard
from app.models import RiskScanRequest, RiskScanResponse
from app.services.risk_radar.detector import generate_risk_radar_response
from app.services.sensitivity import classify_sensitivity

router = APIRouter()

@router.post("/risk/scan", response_model=RiskScanResponse, summary="Risk Scan Endpoint")
def scan_clause(body: RiskScanRequest, org: OrgContext = Depends(api_guard)) -> RiskScanResponse:
    return generate_risk_radar_response(body.text, sensitivity=classify_sensitivity(body.text).tier)
