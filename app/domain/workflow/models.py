from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TicketStatus(StrEnum):
    OPEN = "OPEN"
    IN_REVIEW = "IN_REVIEW"
    ASSIGNED = "ASSIGNED"
    ESCALATED = "ESCALATED"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"
    DUPLICATE = "DUPLICATE"
    REJECTED = "REJECTED"


class ReviewStatus(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    OVERRIDDEN = "OVERRIDDEN"


class WorkflowTicket(Base):
    __tablename__ = "workflow_tickets"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    feedback_record_id: Mapped[int] = mapped_column(ForeignKey("feedback_records.id"), index=True)
    analysis_run_id: Mapped[int | None] = mapped_column(ForeignKey("llm_analysis_runs.id"), nullable=True, index=True)
    retrieval_trace_id: Mapped[int | None] = mapped_column(ForeignKey("retrieval_traces.id"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    severity: Mapped[str | None] = mapped_column(String(16), index=True, nullable=True)
    status: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    assigned_team: Mapped[str | None] = mapped_column(String(128), index=True, nullable=True)
    assigned_owner: Mapped[str | None] = mapped_column(String(128), nullable=True)
    duplicate_of_ticket_id: Mapped[int | None] = mapped_column(ForeignKey("workflow_tickets.id"), nullable=True, index=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    escalated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class WorkflowReviewItem(Base):
    __tablename__ = "workflow_review_items"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    feedback_record_id: Mapped[int] = mapped_column(ForeignKey("feedback_records.id"), index=True)
    analysis_run_id: Mapped[int | None] = mapped_column(ForeignKey("llm_analysis_runs.id"), nullable=True, index=True)
    ticket_id: Mapped[int | None] = mapped_column(ForeignKey("workflow_tickets.id"), nullable=True, index=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    suggested_team: Mapped[str | None] = mapped_column(String(128), nullable=True)
    suggested_severity: Mapped[str | None] = mapped_column(String(16), nullable=True)
    final_team: Mapped[str | None] = mapped_column(String(128), nullable=True)
    final_severity: Mapped[str | None] = mapped_column(String(16), nullable=True)
    reviewer_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class WorkflowAuditLog(Base):
    __tablename__ = "workflow_audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    entity_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    entity_id: Mapped[int] = mapped_column(index=True, nullable=False)
    action: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    actor_type: Mapped[str] = mapped_column(String(64), nullable=False)
    actor_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    previous_state_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    new_state_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
