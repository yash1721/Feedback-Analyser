from dataclasses import dataclass
from datetime import datetime, timezone

from app.config import Settings
from app.core.exceptions import BadRequestError, NotFoundError
from app.domain.feedback.models import FeedbackRecord
from app.domain.feedback.service import FeedbackService
from app.domain.notifications.provider import NotificationProvider
from app.domain.workflow.models import ReviewStatus, TicketStatus, WorkflowAuditLog, WorkflowReviewItem, WorkflowTicket
from app.domain.workflow.repository import WorkflowRepository
from app.domain.workflow.rules import evaluate_workflow_rules
from app.domain.workflow.schemas import ReviewDecisionAction


@dataclass(frozen=True)
class WorkflowCreateTicketResult:
    ticket: WorkflowTicket
    review_created: bool
    escalated: bool
    duplicate_of_ticket_id: int | None
    audit_event_ids: list[int]


@dataclass(frozen=True)
class ReviewDecisionResult:
    review: WorkflowReviewItem
    ticket: WorkflowTicket | None
    audit_event: WorkflowAuditLog


class WorkflowService:
    def __init__(
        self,
        *,
        repository: WorkflowRepository,
        feedback_service: FeedbackService,
        notification_provider: NotificationProvider,
        settings: Settings,
    ) -> None:
        self.repository = repository
        self.feedback_service = feedback_service
        self.notification_provider = notification_provider
        self.settings = settings

    def create_ticket_for_feedback(self, feedback_id: int) -> WorkflowCreateTicketResult:
        existing = self.repository.get_ticket_for_feedback(feedback_id)
        if existing is not None:
            return WorkflowCreateTicketResult(
                ticket=existing,
                review_created=False,
                escalated=existing.status == TicketStatus.ESCALATED,
                duplicate_of_ticket_id=existing.duplicate_of_ticket_id,
                audit_event_ids=[],
            )

        record = self.feedback_service.get_feedback_record(feedback_id)
        if record.latest_analysis_run_id is None:
            raise BadRequestError(
                "Feedback analysis is required before workflow ticket creation.",
                {"feedback_id": feedback_id},
            )
        analysis_run = self.repository.get_analysis_run(record.latest_analysis_run_id)
        if analysis_run is None:
            raise BadRequestError(
                "Latest analysis run is missing for this feedback record.",
                {"feedback_id": feedback_id, "analysis_run_id": record.latest_analysis_run_id},
            )

        title = self._build_title(record)
        duplicate = self.repository.find_duplicate(
            category=record.category,
            assigned_team=record.routed_team,
            title=title,
        )
        rules = evaluate_workflow_rules(record, self.settings)
        now = datetime.now(timezone.utc)
        status = TicketStatus.DUPLICATE if duplicate else TicketStatus.OPEN
        if duplicate is None and rules.escalate:
            status = TicketStatus.ESCALATED
        elif duplicate is None and rules.needs_review:
            status = TicketStatus.IN_REVIEW
        elif duplicate is None and record.routed_team:
            status = TicketStatus.ASSIGNED

        ticket = self.repository.create_ticket(
            feedback_record_id=record.id,
            analysis_run_id=analysis_run.id,
            retrieval_trace_id=analysis_run.retrieval_trace_id,
            title=title,
            description=self._build_description(record),
            category=record.category,
            severity=record.severity,
            status=status,
            assigned_team=record.routed_team,
            assigned_owner=None,
            duplicate_of_ticket_id=duplicate.id if duplicate else None,
            due_at=rules.due_at,
            escalated_at=now if status == TicketStatus.ESCALATED else None,
        )
        audit_ids = [
            self._audit_ticket(
                ticket,
                action="TICKET_CREATED",
                reason="Created from latest feedback analysis.",
            ).id
        ]
        if duplicate is not None:
            audit_ids.append(
                self._audit_ticket(
                    ticket,
                    action="DUPLICATE_LINKED",
                    reason=f"Matched existing open ticket {duplicate.id}.",
                    new_state={"duplicate_of_ticket_id": duplicate.id},
                ).id
            )
        if status == TicketStatus.ESCALATED:
            audit_ids.append(
                self._audit_ticket(
                    ticket,
                    action="TICKET_ESCALATED",
                    reason="Escalation rules matched.",
                    new_state={"status": TicketStatus.ESCALATED},
                ).id
            )
            self.notification_provider.notify_escalation(ticket, reason="Escalation rules matched.")
        else:
            self.notification_provider.notify_ticket_created(ticket)

        review_created = False
        if duplicate is None and rules.needs_review:
            review = self.repository.create_review(
                feedback_record_id=record.id,
                analysis_run_id=analysis_run.id,
                ticket_id=ticket.id,
                reason="; ".join(rules.review_reasons),
                status=ReviewStatus.PENDING,
                suggested_team=record.routed_team,
                suggested_severity=record.severity,
            )
            review_created = True
            audit_ids.append(
                self._audit_review(
                    review,
                    action="REVIEW_CREATED",
                    reason=review.reason,
                ).id
            )
            self.notification_provider.notify_review_required(review)

        self.repository.session.commit()
        return WorkflowCreateTicketResult(
            ticket=ticket,
            review_created=review_created,
            escalated=status == TicketStatus.ESCALATED,
            duplicate_of_ticket_id=ticket.duplicate_of_ticket_id,
            audit_event_ids=audit_ids,
        )

    def list_tickets(
        self,
        *,
        limit: int,
        offset: int,
        status: TicketStatus | None = None,
        assigned_team: str | None = None,
    ) -> tuple[list[WorkflowTicket], int]:
        return self.repository.list_tickets(limit=limit, offset=offset, status=status, assigned_team=assigned_team)

    def get_ticket(self, ticket_id: int) -> WorkflowTicket:
        ticket = self.repository.get_ticket(ticket_id)
        if ticket is None:
            raise NotFoundError("Workflow ticket was not found.", {"ticket_id": ticket_id})
        return ticket

    def update_ticket_status(self, ticket_id: int, *, status: TicketStatus, reason: str | None = None) -> WorkflowTicket:
        ticket = self.get_ticket(ticket_id)
        previous = self._ticket_state(ticket)
        now = datetime.now(timezone.utc)
        fields: dict = {"status": status}
        if status == TicketStatus.RESOLVED:
            fields["resolved_at"] = now
        if status == TicketStatus.CLOSED:
            fields["closed_at"] = now
        updated = self.repository.update_ticket(ticket, **fields)
        self._audit_ticket(
            updated,
            action="TICKET_STATUS_UPDATED",
            reason=reason,
            previous_state=previous,
            new_state=self._ticket_state(updated),
        )
        self.repository.session.commit()
        return updated

    def assign_ticket(
        self,
        ticket_id: int,
        *,
        assigned_team: str,
        assigned_owner: str | None = None,
        reason: str | None = None,
    ) -> WorkflowTicket:
        ticket = self.get_ticket(ticket_id)
        previous = self._ticket_state(ticket)
        updated = self.repository.update_ticket(
            ticket,
            assigned_team=assigned_team,
            assigned_owner=assigned_owner,
            status=TicketStatus.ASSIGNED if ticket.status != TicketStatus.ESCALATED else ticket.status,
        )
        self._audit_ticket(
            updated,
            action="TICKET_ASSIGNED",
            reason=reason,
            previous_state=previous,
            new_state=self._ticket_state(updated),
        )
        self.repository.session.commit()
        return updated

    def escalate_ticket(self, ticket_id: int, *, reason: str | None = None) -> WorkflowTicket:
        ticket = self.get_ticket(ticket_id)
        previous = self._ticket_state(ticket)
        updated = self.repository.update_ticket(
            ticket,
            status=TicketStatus.ESCALATED,
            escalated_at=datetime.now(timezone.utc),
        )
        self._audit_ticket(
            updated,
            action="TICKET_ESCALATED",
            reason=reason,
            previous_state=previous,
            new_state=self._ticket_state(updated),
        )
        self.notification_provider.notify_escalation(updated, reason=reason)
        self.repository.session.commit()
        return updated

    def list_reviews(
        self,
        *,
        limit: int,
        offset: int,
        status: ReviewStatus | None = None,
    ) -> tuple[list[WorkflowReviewItem], int]:
        return self.repository.list_reviews(limit=limit, offset=offset, status=status)

    def get_review(self, review_id: int) -> WorkflowReviewItem:
        review = self.repository.get_review(review_id)
        if review is None:
            raise NotFoundError("Workflow review item was not found.", {"review_id": review_id})
        return review

    def decide_review(
        self,
        review_id: int,
        *,
        action: ReviewDecisionAction,
        final_team: str | None = None,
        final_severity: str | None = None,
        duplicate_of_ticket_id: int | None = None,
        reviewer_note: str | None = None,
    ) -> ReviewDecisionResult:
        review = self.get_review(review_id)
        ticket = self.repository.get_ticket(review.ticket_id) if review.ticket_id else None
        if action in {ReviewDecisionAction.OVERRIDE_TEAM, ReviewDecisionAction.APPROVE} and final_team:
            review.final_team = final_team
            if ticket is not None:
                ticket.assigned_team = final_team
        if action == ReviewDecisionAction.OVERRIDE_SEVERITY and final_severity:
            review.final_severity = final_severity
            if ticket is not None:
                ticket.severity = final_severity
        if action == ReviewDecisionAction.MARK_DUPLICATE:
            if duplicate_of_ticket_id is None:
                raise BadRequestError("duplicate_of_ticket_id is required for MARK_DUPLICATE.")
            review.status = ReviewStatus.OVERRIDDEN
            if ticket is not None:
                ticket.duplicate_of_ticket_id = duplicate_of_ticket_id
                ticket.status = TicketStatus.DUPLICATE
        elif action == ReviewDecisionAction.REJECT:
            review.status = ReviewStatus.REJECTED
            if ticket is not None:
                ticket.status = TicketStatus.REJECTED
        elif action == ReviewDecisionAction.RESOLVE:
            review.status = ReviewStatus.APPROVED
            if ticket is not None:
                ticket.status = TicketStatus.RESOLVED
                ticket.resolved_at = datetime.now(timezone.utc)
        elif action in {ReviewDecisionAction.OVERRIDE_TEAM, ReviewDecisionAction.OVERRIDE_SEVERITY}:
            review.status = ReviewStatus.OVERRIDDEN
        else:
            review.status = ReviewStatus.APPROVED
            if ticket is not None and ticket.status == TicketStatus.IN_REVIEW:
                ticket.status = TicketStatus.ASSIGNED if ticket.assigned_team else TicketStatus.OPEN
        review.reviewer_note = reviewer_note
        review.decided_at = datetime.now(timezone.utc)
        self.repository.session.flush()
        self.repository.session.refresh(review)
        if ticket is not None:
            self.repository.session.refresh(ticket)
        event = self._audit_review(
            review,
            action=f"REVIEW_{action}",
            reason=reviewer_note,
            new_state={"review_status": review.status, "ticket_status": ticket.status if ticket else None},
        )
        self.repository.session.commit()
        return ReviewDecisionResult(review=review, ticket=ticket, audit_event=event)

    def list_audit_logs(
        self,
        *,
        limit: int,
        offset: int,
        entity_type: str | None = None,
        entity_id: int | None = None,
    ) -> tuple[list[WorkflowAuditLog], int]:
        return self.repository.list_audit_logs(limit=limit, offset=offset, entity_type=entity_type, entity_id=entity_id)

    def _build_title(self, record: FeedbackRecord) -> str:
        return f"[{record.severity or 'P3'}] {record.category or 'OTHER'} feedback for {record.routed_team or 'Unassigned'}"

    def _build_description(self, record: FeedbackRecord) -> str:
        text = record.summary or record.normalized_text or record.extracted_text or record.raw_text or ""
        action = record.recommended_action or "Review the feedback and decide the next operational action."
        return f"{text}\n\nRecommended action: {action}"

    def _audit_ticket(
        self,
        ticket: WorkflowTicket,
        *,
        action: str,
        reason: str | None,
        previous_state: dict | None = None,
        new_state: dict | None = None,
    ) -> WorkflowAuditLog:
        return self.repository.create_audit_log(
            entity_type="ticket",
            entity_id=ticket.id,
            action=action,
            actor_type="system",
            previous_state_json=previous_state,
            new_state_json=new_state or self._ticket_state(ticket),
            reason=reason,
        )

    def _audit_review(
        self,
        review: WorkflowReviewItem,
        *,
        action: str,
        reason: str | None,
        new_state: dict | None = None,
    ) -> WorkflowAuditLog:
        return self.repository.create_audit_log(
            entity_type="review",
            entity_id=review.id,
            action=action,
            actor_type="system",
            previous_state_json=None,
            new_state_json=new_state
            or {"status": review.status, "ticket_id": review.ticket_id, "reason": review.reason},
            reason=reason,
        )

    def _ticket_state(self, ticket: WorkflowTicket) -> dict:
        return {
            "status": ticket.status,
            "assigned_team": ticket.assigned_team,
            "assigned_owner": ticket.assigned_owner,
            "severity": ticket.severity,
            "duplicate_of_ticket_id": ticket.duplicate_of_ticket_id,
        }
