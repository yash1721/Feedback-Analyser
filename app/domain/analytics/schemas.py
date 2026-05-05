from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class TrendInterval(StrEnum):
    DAY = "day"
    WEEK = "week"
    MONTH = "month"


class AnalyticsTimeRange(BaseModel):
    start_date: datetime
    end_date: datetime
    interval: TrendInterval = TrendInterval.DAY


class BreakdownItem(BaseModel):
    label: str
    count: int
    percentage: float


class FeedbackTrendPoint(BaseModel):
    bucket: str
    count: int


class AnalyticsSummaryResponse(BaseModel):
    time_range: AnalyticsTimeRange
    total_feedback: int
    negative_feedback_percentage: float
    failed_processing_percentage: float
    average_confidence_score: float | None
    pii_detected_count: int
    prompt_injection_detected_count: int
    source_type_breakdown: list[BreakdownItem]
    processing_status_breakdown: list[BreakdownItem]
    sentiment_breakdown: list[BreakdownItem]
    category_breakdown: list[BreakdownItem]
    severity_breakdown: list[BreakdownItem]
    team_breakdown: list[BreakdownItem]


class FeedbackTrendResponse(BaseModel):
    time_range: AnalyticsTimeRange
    points: list[FeedbackTrendPoint]


class TicketAnalyticsResponse(BaseModel):
    time_range: AnalyticsTimeRange
    total_tickets: int
    open_ticket_count: int
    escalated_ticket_count: int
    duplicate_ticket_count: int
    escalation_rate: float
    status_breakdown: list[BreakdownItem]
    severity_breakdown: list[BreakdownItem]
    team_breakdown: list[BreakdownItem]


class ReviewAnalyticsResponse(BaseModel):
    time_range: AnalyticsTimeRange
    total_reviews: int
    pending_review_count: int
    human_review_rate: float
    status_breakdown: list[BreakdownItem]
    reason_breakdown: list[BreakdownItem]


class EvaluationAnalyticsResponse(BaseModel):
    latest_run_id: int | None
    dataset_name: str | None
    provider: str | None
    model_name: str | None
    created_at: datetime | None
    total_examples: int | None
    metrics: dict = Field(default_factory=dict)


class ExecutiveSummaryResponse(BaseModel):
    time_range: AnalyticsTimeRange
    summary_text: str
    key_findings: list[str]
    recommended_focus: str
    risk_flags: list[str]
    generated_from: dict


class AnalyticsReportResponse(BaseModel):
    format: str
    report_path: str
    generated_at: datetime
    executive_summary: ExecutiveSummaryResponse
