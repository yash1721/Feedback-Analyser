from collections.abc import Callable
from time import perf_counter

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest


HTTP_REQUESTS_TOTAL = Counter(
    "feedbackiq_http_requests_total",
    "Total HTTP requests.",
    ["method", "path", "status_code"],
)
HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "feedbackiq_http_request_duration_seconds",
    "HTTP request latency in seconds.",
    ["method", "path"],
)

INGESTION_REQUESTS_TOTAL = Counter(
    "feedbackiq_ingestion_requests_total",
    "Total ingestion requests.",
    ["source_type", "status"],
)
PROCESSING_JOBS_TOTAL = Counter(
    "feedbackiq_processing_jobs_total",
    "Total processing job events.",
    ["event", "status"],
)
PROCESSING_JOB_DURATION_SECONDS = Histogram(
    "feedbackiq_processing_job_duration_seconds",
    "Processing job duration in seconds.",
    ["status"],
)
PROCESSING_RECORD_STATUS_TOTAL = Gauge(
    "feedbackiq_processing_record_status_total",
    "Feedback record count by processing status.",
    ["status"],
)
RETRIEVAL_REQUESTS_TOTAL = Counter(
    "feedbackiq_retrieval_requests_total",
    "Total retrieval requests.",
    ["provider", "status"],
)
RETRIEVAL_LATENCY_SECONDS = Histogram(
    "feedbackiq_retrieval_latency_seconds",
    "Retrieval latency in seconds.",
    ["provider"],
)
RETRIEVAL_NO_RESULT_TOTAL = Counter(
    "feedbackiq_retrieval_no_result_total",
    "Total retrieval requests returning no results.",
    ["provider"],
)
ANALYSIS_RUNS_TOTAL = Counter(
    "feedbackiq_analysis_runs_total",
    "Total LLM analysis runs.",
    ["provider", "model", "status"],
)
ANALYSIS_INVALID_OUTPUT_TOTAL = Counter(
    "feedbackiq_analysis_invalid_output_total",
    "Total invalid structured analysis outputs.",
    ["provider", "model"],
)
ANALYSIS_LATENCY_SECONDS = Histogram(
    "feedbackiq_analysis_latency_seconds",
    "LLM analysis latency in seconds.",
    ["provider", "model"],
)
WORKFLOW_TICKETS_CREATED_TOTAL = Counter(
    "feedbackiq_workflow_tickets_created_total",
    "Total workflow tickets created.",
    ["status"],
)
WORKFLOW_REVIEWS_CREATED_TOTAL = Counter(
    "feedbackiq_workflow_reviews_created_total",
    "Total workflow review items created.",
)
WORKFLOW_ESCALATIONS_TOTAL = Counter(
    "feedbackiq_workflow_escalations_total",
    "Total workflow escalations.",
)
EVALUATION_RUNS_TOTAL = Counter(
    "feedbackiq_evaluation_runs_total",
    "Total evaluation runs.",
    ["provider", "status"],
)
EVALUATION_LATENCY_SECONDS = Histogram(
    "feedbackiq_evaluation_latency_seconds",
    "Evaluation run latency in seconds.",
    ["provider"],
)
AUTH_FAILURES_TOTAL = Counter(
    "feedbackiq_auth_failures_total",
    "Total API authentication failures.",
    ["reason"],
)
RATE_LIMITED_REQUESTS_TOTAL = Counter(
    "feedbackiq_rate_limited_requests_total",
    "Total rate-limited requests.",
    ["endpoint_group"],
)
PII_REDACTIONS_TOTAL = Counter(
    "feedbackiq_pii_redactions_total",
    "Total PII redaction events.",
    ["pii_type"],
)
PROMPT_INJECTION_DETECTED_TOTAL = Counter(
    "feedbackiq_prompt_injection_detected_total",
    "Total prompt injection detections.",
    ["risk_level"],
)
UNSAFE_URL_BLOCKED_TOTAL = Counter(
    "feedbackiq_unsafe_url_blocked_total",
    "Total unsafe URL blocks.",
    ["reason"],
)
FILE_UPLOAD_REJECTED_TOTAL = Counter(
    "feedbackiq_file_upload_rejected_total",
    "Total rejected file uploads.",
    ["reason"],
)
GUARDRAIL_VIOLATIONS_TOTAL = Counter(
    "feedbackiq_guardrail_violations_total",
    "Total output guardrail violations.",
    ["reason"],
)


def metrics_response() -> tuple[bytes, str]:
    return generate_latest(), CONTENT_TYPE_LATEST


def observe_duration_seconds(histogram: Histogram, labels: dict[str, str], func: Callable):
    start = perf_counter()
    try:
        return func()
    finally:
        histogram.labels(**labels).observe(perf_counter() - start)


class Timer:
    def __init__(self) -> None:
        self.start = perf_counter()

    def elapsed(self) -> float:
        return perf_counter() - self.start


def update_processing_status_gauges(counts: dict[str, int]) -> None:
    for status, count in counts.items():
        PROCESSING_RECORD_STATUS_TOTAL.labels(status=status).set(count)
