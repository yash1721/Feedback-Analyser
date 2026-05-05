from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.evaluation.models import EvaluationRun
from app.domain.feedback.models import FeedbackRecord
from app.domain.workflow.models import WorkflowReviewItem, WorkflowTicket


class AnalyticsRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def count_feedback(self, *, start_date: datetime, end_date: datetime) -> int:
        return self._count_between(FeedbackRecord, start_date=start_date, end_date=end_date)

    def count_tickets(self, *, start_date: datetime, end_date: datetime) -> int:
        return self._count_between(WorkflowTicket, start_date=start_date, end_date=end_date)

    def count_reviews(self, *, start_date: datetime, end_date: datetime) -> int:
        return self._count_between(WorkflowReviewItem, start_date=start_date, end_date=end_date)

    def feedback_breakdown(self, field_name: str, *, start_date: datetime, end_date: datetime) -> list[tuple[str, int]]:
        field = getattr(FeedbackRecord, field_name)
        return self._breakdown(FeedbackRecord, field, start_date=start_date, end_date=end_date)

    def ticket_breakdown(self, field_name: str, *, start_date: datetime, end_date: datetime) -> list[tuple[str, int]]:
        field = getattr(WorkflowTicket, field_name)
        return self._breakdown(WorkflowTicket, field, start_date=start_date, end_date=end_date)

    def review_breakdown(self, field_name: str, *, start_date: datetime, end_date: datetime) -> list[tuple[str, int]]:
        field = getattr(WorkflowReviewItem, field_name)
        return self._breakdown(WorkflowReviewItem, field, start_date=start_date, end_date=end_date)

    def feedback_rows_for_trend(self, *, start_date: datetime, end_date: datetime) -> list[datetime]:
        return list(
            self.session.scalars(
                select(FeedbackRecord.created_at)
                .where(FeedbackRecord.created_at >= start_date, FeedbackRecord.created_at <= end_date)
                .order_by(FeedbackRecord.created_at.asc())
            )
        )

    def average_confidence(self, *, start_date: datetime, end_date: datetime) -> float | None:
        return self.session.scalar(
            select(func.avg(FeedbackRecord.confidence_score)).where(
                FeedbackRecord.created_at >= start_date,
                FeedbackRecord.created_at <= end_date,
                FeedbackRecord.confidence_score.is_not(None),
            )
        )

    def count_feedback_where(self, field_name: str, value, *, start_date: datetime, end_date: datetime) -> int:
        field = getattr(FeedbackRecord, field_name)
        return self.session.scalar(
            select(func.count()).select_from(FeedbackRecord).where(
                FeedbackRecord.created_at >= start_date,
                FeedbackRecord.created_at <= end_date,
                field == value,
            )
        ) or 0

    def count_ticket_where(self, field_name: str, value, *, start_date: datetime, end_date: datetime) -> int:
        field = getattr(WorkflowTicket, field_name)
        return self.session.scalar(
            select(func.count()).select_from(WorkflowTicket).where(
                WorkflowTicket.created_at >= start_date,
                WorkflowTicket.created_at <= end_date,
                field == value,
            )
        ) or 0

    def count_review_where(self, field_name: str, value, *, start_date: datetime, end_date: datetime) -> int:
        field = getattr(WorkflowReviewItem, field_name)
        return self.session.scalar(
            select(func.count()).select_from(WorkflowReviewItem).where(
                WorkflowReviewItem.created_at >= start_date,
                WorkflowReviewItem.created_at <= end_date,
                field == value,
            )
        ) or 0

    def latest_evaluation_run(self) -> EvaluationRun | None:
        return self.session.scalar(select(EvaluationRun).order_by(EvaluationRun.created_at.desc(), EvaluationRun.id.desc()).limit(1))

    def _count_between(self, model, *, start_date: datetime, end_date: datetime) -> int:
        return self.session.scalar(
            select(func.count()).select_from(model).where(model.created_at >= start_date, model.created_at <= end_date)
        ) or 0

    def _breakdown(self, model, field, *, start_date: datetime, end_date: datetime) -> list[tuple[str, int]]:
        rows = self.session.execute(
            select(field, func.count())
            .select_from(model)
            .where(model.created_at >= start_date, model.created_at <= end_date, field.is_not(None))
            .group_by(field)
            .order_by(func.count().desc())
        ).all()
        return [(str(label), int(count)) for label, count in rows]
