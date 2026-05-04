from fastapi import APIRouter, Depends, Query

from app.core.responses import success_response
from app.dependencies import get_workflow_service
from app.domain.workflow.models import ReviewStatus
from app.domain.workflow.schemas import (
    ReviewDecisionRequest,
    ReviewDecisionResponse,
    WorkflowReviewListResponse,
    WorkflowReviewRead,
    WorkflowTicketRead,
)
from app.domain.workflow.service import WorkflowService

router = APIRouter(prefix="/reviews", tags=["reviews"])


@router.get("")
def list_reviews(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    status: ReviewStatus | None = None,
    service: WorkflowService = Depends(get_workflow_service),
) -> dict:
    reviews, total = service.list_reviews(limit=limit, offset=offset, status=status)
    response = WorkflowReviewListResponse(
        items=[WorkflowReviewRead.model_validate(review) for review in reviews],
        total=total,
        limit=limit,
        offset=offset,
    )
    return success_response(data=response.model_dump(mode="json"))


@router.get("/{review_id}")
def get_review(review_id: int, service: WorkflowService = Depends(get_workflow_service)) -> dict:
    review = service.get_review(review_id)
    return success_response(data=WorkflowReviewRead.model_validate(review).model_dump(mode="json"))


@router.post("/{review_id}/decision")
def decide_review(
    review_id: int,
    request: ReviewDecisionRequest,
    service: WorkflowService = Depends(get_workflow_service),
) -> dict:
    result = service.decide_review(
        review_id,
        action=request.action,
        final_team=request.final_team,
        final_severity=request.final_severity,
        duplicate_of_ticket_id=request.duplicate_of_ticket_id,
        reviewer_note=request.reviewer_note,
    )
    response = ReviewDecisionResponse(
        review=WorkflowReviewRead.model_validate(result.review),
        ticket=WorkflowTicketRead.model_validate(result.ticket) if result.ticket is not None else None,
        audit_event_id=result.audit_event.id,
    )
    return success_response(data=response.model_dump(mode="json"))
