from fastapi import APIRouter, Depends

from app.core.responses import success_response
from app.dependencies import get_analysis_service, get_feedback_service
from app.domain.analysis.schemas import AnalysisRunResponse, LatestAnalysisResponse
from app.domain.analysis.service import AnalysisService
from app.domain.feedback.service import FeedbackService

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.post("/feedback-records/{feedback_id}/run")
def run_feedback_analysis(
    feedback_id: int,
    service: AnalysisService = Depends(get_analysis_service),
) -> dict:
    response = service.run_feedback_analysis(feedback_id)
    return success_response(data=response.model_dump(mode="json"))


@router.get("/feedback-records/{feedback_id}/latest")
def get_latest_feedback_analysis(
    feedback_id: int,
    analysis_service: AnalysisService = Depends(get_analysis_service),
    feedback_service: FeedbackService = Depends(get_feedback_service),
) -> dict:
    record = feedback_service.get_feedback_record(feedback_id)
    analysis_service.get_latest_run(feedback_id)
    response = LatestAnalysisResponse(
        feedback_id=record.id,
        latest_analysis_run_id=record.latest_analysis_run_id,
        sentiment_label=record.sentiment_label,
        sentiment_score=record.sentiment_score,
        category=record.category,
        severity=record.severity,
        routed_team=record.routed_team,
        summary=record.summary,
        recommended_action=record.recommended_action,
        confidence_score=record.confidence_score,
    )
    return success_response(data=response.model_dump(mode="json"))


@router.get("/runs/{run_id}")
def get_analysis_run(
    run_id: int,
    service: AnalysisService = Depends(get_analysis_service),
) -> dict:
    run = service.get_run(run_id)
    return success_response(data=AnalysisRunResponse.model_validate(run).model_dump(mode="json"))
