from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.agents.graph import run_case_analysis
from app.auth import OrgContext
from app.db import get_db
from app.db_models import AgentTrace, CaseAnalysis, Document
from app.guard import api_guard
from app.models import AgentAnalyzeRequest, AgentAnalyzeResponse
from app.services.model_router import is_external_permitted

router = APIRouter(tags=["agents"])


def run_and_persist_analysis(
    document: Document,
    org: OrgContext,
    db: Session,
    *,
    analysis_mode: str = "full",
    use_ai_planner: bool = False,
) -> AgentAnalyzeResponse:
    """Run the planner-driven agent graph on a persisted document, write one
    AgentTrace row per step, and build the response. Shared by /api/agents/
    analyze and /api/v2/documents/{id}/analyze."""
    result = run_case_analysis(
        document_id=document.id,
        org_id=org.id,
        full_text=document.full_text,
        analysis_mode=analysis_mode,
        use_ai_planner=use_ai_planner,
        sensitivity_tier=document.sensitivity_tier,
    )

    for step_no, step in enumerate(result.trace, start=1):
        db.add(
            AgentTrace(
                org_id=org.id,
                document_id=document.id,
                agent_name=step.agent_name,
                step_no=step_no,
                input_summary=step.input_summary,
                output_summary=step.output_summary,
            )
        )
    db.add(
        CaseAnalysis(
            org_id=org.id,
            document_id=document.id,
            analysis_mode=analysis_mode,
            plan=result.plan,
            summary=result.summary,
            faithfulness_ok=result.faithfulness_ok,
            faithfulness_method=result.faithfulness_method,
            unsupported_claims=result.unsupported_claims,
            invalid_citation_numbers=result.invalid_citation_numbers,
            needs_human_review=result.needs_human_review,
        )
    )
    db.commit()

    return AgentAnalyzeResponse(
        document_id=document.id,
        clause_count=len(result.clauses),
        sensitivity_tier=result.sensitivity_tier,
        external_providers_permitted=is_external_permitted(result.sensitivity_tier),
        plan=result.plan,
        plan_rationale=result.plan_rationale,
        risk_findings=result.risk_findings,
        kg_conflicts=result.kg_conflicts,
        summary=result.summary,
        faithfulness_ok=result.faithfulness_ok,
        faithfulness_method=result.faithfulness_method,
        unsupported_claims=result.unsupported_claims,
        invalid_citation_numbers=result.invalid_citation_numbers,
        needs_human_review=result.needs_human_review,
        trace=result.trace,
    )


@router.post("/agents/analyze", response_model=AgentAnalyzeResponse, summary="Run Agentic Case Analysis")
def analyze_case(
    req: AgentAnalyzeRequest,
    org: OrgContext = Depends(api_guard),
    db: Session = Depends(get_db),
) -> AgentAnalyzeResponse:
    document = db.query(Document).filter_by(id=req.document_id, org_id=org.id).first()
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")

    return run_and_persist_analysis(
        document, org, db,
        analysis_mode=req.analysis_mode,
        use_ai_planner=req.use_ai_planner,
    )
