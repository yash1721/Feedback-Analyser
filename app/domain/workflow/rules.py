from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from app.config import Settings
from app.domain.feedback.models import FeedbackRecord


@dataclass(frozen=True)
class WorkflowRuleDecision:
    needs_review: bool
    escalate: bool
    review_reasons: list[str]
    due_at: datetime


def evaluate_workflow_rules(record: FeedbackRecord, settings: Settings) -> WorkflowRuleDecision:
    reasons: list[str] = []
    severity = (record.severity or "P3").upper()
    category = (record.category or "").upper()
    sentiment = (record.sentiment_label or "").upper()

    if severity == "P0":
        sla_hours = settings.workflow_p0_sla_hours
    elif severity == "P1":
        sla_hours = settings.workflow_p1_sla_hours
    else:
        sla_hours = settings.workflow_default_sla_hours

    if severity in {"P0", "P1"}:
        reasons.append(f"High severity {severity} requires review.")
    if record.confidence_score is None or record.confidence_score < settings.workflow_low_confidence_threshold:
        reasons.append("Analysis confidence is below workflow threshold.")
    if not record.routed_team:
        reasons.append("No routed team was produced by analysis.")

    escalates_for_risk = sentiment == "NEGATIVE" and category in {"PAYMENT", "SECURITY"}
    escalate = severity in {"P0", "P1"} or escalates_for_risk
    return WorkflowRuleDecision(
        needs_review=bool(reasons),
        escalate=escalate,
        review_reasons=reasons,
        due_at=datetime.now(timezone.utc) + timedelta(hours=sla_hours),
    )
