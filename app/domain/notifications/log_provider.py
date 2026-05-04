import logging

from app.domain.notifications.provider import NotificationResult
from app.domain.workflow.models import WorkflowReviewItem, WorkflowTicket

logger = logging.getLogger(__name__)


class LogNotificationProvider:
    provider_name = "log"

    def notify_ticket_created(self, ticket: WorkflowTicket) -> NotificationResult:
        logger.info("Workflow ticket created", extra={"ticket_id": ticket.id})
        return NotificationResult(True, self.provider_name, "ticket_created")

    def notify_escalation(self, ticket: WorkflowTicket, *, reason: str | None = None) -> NotificationResult:
        logger.warning("Workflow ticket escalated", extra={"ticket_id": ticket.id, "reason": reason})
        return NotificationResult(True, self.provider_name, "ticket_escalated")

    def notify_review_required(self, review: WorkflowReviewItem) -> NotificationResult:
        logger.info("Workflow review required", extra={"review_id": review.id})
        return NotificationResult(True, self.provider_name, "review_required")
