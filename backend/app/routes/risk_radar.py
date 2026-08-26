from fastapi import APIRouter
from app.models import RiskScanRequest, RiskScanResponse
from app.services.risk_radar.detector import generate_risk_radar_response

router = APIRouter()

@router.post("/risk/scan", response_model=RiskScanResponse, summary="Risk Scan Endpoint")
def scan_clause(body: RiskScanRequest) -> RiskScanResponse:
    return generate_risk_radar_response(body.text)
