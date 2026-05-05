from fastapi import APIRouter, Depends, Query

from app.core.auth import require_permission
from app.core.pagination import PaginationParams
from app.core.responses import success_response
from app.dependencies import get_feedback_service
from app.domain.feedback.models import FeedbackProcessingStatus, FeedbackSourceType
from app.domain.feedback.schemas import (
    FeedbackRecordCreate,
    FeedbackRecordListResponse,
    FeedbackRecordRead,
    FeedbackStatusUpdate,
)
from app.domain.feedback.service import FeedbackService

router = APIRouter(prefix="/feedback-records", tags=["feedback-records"], dependencies=[Depends(require_permission("feedback:read"))])


@router.post("")
def create_feedback_record(
    payload: FeedbackRecordCreate,
    _=Depends(require_permission("feedback:write")),
    service: FeedbackService = Depends(get_feedback_service),
) -> dict:
    record = service.create_text_feedback(
        text=payload.text,
        source_type=payload.source_type,
        original_input_reference=payload.original_input_reference,
    )
    return success_response(data=FeedbackRecordRead.model_validate(record).model_dump(mode="json"))


@router.get("")
def list_feedback_records(
    pagination: PaginationParams = Depends(),
    source_type: FeedbackSourceType | None = Query(default=None),
    processing_status: FeedbackProcessingStatus | None = Query(default=None),
    routed_team: str | None = Query(default=None),
    sentiment_label: str | None = Query(default=None),
    service: FeedbackService = Depends(get_feedback_service),
) -> dict:
    records, total = service.list_feedback_records(
        limit=pagination.limit,
        offset=pagination.offset,
        source_type=source_type,
        processing_status=processing_status,
        routed_team=routed_team,
        sentiment_label=sentiment_label,
    )
    response = FeedbackRecordListResponse(
        items=[FeedbackRecordRead.model_validate(record) for record in records],
        total=total,
        limit=pagination.limit,
        offset=pagination.offset,
    )
    return success_response(data=response.model_dump(mode="json"))


@router.get("/{feedback_id}")
def get_feedback_record(
    feedback_id: int,
    service: FeedbackService = Depends(get_feedback_service),
) -> dict:
    record = service.get_feedback_record(feedback_id)
    return success_response(data=FeedbackRecordRead.model_validate(record).model_dump(mode="json"))


@router.patch("/{feedback_id}/status")
def update_feedback_record_status(
    feedback_id: int,
    payload: FeedbackStatusUpdate,
    _=Depends(require_permission("feedback:write")),
    service: FeedbackService = Depends(get_feedback_service),
) -> dict:
    record = service.update_status(
        feedback_id,
        processing_status=payload.processing_status,
        error_code=payload.error_code,
        error_message=payload.error_message,
    )
    return success_response(data=FeedbackRecordRead.model_validate(record).model_dump(mode="json"))
