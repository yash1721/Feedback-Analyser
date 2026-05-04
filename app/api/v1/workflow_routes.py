from fastapi import APIRouter, Depends, Query

from app.core.responses import success_response
from app.dependencies import get_workflow_service
from app.domain.workflow.schemas import (
    WorkflowAuditLogListResponse,
    WorkflowAuditLogRead,
    WorkflowCreateTicketResponse,
    WorkflowTicketRead,
)
from app.domain.workflow.service import WorkflowService

router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.post("/feedback-records/{feedback_id}/create-ticket")
def create_ticket_for_feedback(
    feedback_id: int,
    service: WorkflowService = Depends(get_workflow_service),
) -> dict:
    result = service.create_ticket_for_feedback(feedback_id)
    response = WorkflowCreateTicketResponse(
        ticket=WorkflowTicketRead.model_validate(result.ticket),
        review_created=result.review_created,
        escalated=result.escalated,
        duplicate_of_ticket_id=result.duplicate_of_ticket_id,
        audit_event_ids=result.audit_event_ids,
    )
    return success_response(data=response.model_dump(mode="json"))


@router.get("/audit-logs")
def list_workflow_audit_logs(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    entity_type: str | None = None,
    entity_id: int | None = None,
    service: WorkflowService = Depends(get_workflow_service),
) -> dict:
    events, total = service.list_audit_logs(limit=limit, offset=offset, entity_type=entity_type, entity_id=entity_id)
    response = WorkflowAuditLogListResponse(
        items=[WorkflowAuditLogRead.model_validate(event) for event in events],
        total=total,
        limit=limit,
        offset=offset,
    )
    return success_response(data=response.model_dump(mode="json"))
