from collections.abc import Callable
from contextlib import AbstractContextManager

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.config import get_settings
from app.core.auth import require_permission
from app.core.exceptions import FeedbackIQError
from app.core.responses import success_response
from app.dependencies import get_feedback_analysis_service, get_feedback_service_scope_provider
from app.domain.feedback.models import FeedbackProcessingStatus
from app.domain.feedback.feedback_analysis_service import FeedbackAnalysisService
from app.domain.feedback.service import FeedbackService

router = APIRouter(prefix="/feedback", tags=["feedback"], dependencies=[Depends(require_permission("analysis:run"))])


class FeedbackAnalyzeRequest(BaseModel):
    text: str = Field(..., min_length=1)
    top_k: int | None = Field(default=None, ge=1, le=20)
    persist: bool = False


@router.post("/analyze")
def analyze_feedback(
    payload: FeedbackAnalyzeRequest,
    service: FeedbackAnalysisService = Depends(get_feedback_analysis_service),
    feedback_service_scope_provider: Callable[[], AbstractContextManager[FeedbackService]] = Depends(
        get_feedback_service_scope_provider
    ),
) -> dict:
    settings = get_settings()
    record_id: int | None = None
    feedback_service = None
    service_context = feedback_service_scope_provider() if payload.persist else None
    if service_context is not None:
        feedback_service = service_context.__enter__()
    try:
        if feedback_service is not None:
            record = feedback_service.create_text_feedback(text=payload.text)
            record_id = record.id
            feedback_service.update_status(record_id, processing_status=FeedbackProcessingStatus.PROCESSING)
        try:
            result = service.analyze(payload.text, payload.top_k or settings.retrieval_top_k)
        except FeedbackIQError as exc:
            if feedback_service is not None and record_id is not None:
                feedback_service.mark_failed(record_id, error_code=exc.code, error_message=exc.message)
            raise
        except Exception:
            if feedback_service is not None and record_id is not None:
                feedback_service.mark_failed(record_id, error_code="internal_error", error_message="Feedback analysis failed.")
            raise
        if feedback_service is not None and record_id is not None:
            feedback_service.attach_analysis_result(record_id, sentiment=result.sentiment, routing=result.routing)
    finally:
        if service_context is not None:
            service_context.__exit__(None, None, None)
    data = {
        "text": result.text,
        "sentiment": {"label": result.sentiment.label, "score": result.sentiment.score},
        "routing": {
            "team": result.routing.team,
            "matched_keyword": result.routing.matched_keyword,
        },
        "retrieval": [
            {"text": item.text, "score": item.score}
            for item in result.retrieval_results
        ],
        "rag_context": result.rag_context,
    }
    if record_id is not None:
        data["record_id"] = record_id
    return success_response(
        data=data
    )
