from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.agents.graph import run_case_analysis
from app.auth import OrgContext
from app.db import get_db
from app.db_models import AgentTrace, Document
from app.guard import api_guard
from app.models import AgentAnalyzeRequest, AgentAnalyzeResponse

router = APIRouter(tags=["agents"])


@router.post("/agents/analyze", response_model=AgentAnalyzeResponse, summary="Run Agentic Case Analysis")
def analyze_case(
    req: AgentAnalyzeRequest,
    org: OrgContext = Depends(api_guard),
    db: Session = Depends(get_db),
) -> AgentAnalyzeResponse:
    document = db.query(Document).filter_by(id=req.document_id, org_id=org.id).first()
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")

    result = run_case_analysis(document_id=document.id, org_id=org.id, full_text=document.full_text)

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
    db.commit()

    return AgentAnalyzeResponse(
        document_id=document.id,
        clause_count=len(result.clauses),
        risk_findings=result.risk_findings,
        kg_conflicts=result.kg_conflicts,
        summary=result.summary,
        faithfulness_ok=result.faithfulness_ok,
        invalid_citation_numbers=result.invalid_citation_numbers,
        needs_human_review=result.needs_human_review,
        trace=result.trace,
    )
