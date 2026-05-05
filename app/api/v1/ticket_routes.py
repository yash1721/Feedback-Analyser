from fastapi import APIRouter, Depends, Query

from app.core.auth import require_permission
from app.core.responses import success_response
from app.dependencies import get_workflow_service
from app.domain.workflow.models import TicketStatus
from app.domain.workflow.schemas import (
    TicketAssignRequest,
    TicketEscalateRequest,
    TicketStatusUpdate,
    WorkflowTicketListResponse,
    WorkflowTicketRead,
)
from app.domain.workflow.service import WorkflowService

router = APIRouter(prefix="/tickets", tags=["tickets"], dependencies=[Depends(require_permission("ticket:read"))])


@router.get("")
def list_tickets(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    status: TicketStatus | None = None,
    assigned_team: str | None = None,
    service: WorkflowService = Depends(get_workflow_service),
) -> dict:
    tickets, total = service.list_tickets(limit=limit, offset=offset, status=status, assigned_team=assigned_team)
    response = WorkflowTicketListResponse(
        items=[WorkflowTicketRead.model_validate(ticket) for ticket in tickets],
        total=total,
        limit=limit,
        offset=offset,
    )
    return success_response(data=response.model_dump(mode="json"))


@router.get("/{ticket_id}")
def get_ticket(ticket_id: int, service: WorkflowService = Depends(get_workflow_service)) -> dict:
    ticket = service.get_ticket(ticket_id)
    return success_response(data=WorkflowTicketRead.model_validate(ticket).model_dump(mode="json"))


@router.patch("/{ticket_id}/status")
def update_ticket_status(
    ticket_id: int,
    request: TicketStatusUpdate,
    _=Depends(require_permission("ticket:write")),
    service: WorkflowService = Depends(get_workflow_service),
) -> dict:
    ticket = service.update_ticket_status(ticket_id, status=request.status, reason=request.reason)
    return success_response(data=WorkflowTicketRead.model_validate(ticket).model_dump(mode="json"))


@router.post("/{ticket_id}/assign")
def assign_ticket(
    ticket_id: int,
    request: TicketAssignRequest,
    _=Depends(require_permission("ticket:write")),
    service: WorkflowService = Depends(get_workflow_service),
) -> dict:
    ticket = service.assign_ticket(
        ticket_id,
        assigned_team=request.assigned_team,
        assigned_owner=request.assigned_owner,
        reason=request.reason,
    )
    return success_response(data=WorkflowTicketRead.model_validate(ticket).model_dump(mode="json"))


@router.post("/{ticket_id}/escalate")
def escalate_ticket(
    ticket_id: int,
    request: TicketEscalateRequest,
    _=Depends(require_permission("ticket:write")),
    service: WorkflowService = Depends(get_workflow_service),
) -> dict:
    ticket = service.escalate_ticket(ticket_id, reason=request.reason)
    return success_response(data=WorkflowTicketRead.model_validate(ticket).model_dump(mode="json"))
