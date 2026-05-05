# Design Decisions

## FastAPI Instead Of Flask

FastAPI gives request validation, OpenAPI documentation, dependency injection, and strong test support. That makes it a better fit for a production backend learning project.

## Adapter Pattern

OCR, embeddings, vector storage, sentiment, and routing are behind interfaces. The concrete Phase 0 implementations are Tesseract, sentence-transformers, FAISS, Hugging Face, and keyword routing.

## Lazy Model Loading

Heavy AI models are loaded only when their services are first used. This keeps startup and basic tests lighter.

## Local FAISS For Phase 0

FAISS keeps retrieval local and close to the original prototype. The `VectorStore` interface allows Qdrant to be added later without rewriting API routes.

## PostgreSQL With SQLite Tests

Phase 1 uses PostgreSQL for real local app usage because it is closer to production backend systems: stronger concurrency, richer SQL behavior, and a deployment path that maps well to managed databases. Tests use SQLite because they need to be fast, isolated, and independent of Docker.

## SQLAlchemy And Alembic

SQLAlchemy 2.0 is the ORM layer and Alembic owns schema migrations. This is more verbose than SQLModel, but it is widely used in production Python backends and gives clear separation between database models, queries, and API DTOs.

## Controller-Service-Repository

Feedback record routes are controllers. They validate requests and format responses. `FeedbackService` owns workflow decisions. `FeedbackRepository` owns SQLAlchemy queries. This prevents route handlers from becoming difficult-to-test database scripts.

## DTOs Instead Of Returning ORM Models

Pydantic schemas are the API contract. SQLAlchemy models are the database contract. Keeping them separate lets the database evolve without accidentally changing public response shapes.

## Store Metadata, Not Full RAG Context

Phase 1 stores feedback metadata, sentiment, routing, and processing state. It does not store full RAG context yet because retrieval traces and evidence deserve a separate design later.

## Local Storage Adapter

Phase 1 adds a storage interface and local implementation only. S3 is intentionally not implemented yet, but the adapter boundary keeps that future change small.

## Dedicated Ingestion APIs

Phase 2 adds `/ingestion/*` endpoints instead of expanding `/ocr/*` or `/feedback-records/*`. OCR remains extract-only, feedback records remain persistence-oriented, and ingestion becomes the workflow boundary that validates input, stores source files, extracts text, normalizes text, and persists lifecycle state.

## Extracted Status

`EXTRACTED` separates successful ingestion from completed analysis. `PENDING` still means accepted but not processed, `PROCESSING` means an active workflow step, `EXTRACTED` means normalized text is ready for later analysis, `COMPLETED` means analysis has finished, and `FAILED` means ingestion or analysis failed.

## PDF Extraction Choice

Phase 2 uses `pypdf` because it is lightweight, pure Python, simple to test, and good enough for text-based PDFs. Layout-heavy or scanned PDFs can be handled later with `pdfplumber`, PyMuPDF, or OCR-based PDF processing.

## Bulk CSV Partial Success

CSV ingestion creates records for valid rows and returns row-level errors for invalid rows. This mirrors production import behavior better than rejecting an entire file because one row is blank.

## Celery And Redis For Phase 3

Phase 3 uses Celery with Redis because it demonstrates real queue-backed workers, retries, task IDs, and separate process lifecycles while staying easy to run locally with Docker Compose. FastAPI `BackgroundTasks` was not chosen because work can be lost when the API process restarts and it does not provide durable broker semantics.

## Feedback Records As Processing State

`feedback_records` remains the main source of truth. Phase 3 adds `QUEUED` and `processing_task_id` instead of introducing a separate jobs table. This is enough because each feedback record has one active processing workflow. A future jobs table can be added when attempt history, cancellation, or multiple workflow types become requirements.

## Status-Based Idempotency

Enqueue uses record state for idempotency. `PENDING` and `EXTRACTED` records can move to `QUEUED`; `QUEUED`, `PROCESSING`, and `COMPLETED` records return their current state without creating duplicate work. `FAILED` is terminal for now so accidental retries do not hide ingestion or model failures.

## Bounded Retry Policy

Celery retries transient processing failures with bounded exponential backoff. Permanent problems such as missing text or invalid lifecycle state are persisted as `FAILED` without retry. This prevents temporary model/provider issues from becoming immediate final failures while avoiding infinite retry loops for bad data.

## Qdrant For Production Retrieval

Phase 4 uses Qdrant because it provides an API-based vector database, Docker-friendly local development, HNSW indexing, cosine similarity, and metadata payload filtering. FAISS stays available for local/prototype retrieval, but Qdrant gives a stronger production backend architecture.

## BGE-M3 Embeddings

BGE-M3 is the default Phase 4 embedding model because it is a strong open-source multilingual retrieval model and is better suited to English/Hindi feedback than MiniLM. It is loaded lazily so app import and Docker-free tests remain fast.

