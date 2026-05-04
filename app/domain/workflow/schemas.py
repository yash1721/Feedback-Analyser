from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from app.domain.workflow.models import ReviewStatus, TicketStatus


class ReviewDecisionAction(StrEnum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    OVERRIDE_TEAM = "OVERRIDE_TEAM"
    OVERRIDE_SEVERITY = "OVERRIDE_SEVERITY"
    MARK_DUPLICATE = "MARK_DUPLICATE"
    RESOLVE = "RESOLVE"


class WorkflowTicketRead(BaseModel):
    id: int
    feedback_record_id: int
    analysis_run_id: int | None
    retrieval_trace_id: int | None
    title: str
    description: str
    category: str | None
    severity: str | None
    status: TicketStatus
    assigned_team: str | None
    assigned_owner: str | None
    duplicate_of_ticket_id: int | None
    due_at: datetime | None
    escalated_at: datetime | None
    resolved_at: datetime | None
    closed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WorkflowTicketListResponse(BaseModel):
    items: list[WorkflowTicketRead]
    total: int
    limit: int
    offset: int


class WorkflowCreateTicketResponse(BaseModel):
    ticket: WorkflowTicketRead
    review_created: bool
    escalated: bool
    duplicate_of_ticket_id: int | None
    audit_event_ids: list[int] = Field(default_factory=list)


class TicketStatusUpdate(BaseModel):
    status: TicketStatus
    reason: str | None = Field(default=None, max_length=1000)


class TicketAssignRequest(BaseModel):
    assigned_team: str = Field(..., min_length=1, max_length=128)
    assigned_owner: str | None = Field(default=None, max_length=128)
    reason: str | None = Field(default=None, max_length=1000)


class TicketEscalateRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=1000)


class WorkflowReviewRead(BaseModel):
    id: int
    feedback_record_id: int
    analysis_run_id: int | None
    ticket_id: int | None
    reason: str
    status: ReviewStatus
    suggested_team: str | None
    suggested_severity: str | None
    final_team: str | None
    final_severity: str | None
    reviewer_note: str | None
    created_at: datetime
    updated_at: datetime
    decided_at: datetime | None

    model_config = {"from_attributes": True}


class WorkflowReviewListResponse(BaseModel):
    items: list[WorkflowReviewRead]
    total: int
    limit: int
    offset: int


class ReviewDecisionRequest(BaseModel):
    action: ReviewDecisionAction
    final_team: str | None = Field(default=None, max_length=128)
    final_severity: str | None = Field(default=None, max_length=16)
    duplicate_of_ticket_id: int | None = None
    reviewer_note: str | None = Field(default=None, max_length=1000)


class ReviewDecisionResponse(BaseModel):
    review: WorkflowReviewRead
    ticket: WorkflowTicketRead | None
    audit_event_id: int


class WorkflowAuditLogRead(BaseModel):
    id: int
    entity_type: str
    entity_id: int
    action: str
    actor_type: str
    actor_id: str | None
    previous_state_json: dict | None
    new_state_json: dict | None
    reason: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class WorkflowAuditLogListResponse(BaseModel):
    items: list[WorkflowAuditLogRead]
    total: int
    limit: int
    offset: int
