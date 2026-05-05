from datetime import datetime

from fastapi import APIRouter, Depends, Query

from app.core.auth import require_permission
from app.core.responses import success_response
from app.dependencies import get_analytics_service
from app.domain.analytics.schemas import TrendInterval
from app.domain.analytics.service import AnalyticsService

router = APIRouter(
    prefix="/analytics",
    tags=["analytics"],
    dependencies=[Depends(require_permission("analytics:read"))],
)


def _time_range(
    start_date: datetime | None = Query(default=None),
    end_date: datetime | None = Query(default=None),
    interval: TrendInterval = Query(default=TrendInterval.DAY),
    service: AnalyticsService = Depends(get_analytics_service),
):
    return service.time_range(start_date=start_date, end_date=end_date, interval=interval)


@router.get("/summary")
def analytics_summary(
    time_range=Depends(_time_range),
    service: AnalyticsService = Depends(get_analytics_service),
) -> dict:
    return success_response(data=service.summary(time_range).model_dump(mode="json"))


@router.get("/feedback-trends")
def feedback_trends(
    time_range=Depends(_time_range),
    service: AnalyticsService = Depends(get_analytics_service),
) -> dict:
    return success_response(data=service.feedback_trends(time_range).model_dump(mode="json"))


@router.get("/sentiment-breakdown")
def sentiment_breakdown(
    time_range=Depends(_time_range),
    service: AnalyticsService = Depends(get_analytics_service),
) -> dict:
    return success_response(data={"items": [item.model_dump(mode="json") for item in service.sentiment_breakdown(time_range)]})


@router.get("/category-breakdown")
def category_breakdown(
    time_range=Depends(_time_range),
    service: AnalyticsService = Depends(get_analytics_service),
) -> dict:
    return success_response(data={"items": [item.model_dump(mode="json") for item in service.category_breakdown(time_range)]})


@router.get("/severity-breakdown")
def severity_breakdown(
    time_range=Depends(_time_range),
    service: AnalyticsService = Depends(get_analytics_service),
) -> dict:
    return success_response(data={"items": [item.model_dump(mode="json") for item in service.severity_breakdown(time_range)]})


@router.get("/team-routing")
def team_routing(
    time_range=Depends(_time_range),
    service: AnalyticsService = Depends(get_analytics_service),
) -> dict:
    return success_response(data={"items": [item.model_dump(mode="json") for item in service.team_routing_breakdown(time_range)]})


@router.get("/tickets")
def ticket_analytics(
    time_range=Depends(_time_range),
    service: AnalyticsService = Depends(get_analytics_service),
) -> dict:
    return success_response(data=service.tickets(time_range).model_dump(mode="json"))


@router.get("/reviews")
def review_analytics(
    time_range=Depends(_time_range),
    service: AnalyticsService = Depends(get_analytics_service),
) -> dict:
    return success_response(data=service.reviews(time_range).model_dump(mode="json"))


@router.get("/evaluations")
def evaluation_analytics(service: AnalyticsService = Depends(get_analytics_service)) -> dict:
    return success_response(data=service.evaluations().model_dump(mode="json"))


@router.get("/executive-summary")
def executive_summary(
    time_range=Depends(_time_range),
    service: AnalyticsService = Depends(get_analytics_service),
) -> dict:
    return success_response(data=service.executive_summary(time_range).model_dump(mode="json"))


@router.get("/report")
def analytics_report(
    format: str = Query(default="markdown", pattern="^(markdown|json)$"),
    time_range=Depends(_time_range),
    service: AnalyticsService = Depends(get_analytics_service),
) -> dict:
    return success_response(data=service.report(time_range, format=format).model_dump(mode="json"))