## Retrieval Evidence

Retrieval traces are stored in separate tables instead of `feedback_records`. Evidence can be many-to-one with feedback records, can grow over time, and includes scores/ranks/metadata that should not bloat the feedback row.

## LLM Provider Abstraction

Phase 5 uses an `LLMProvider` adapter instead of calling an external model directly. The default provider is local and rule-based so tests and live verification do not need paid APIs. External providers can be added later behind the same interface.

## Structured Analysis Output

LLM output is treated as untrusted input. It must parse as JSON and validate against `StructuredAnalysisOutput` before updating feedback records. Invalid output is stored as an invalid analysis run, preserving auditability without corrupting operational fields.

## Analysis Runs And Latest Fields

`llm_analysis_runs` stores detailed audit history. `feedback_records` stores latest fields such as category, severity, summary, recommended action, confidence, sentiment, and routed team for fast operational reads.

## Internal Ticketing Before External Integrations

Phase 6 creates internal workflow tickets before adding Jira, Slack, or Zendesk. This keeps local verification credential-free, lets tests use a mock notification provider, and creates a clean adapter boundary for future external systems.

## Human Review For Risky AI Output

High-severity analysis, low-confidence output, and missing routed teams create `workflow_review_items`. Human review is intentionally deterministic and explicit because enterprise AI systems need a safe override path instead of blindly acting on every model result.

## Workflow Audit Logs

Ticket creation, escalation, duplicate linking, and review decisions are written to `workflow_audit_logs`. Audit events are separate from tickets so the current ticket row stays compact while historical decisions remain available for debugging and compliance-style explanations.

## Simple Duplicate Detection First

Phase 6 uses deterministic duplicate detection based on category, assigned team, and ticket title. Vector clustering is deferred because a simple rule is predictable, testable, and enough to prove the workflow pattern without adding Phase 7-style analytics complexity.

## Configurable Workflow Policy

SLA hours, low-confidence threshold, notification provider, and automatic ticket creation are environment-driven. The default `WORKFLOW_AUTO_CREATE_TICKETS=false` keeps workflow creation manual unless the operator opts into automatic post-analysis ticketing.

## API Keys Before Full IAM

Phase 9 uses API keys and simple roles instead of OAuth or SSO. This protects local/demo APIs, keeps tests deterministic, and leaves full identity management for a future deployment phase.

## Best-Effort PII Redaction

PII detection is regex/Luhn based. It is intentionally local and deterministic, and the docs avoid claiming complete DLP coverage. Existing raw fields remain for compatibility while sanitized text is available for prompts.

## Security Audit Logs

Security audit logs are separate from workflow audit logs. Workflow audit explains ticket decisions; security audit explains allowed, blocked, redacted, and suspicious actions.
# Phase 7 Evaluation Decisions

## Golden Dataset First

FeedbackIQ uses a small JSON seed dataset before adding larger benchmark sets. This makes quality measurement reproducible and keeps normal tests fast. Without golden labels, we could only verify that the system returns output, not whether the output is correct.

## DB Run History Plus File Reports

Evaluation runs and items are stored in PostgreSQL so results are queryable through the API. JSON and Markdown reports are also written to disk because they are easier to inspect during local demos and interviews.

The alternative was reports-only. That is simpler, but it loses experiment history and API access.

## Lightweight Metrics

Phase 7 starts with accuracy, precision@k, recall@k, hit@k, MRR, groundedness status, failure rates, and latency percentiles. These metrics map directly to current FeedbackIQ behavior and stay deterministic in tests.

Advanced external evaluation tools are intentionally deferred because they would add dependency and cost before the baseline measurement layer is stable.

## No Operational Mutation During Evaluation

Evaluation runs do not create real workflow tickets or customer feedback records. They call retrieval and provider logic, compare predictions with expected labels, and derive workflow expectations in metrics. This keeps benchmark state separate from production state.

# Phase 8 Observability Decisions

## Stdlib JSON Logging

FeedbackIQ uses Python's standard logging with a custom JSON formatter instead of introducing a new logging framework. This keeps the dependency footprint small and works with Uvicorn and Celery.

## Prometheus Metrics

Metrics are Prometheus-compatible and exposed at `/metrics`. Counters track events, histograms track latency, and gauges track current state. Labels are bounded to avoid high-cardinality production metrics.

## Correlation IDs

The app preserves incoming `X-Correlation-ID` or `X-Request-ID`, generates one when missing, stores it in a context variable, and returns it in response headers. This allows request and service logs to be connected.

## OpenTelemetry Optional

OpenTelemetry setup is disabled by default. Phase 8 prioritizes correlation IDs, logs, metrics, and readiness because they give immediate operational value without requiring a collector.
