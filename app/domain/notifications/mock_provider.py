from app.domain.notifications.provider import NotificationResult
from app.domain.workflow.models import WorkflowReviewItem, WorkflowTicket


class MockNotificationProvider:
    provider_name = "mock"

    def __init__(self) -> None:
        self.calls: list[dict] = []

    def notify_ticket_created(self, ticket: WorkflowTicket) -> NotificationResult:
        self.calls.append({"event": "ticket_created", "ticket_id": ticket.id})
        return NotificationResult(True, self.provider_name, "ticket_created")

    def notify_escalation(self, ticket: WorkflowTicket, *, reason: str | None = None) -> NotificationResult:
        self.calls.append({"event": "ticket_escalated", "ticket_id": ticket.id, "reason": reason})
        return NotificationResult(True, self.provider_name, "ticket_escalated")

    def notify_review_required(self, review: WorkflowReviewItem) -> NotificationResult:
        self.calls.append({"event": "review_required", "review_id": review.id})
        return NotificationResult(True, self.provider_name, "review_required")
