from app.config import Settings
from app.domain.feedback.models import FeedbackRecord
from app.domain.workflow.rules import evaluate_workflow_rules


def test_high_severity_feedback_escalates_and_requires_review():
    record = FeedbackRecord(
        severity="P1",
        category="PAYMENT",
        sentiment_label="NEGATIVE",
        routed_team="Payment Team",
        confidence_score=0.9,
    )

    decision = evaluate_workflow_rules(record, Settings())

    assert decision.escalate is True
    assert decision.needs_review is True
    assert "High severity P1 requires review." in decision.review_reasons


def test_low_confidence_requires_review_without_escalation():
    record = FeedbackRecord(
        severity="P3",
        category="UI",
        sentiment_label="NEUTRAL",
        routed_team="Frontend Team",
        confidence_score=0.4,
    )

    decision = evaluate_workflow_rules(record, Settings())

    assert decision.escalate is False
    assert decision.needs_review is True
    assert "Analysis confidence is below workflow threshold." in decision.review_reasons
