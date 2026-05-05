from fastapi import APIRouter, Depends

from app.core.auth import require_permission
from app.core.responses import success_response
from app.dependencies import get_processing_service
from app.domain.processing.schemas import ProcessingEnqueueResponse, ProcessingStatusResponse
from app.domain.processing.service import ProcessingService

router = APIRouter(prefix="/processing", tags=["processing"], dependencies=[Depends(require_permission("processing:read"))])


@router.post("/feedback-records/{feedback_id}/enqueue")
def enqueue_feedback_record(
    feedback_id: int,
    _=Depends(require_permission("processing:write")),
    service: ProcessingService = Depends(get_processing_service),
) -> dict:
    result = service.enqueue_feedback_record(feedback_id)
    response = ProcessingEnqueueResponse(
        feedback_id=result.record.id,
        processing_status=result.record.processing_status,
        task_id=result.task_id,
        enqueued=result.enqueued,
    )
    return success_response(data=response.model_dump(mode="json"))


@router.get("/feedback-records/{feedback_id}/status")
def get_feedback_processing_status(
    feedback_id: int,
    service: ProcessingService = Depends(get_processing_service),
) -> dict:
    record = service.get_feedback_status(feedback_id)
    response = ProcessingStatusResponse(
        feedback_id=record.id,
        processing_status=record.processing_status,
        task_id=record.processing_task_id,
        error_code=record.error_code,
        error_message=record.error_message,
        sentiment_label=record.sentiment_label,
        sentiment_score=record.sentiment_score,
        routed_team=record.routed_team,
        matched_keyword=record.matched_keyword,
    )
    return success_response(data=response.model_dump(mode="json"))
