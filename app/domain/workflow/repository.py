from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.analysis.models import LLMAnalysisRun
from app.domain.workflow.models import ReviewStatus, TicketStatus, WorkflowAuditLog, WorkflowReviewItem, WorkflowTicket


class WorkflowRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_analysis_run(self, run_id: int) -> LLMAnalysisRun | None:
        return self.session.get(LLMAnalysisRun, run_id)

    def create_ticket(self, **fields) -> WorkflowTicket:
        ticket = WorkflowTicket(**fields)
        self.session.add(ticket)
        self.session.flush()
        self.session.refresh(ticket)
        return ticket

    def get_ticket(self, ticket_id: int) -> WorkflowTicket | None:
        return self.session.get(WorkflowTicket, ticket_id)

    def get_ticket_for_feedback(self, feedback_record_id: int) -> WorkflowTicket | None:
        return self.session.scalar(
            select(WorkflowTicket)
            .where(WorkflowTicket.feedback_record_id == feedback_record_id)
            .order_by(WorkflowTicket.created_at.desc(), WorkflowTicket.id.desc())
            .limit(1)
        )

    def list_tickets(
        self,
        *,
        limit: int,
        offset: int,
        status: TicketStatus | None = None,
        assigned_team: str | None = None,
    ) -> tuple[list[WorkflowTicket], int]:
        statement = select(WorkflowTicket)
        if status is not None:
            statement = statement.where(WorkflowTicket.status == status)
        if assigned_team is not None:
            statement = statement.where(WorkflowTicket.assigned_team == assigned_team)
        total = self.session.scalar(select(func.count()).select_from(statement.subquery())) or 0
        tickets = list(
            self.session.scalars(
                statement.order_by(WorkflowTicket.created_at.desc(), WorkflowTicket.id.desc())
                .limit(limit)
                .offset(offset)
            )
        )
        return tickets, total

    def find_duplicate(self, *, category: str | None, assigned_team: str | None, title: str) -> WorkflowTicket | None:
        statement = select(WorkflowTicket).where(
            WorkflowTicket.status.notin_(
                [TicketStatus.CLOSED, TicketStatus.RESOLVED, TicketStatus.REJECTED, TicketStatus.DUPLICATE]
            )
        )
        if category is not None:
            statement = statement.where(WorkflowTicket.category == category)
        if assigned_team is not None:
            statement = statement.where(WorkflowTicket.assigned_team == assigned_team)
        title_key = title.strip().lower()
        candidates = self.session.scalars(statement.order_by(WorkflowTicket.created_at.desc())).all()
        for candidate in candidates:
            if candidate.title.strip().lower() == title_key:
                return candidate
        return None

    def update_ticket(self, ticket: WorkflowTicket, **fields) -> WorkflowTicket:
        for key, value in fields.items():
            setattr(ticket, key, value)
        self.session.flush()
        self.session.refresh(ticket)
        return ticket

    def create_review(self, **fields) -> WorkflowReviewItem:
        review = WorkflowReviewItem(**fields)
        self.session.add(review)
        self.session.flush()
        self.session.refresh(review)
        return review

    def get_review(self, review_id: int) -> WorkflowReviewItem | None:
        return self.session.get(WorkflowReviewItem, review_id)

    def list_reviews(
        self,
        *,
        limit: int,
        offset: int,
        status: ReviewStatus | None = None,
    ) -> tuple[list[WorkflowReviewItem], int]:
        statement = select(WorkflowReviewItem)
        if status is not None:
            statement = statement.where(WorkflowReviewItem.status == status)
        total = self.session.scalar(select(func.count()).select_from(statement.subquery())) or 0
        reviews = list(
            self.session.scalars(
                statement.order_by(WorkflowReviewItem.created_at.desc(), WorkflowReviewItem.id.desc())
                .limit(limit)
                .offset(offset)
            )
        )
        return reviews, total

    def update_review(self, review: WorkflowReviewItem, **fields) -> WorkflowReviewItem:
        for key, value in fields.items():
            setattr(review, key, value)
        self.session.flush()
        self.session.refresh(review)
        return review

    def create_audit_log(self, **fields) -> WorkflowAuditLog:
        event = WorkflowAuditLog(**fields)
        self.session.add(event)
        self.session.flush()
        self.session.refresh(event)
        return event

    def list_audit_logs(
        self,
        *,
        limit: int,
        offset: int,
        entity_type: str | None = None,
        entity_id: int | None = None,
    ) -> tuple[list[WorkflowAuditLog], int]:
        statement = select(WorkflowAuditLog)
        if entity_type is not None:
            statement = statement.where(WorkflowAuditLog.entity_type == entity_type)
        if entity_id is not None:
            statement = statement.where(WorkflowAuditLog.entity_id == entity_id)
        total = self.session.scalar(select(func.count()).select_from(statement.subquery())) or 0
        events = list(
            self.session.scalars(
                statement.order_by(WorkflowAuditLog.created_at.desc(), WorkflowAuditLog.id.desc())
                .limit(limit)
                .offset(offset)
            )
        )
        return events, total
