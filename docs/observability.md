# Observability, Monitoring, and Diagnostics

Phase 8 adds production-style diagnostics to FeedbackIQ: structured logs, correlation IDs, Prometheus-compatible metrics, readiness checks, safe text logging, and worker instrumentation.

## Correlation IDs

Every API request receives a correlation ID. FeedbackIQ reads `X-Correlation-ID` or `X-Request-ID` when provided, otherwise it generates a UUID.

Responses include:

```text
X-Correlation-ID
X-Request-ID
```

The value is stored in a context variable so logs created in routes, services, and workers can include the same identifier.

## Structured Logs

Logging is configured through environment variables:

```text
LOG_LEVEL=INFO
LOG_FORMAT=plain
SERVICE_NAME=FeedbackIQ
```

Set `LOG_FORMAT=json` for machine-readable logs. JSON logs include timestamp, level, logger, message, service, environment, correlation ID, and safe extra fields.

Do not log full feedback text, uploaded file contents, or secrets. Use IDs, lengths, hashes, previews, provider names, error codes, and durations.

## Metrics

FeedbackIQ exposes Prometheus metrics at:

```text
GET /metrics
```

Important metrics include:

- `feedbackiq_http_requests_total`
- `feedbackiq_http_request_duration_seconds`
- `feedbackiq_ingestion_requests_total`
- `feedbackiq_processing_jobs_total`
- `feedbackiq_processing_job_duration_seconds`
- `feedbackiq_processing_record_status_total`
- `feedbackiq_retrieval_requests_total`
- `feedbackiq_retrieval_latency_seconds`
- `feedbackiq_retrieval_no_result_total`
- `feedbackiq_analysis_runs_total`
- `feedbackiq_analysis_invalid_output_total`
- `feedbackiq_analysis_latency_seconds`
- `feedbackiq_workflow_tickets_created_total`
- `feedbackiq_workflow_reviews_created_total`
- `feedbackiq_evaluation_runs_total`
- `feedbackiq_evaluation_latency_seconds`

Counters measure how often something happened. Histograms measure distributions such as p95/p99 latency. Gauges measure current values, such as records by processing status.

## Health Checks

Existing health:

```text
GET /api/v1/health
```

Liveness:

```text
GET /api/v1/health/live
```

Readiness:

```text
GET /api/v1/health/ready
```

Readiness checks PostgreSQL, Redis, and Qdrant when Qdrant is configured. Liveness only confirms the app process is running.

## Worker Observability

Celery tasks log task start, retry, permanent failure, exhausted retries, and final status. Logs include `task_id`, `feedback_id`, and the current correlation ID where available.

## Safe Logging

`app.core.redaction.redact_text_preview` returns:

- text length
- SHA-256 hash
- short redacted preview

It masks obvious emails and phone numbers.

## Live Verification

Run:

```powershell
.\scripts\verify_phase8_live.ps1
```

The script starts Docker services, runs migrations, starts the API, verifies health/readiness/correlation headers, exercises ingestion/retrieval/analysis/workflow/evaluation, checks `/metrics`, and runs pytest.

## Interview Story

The SDE-2 talking point: FeedbackIQ treats observability as a first-class backend feature. Requests have correlation IDs, logs are structured, metrics expose latency and failure rates, readiness separates dependency health from process liveness, and async worker failures can be connected back to feedback records and tasks.
