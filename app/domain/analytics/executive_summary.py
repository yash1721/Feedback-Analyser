from app.domain.analytics.schemas import AnalyticsSummaryResponse, EvaluationAnalyticsResponse, ExecutiveSummaryResponse, TicketAnalyticsResponse, ReviewAnalyticsResponse


def build_executive_summary(
    *,
    summary: AnalyticsSummaryResponse,
    tickets: TicketAnalyticsResponse,
    reviews: ReviewAnalyticsResponse,
    evaluation: EvaluationAnalyticsResponse,
) -> ExecutiveSummaryResponse:
    top_category = _top_label(summary.category_breakdown)
    top_team = _top_label(summary.team_breakdown)
    key_findings = [
        f"Total feedback: {summary.total_feedback}",
        f"Negative feedback: {summary.negative_feedback_percentage:.1f}%",
        f"Top category: {top_category}",
        f"Most impacted team: {top_team}",
        f"Escalated tickets: {tickets.escalated_ticket_count}",
        f"Pending reviews: {reviews.pending_review_count}",
    ]
    risk_flags: list[str] = []
    if summary.negative_feedback_percentage >= 40:
        risk_flags.append("High negative feedback percentage.")
    if tickets.escalated_ticket_count > 0:
        risk_flags.append("Escalated tickets require leadership attention.")
    if reviews.pending_review_count > 0:
        risk_flags.append("Human review backlog exists.")
    if evaluation.metrics:
        exact_match = (evaluation.metrics.get("analysis") or {}).get("exact_label_match_rate")
        if exact_match is not None and exact_match < 0.8:
            risk_flags.append("Latest evaluation exact label match is below 0.8.")
    focus = _recommended_focus(top_category=top_category, top_team=top_team, tickets=tickets, reviews=reviews)
    text = (
        f"Over the selected period, FeedbackIQ processed {summary.total_feedback} feedback items. "
        f"Negative feedback represented {summary.negative_feedback_percentage:.1f}%. "
        f"The top category was {top_category}, and the most impacted team was {top_team}. "
        f"There are {tickets.escalated_ticket_count} escalated tickets and {reviews.pending_review_count} pending reviews. "
        f"Recommended focus: {focus}"
    )
    return ExecutiveSummaryResponse(
        time_range=summary.time_range,
        summary_text=text,
        key_findings=key_findings,
        recommended_focus=focus,
        risk_flags=risk_flags,
        generated_from={
            "summary": "feedback_records",
            "tickets": "workflow_tickets",
            "reviews": "workflow_review_items",
            "evaluation": "evaluation_runs",
        },
    )


def _top_label(items) -> str:
    return items[0].label if items else "NONE"


def _recommended_focus(*, top_category: str, top_team: str, tickets: TicketAnalyticsResponse, reviews: ReviewAnalyticsResponse) -> str:
    if tickets.escalated_ticket_count:
        return f"Resolve escalated {top_category.lower()} issues with {top_team}."
    if reviews.pending_review_count:
        return "Reduce the pending human review backlog."
    if top_category != "NONE":
        return f"Monitor {top_category.lower()} feedback trends and routing load for {top_team}."
    return "Continue collecting feedback to establish a reliable trend baseline."
