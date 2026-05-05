# Analytics Dashboard And Reporting

Phase 10 adds backend-first analytics APIs. The goal is to turn stored feedback, analysis, workflow, review, and evaluation data into product and operational insights without adding a heavy frontend.

## Architecture

Analytics is a read model over existing tables:

1. API routes in `app/api/v1/analytics_routes.py` expose dashboard-friendly endpoints.
2. `AnalyticsService` validates time ranges and shapes responses.
3. `AnalyticsRepository` owns SQLAlchemy aggregate queries.
4. `AnalyticsReportGenerator` writes JSON and Markdown reports.

This keeps analytics separate from ingestion, analysis, workflow, and evaluation services. Those domains create operational data; analytics reads across them.

## Time Ranges

Most endpoints accept:

```text
start_date=2026-05-01T00:00:00Z
end_date=2026-05-06T23:59:59Z
interval=day
```

If no dates are supplied, the default range is the last 30 days. Trend intervals support `day`, `week`, and `month`.

## Endpoints

```text
GET /api/v1/analytics/summary
GET /api/v1/analytics/feedback-trends
GET /api/v1/analytics/sentiment-breakdown
GET /api/v1/analytics/category-breakdown
GET /api/v1/analytics/severity-breakdown
GET /api/v1/analytics/team-routing
GET /api/v1/analytics/tickets
GET /api/v1/analytics/reviews
GET /api/v1/analytics/evaluations
GET /api/v1/analytics/executive-summary
GET /api/v1/analytics/report?format=markdown
```

When Phase 9 auth is enabled, analytics endpoints require an API key with `analytics:read`. The default `admin`, `analyst`, and `service` roles can read analytics.

## Metrics

The summary endpoint includes:

- total feedback
- negative feedback percentage
- failed processing percentage
- average AI confidence score
- PII and prompt-injection counts
- source, status, sentiment, category, severity, and team breakdowns

Ticket analytics include open, escalated, duplicate, status, severity, and team metrics. Review analytics include pending review count, human review rate, status breakdown, and reason breakdown. Evaluation analytics expose the latest benchmark run and metric payload.

## Executive Summary

The executive summary is deterministic by default. It does not call a paid LLM. It summarizes the selected time range, highlights dominant categories/teams, flags risk areas, and recommends an operational focus.

## Reports

`GET /api/v1/analytics/report` writes both JSON and Markdown files under:

```text
analytics_reports/
```

The response returns the selected report path. JSON is useful for automation; Markdown is useful for demos and reviews.

## Verification

Normal tests remain Docker-free:

```powershell
$env:TMP="$PWD\.tmp"
$env:TEMP=$env:TMP
pytest
```

Live verification:

```powershell
.\scripts\verify_phase10_live.ps1
```

The live script starts PostgreSQL, Redis, and Qdrant, applies migrations, launches the API, creates sample feedback/analysis/workflow/evaluation data, calls analytics endpoints, generates a report, and runs pytest.

## Interview Talking Point

Phase 10 demonstrates a backend-for-frontend analytics layer: operational services write normalized domain data, while a dedicated read service aggregates across domains for dashboards and reports. This is the same separation used in many production SaaS systems before introducing heavier OLAP stores, materialized views, or BI tools.
