from dataclasses import dataclass
from typing import Protocol

from app.domain.workflow.models import WorkflowReviewItem, WorkflowTicket


@dataclass(frozen=True)
class NotificationResult:
    delivered: bool
    provider: str
    message: str


class NotificationProvider(Protocol):
    def notify_ticket_created(self, ticket: WorkflowTicket) -> NotificationResult:
        ...

    def notify_escalation(self, ticket: WorkflowTicket, *, reason: str | None = None) -> NotificationResult:
        ...

    def notify_review_required(self, review: WorkflowReviewItem) -> NotificationResult:
        ...
