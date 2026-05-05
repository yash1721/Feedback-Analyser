from collections import Counter
from datetime import datetime, timedelta, timezone

from app.domain.analytics.executive_summary import build_executive_summary
from app.domain.analytics.repository import AnalyticsRepository
from app.domain.analytics.report import AnalyticsReportGenerator
from app.domain.analytics.schemas import (
    AnalyticsReportResponse,
    AnalyticsSummaryResponse,
    AnalyticsTimeRange,
    BreakdownItem,
    EvaluationAnalyticsResponse,
    ExecutiveSummaryResponse,
    FeedbackTrendPoint,
    FeedbackTrendResponse,
    ReviewAnalyticsResponse,
    TicketAnalyticsResponse,
    TrendInterval,
)
from app.domain.feedback.models import FeedbackProcessingStatus
from app.domain.workflow.models import ReviewStatus, TicketStatus


class AnalyticsService:
    def __init__(self, *, repository: AnalyticsRepository, report_generator: AnalyticsReportGenerator) -> None:
        self.repository = repository
        self.report_generator = report_generator

    def time_range(
        self,
        *,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        interval: TrendInterval = TrendInterval.DAY,
    ) -> AnalyticsTimeRange:
        end = _as_utc(end_date) if end_date else datetime.now(timezone.utc)
        start = _as_utc(start_date) if start_date else end - timedelta(days=30)
        if start > end:
            raise ValueError("start_date must be before end_date.")
        return AnalyticsTimeRange(start_date=start, end_date=end, interval=interval)

    def summary(self, time_range: AnalyticsTimeRange) -> AnalyticsSummaryResponse:
        total = self.repository.count_feedback(start_date=time_range.start_date, end_date=time_range.end_date)
        negative = self.repository.count_feedback_where("sentiment_label", "NEGATIVE", start_date=time_range.start_date, end_date=time_range.end_date)
        failed = self.repository.count_feedback_where(
            "processing_status",
            FeedbackProcessingStatus.FAILED,
            start_date=time_range.start_date,
            end_date=time_range.end_date,
        )
        pii = self.repository.count_feedback_where("pii_detected", True, start_date=time_range.start_date, end_date=time_range.end_date)
        injection = self.repository.count_feedback_where(
            "prompt_injection_detected",
            True,
            start_date=time_range.start_date,
            end_date=time_range.end_date,
        )
        average_confidence = self.repository.average_confidence(start_date=time_range.start_date, end_date=time_range.end_date)
        return AnalyticsSummaryResponse(
            time_range=time_range,
            total_feedback=total,
            negative_feedback_percentage=_percentage(negative, total),
            failed_processing_percentage=_percentage(failed, total),
            average_confidence_score=round(float(average_confidence), 4) if average_confidence is not None else None,
            pii_detected_count=pii,
            prompt_injection_detected_count=injection,
            source_type_breakdown=self._feedback_breakdown("source_type", total, time_range),
            processing_status_breakdown=self._feedback_breakdown("processing_status", total, time_range),
            sentiment_breakdown=self._feedback_breakdown("sentiment_label", total, time_range),
            category_breakdown=self._feedback_breakdown("category", total, time_range),
            severity_breakdown=self._feedback_breakdown("severity", total, time_range),
            team_breakdown=self._feedback_breakdown("routed_team", total, time_range),
        )

    def feedback_trends(self, time_range: AnalyticsTimeRange) -> FeedbackTrendResponse:
        rows = self.repository.feedback_rows_for_trend(start_date=time_range.start_date, end_date=time_range.end_date)
        counts = Counter(_bucket_label(row, time_range.interval) for row in rows)
        points = [FeedbackTrendPoint(bucket=bucket, count=count) for bucket, count in sorted(counts.items())]
        return FeedbackTrendResponse(time_range=time_range, points=points)

    def sentiment_breakdown(self, time_range: AnalyticsTimeRange) -> list[BreakdownItem]:
        total = self.repository.count_feedback(start_date=time_range.start_date, end_date=time_range.end_date)
        return self._feedback_breakdown("sentiment_label", total, time_range)

    def category_breakdown(self, time_range: AnalyticsTimeRange) -> list[BreakdownItem]:
        total = self.repository.count_feedback(start_date=time_range.start_date, end_date=time_range.end_date)
        return self._feedback_breakdown("category", total, time_range)

    def severity_breakdown(self, time_range: AnalyticsTimeRange) -> list[BreakdownItem]:
        total = self.repository.count_feedback(start_date=time_range.start_date, end_date=time_range.end_date)
        return self._feedback_breakdown("severity", total, time_range)

    def team_routing_breakdown(self, time_range: AnalyticsTimeRange) -> list[BreakdownItem]:
        total = self.repository.count_feedback(start_date=time_range.start_date, end_date=time_range.end_date)
        return self._feedback_breakdown("routed_team", total, time_range)

    def tickets(self, time_range: AnalyticsTimeRange) -> TicketAnalyticsResponse:
        total = self.repository.count_tickets(start_date=time_range.start_date, end_date=time_range.end_date)
        escalated = self.repository.count_ticket_where("status", TicketStatus.ESCALATED, start_date=time_range.start_date, end_date=time_range.end_date)
        duplicate = self.repository.count_ticket_where("status", TicketStatus.DUPLICATE, start_date=time_range.start_date, end_date=time_range.end_date)
        open_count = sum(
            self.repository.count_ticket_where("status", status, start_date=time_range.start_date, end_date=time_range.end_date)
            for status in [TicketStatus.OPEN, TicketStatus.IN_REVIEW, TicketStatus.ASSIGNED, TicketStatus.ESCALATED]
        )
        return TicketAnalyticsResponse(
            time_range=time_range,
            total_tickets=total,
            open_ticket_count=open_count,
            escalated_ticket_count=escalated,
            duplicate_ticket_count=duplicate,
            escalation_rate=_percentage(escalated, total),
            status_breakdown=self._ticket_breakdown("status", total, time_range),
            severity_breakdown=self._ticket_breakdown("severity", total, time_range),
            team_breakdown=self._ticket_breakdown("assigned_team", total, time_range),
        )

    def reviews(self, time_range: AnalyticsTimeRange) -> ReviewAnalyticsResponse:
        total = self.repository.count_reviews(start_date=time_range.start_date, end_date=time_range.end_date)
        pending = self.repository.count_review_where("status", ReviewStatus.PENDING, start_date=time_range.start_date, end_date=time_range.end_date)
        feedback_total = self.repository.count_feedback(start_date=time_range.start_date, end_date=time_range.end_date)
        return ReviewAnalyticsResponse(
            time_range=time_range,
            total_reviews=total,
            pending_review_count=pending,
            human_review_rate=_percentage(total, feedback_total),
            status_breakdown=self._review_breakdown("status", total, time_range),
            reason_breakdown=self._review_breakdown("reason", total, time_range),
        )

    def evaluations(self) -> EvaluationAnalyticsResponse:
        run = self.repository.latest_evaluation_run()
        if run is None:
            return EvaluationAnalyticsResponse(
                latest_run_id=None,
                dataset_name=None,
                provider=None,
                model_name=None,
                created_at=None,
                total_examples=None,
                metrics={},
            )
        return EvaluationAnalyticsResponse(
            latest_run_id=run.id,
            dataset_name=run.dataset_name,
            provider=run.provider,
            model_name=run.model_name,
            created_at=run.created_at,
            total_examples=run.total_examples,
            metrics=run.metrics_json or {},
        )

    def executive_summary(self, time_range: AnalyticsTimeRange) -> ExecutiveSummaryResponse:
        return build_executive_summary(
            summary=self.summary(time_range),
            tickets=self.tickets(time_range),
            reviews=self.reviews(time_range),
            evaluation=self.evaluations(),
        )

    def report(self, time_range: AnalyticsTimeRange, *, format: str = "markdown") -> AnalyticsReportResponse:
        if format not in {"markdown", "json"}:
            raise ValueError("format must be markdown or json.")
        summary = self.summary(time_range)
        tickets = self.tickets(time_range)
        reviews = self.reviews(time_range)
        evaluation = self.evaluations()
        executive = build_executive_summary(summary=summary, tickets=tickets, reviews=reviews, evaluation=evaluation)
        payload = {
            "summary": summary.model_dump(mode="json"),
            "feedback_trends": self.feedback_trends(time_range).model_dump(mode="json"),
            "tickets": tickets.model_dump(mode="json"),
            "reviews": reviews.model_dump(mode="json"),
            "evaluation": evaluation.model_dump(mode="json"),
            "executive_summary": executive.model_dump(mode="json"),
        }
        return self.report_generator.write_report(payload=payload, executive_summary=executive, format=format)

    def _feedback_breakdown(self, field_name: str, total: int, time_range: AnalyticsTimeRange) -> list[BreakdownItem]:
        return _breakdown_items(self.repository.feedback_breakdown(field_name, start_date=time_range.start_date, end_date=time_range.end_date), total)

    def _ticket_breakdown(self, field_name: str, total: int, time_range: AnalyticsTimeRange) -> list[BreakdownItem]:
        return _breakdown_items(self.repository.ticket_breakdown(field_name, start_date=time_range.start_date, end_date=time_range.end_date), total)

    def _review_breakdown(self, field_name: str, total: int, time_range: AnalyticsTimeRange) -> list[BreakdownItem]:
        return _breakdown_items(self.repository.review_breakdown(field_name, start_date=time_range.start_date, end_date=time_range.end_date), total)


def _breakdown_items(rows: list[tuple[str, int]], total: int) -> list[BreakdownItem]:
    return [BreakdownItem(label=label, count=count, percentage=_percentage(count, total)) for label, count in rows]


def _percentage(part: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round((part / total) * 100, 2)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _bucket_label(value: datetime, interval: TrendInterval) -> str:
    value = _as_utc(value)
    if interval == TrendInterval.MONTH:
        return f"{value.year:04d}-{value.month:02d}"
    if interval == TrendInterval.WEEK:
        year, week, _ = value.isocalendar()
        return f"{year:04d}-W{week:02d}"
    return value.date().isoformat()
