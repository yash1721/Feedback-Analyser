# FeedbackIQ Architecture

FeedbackIQ is a modular monolith: one deployable API, split into clear modules by responsibility.

## Request Flow

1. `app.main` creates the FastAPI application.
2. `app.api.v1` receives HTTP requests and validates payloads.
3. `app.dependencies` wires routes to service objects.
4. Domain services coordinate business behavior.
5. Repositories isolate database queries and persistence.
6. Adapter classes call concrete tools such as Tesseract, sentence-transformers, FAISS, Hugging Face, local storage, or SQLAlchemy.
7. `app.core.responses` returns a consistent response shape.

## Why This Shape

Routes stay thin, services hold workflows, and adapters isolate external libraries. This makes the project easier to test and prepares it for later replacements like Qdrant or BGE-M3.

## Phase 1 Persistence Flow

Feedback records use a Controller-Service-Repository pattern:

1. `app.api.v1.feedback_records_routes` validates HTTP input and returns response DTOs.
2. `FeedbackService` applies lifecycle rules such as creating text feedback, marking failures, and attaching analysis results.
3. `FeedbackRepository` performs SQLAlchemy queries.
4. `app.db.session` provides one database session per request.
5. Alembic migrations version schema changes.

The important boundary is that API routes do not directly query the database, and SQLAlchemy ORM models are not treated as public API contracts.

## Storage Boundary

`StorageProvider` is an adapter interface. Phase 1 includes `LocalFileStorageProvider` only. A future S3 provider can implement the same interface without changing feedback business logic.

## Phase 2 Ingestion Flow

Multimodal ingestion uses a validation-first workflow:

1. `app.api.v1.ingestion_routes` accepts text, image upload, image URL, PDF upload, or CSV upload.
2. Pydantic schemas define JSON request and response contracts; multipart routes validate files in the route and service layer.
3. `MultimodalIngestionService` coordinates storage, extraction, normalization, and feedback persistence.
4. `StorageProvider` stores original uploaded or downloaded files and returns a storage key.
5. OCR and PDF extraction are adapter boundaries, so tests can use fakes and production can use Tesseract or `pypdf`.
6. `FeedbackService` creates `feedback_records` with `EXTRACTED` when text is ready for downstream analysis, or `FAILED` when extraction fails.

`raw_text` preserves directly supplied text or row text, `extracted_text` stores text produced by OCR/PDF/CSV extraction, and `normalized_text` stores cleaned text for later AI pipelines.

## Phase 3 Async Processing Flow

Phase 3 adds a producer-consumer workflow:

1. `app.api.v1.processing_routes` accepts enqueue and status requests.
2. `ProcessingService` validates lifecycle state and marks records `QUEUED`.
3. `ProcessingQueue` is an adapter; the current implementation submits Celery tasks.
4. Redis brokers tasks between the API process and Celery worker.
5. The worker receives only `feedback_id`, opens its own database session, and calls the same processing service logic.
6. `FeedbackAnalysisService` performs retrieval, sentiment analysis, and routing.
7. `FeedbackService` persists `PROCESSING`, `COMPLETED`, or `FAILED` state plus analysis or error fields.

PostgreSQL is the business source of truth. Celery task IDs are stored on `feedback_records.processing_task_id` for observability, but status polling reads from the database rather than treating Celery's result backend as the product state.

## Phase 4 Retrieval Flow

Phase 4 separates relational knowledge from vector indexing:

1. `knowledge_documents` stores source-level metadata.
2. `knowledge_chunks` stores retrievable text chunks and Qdrant point IDs.
3. BGE-M3 generates dense embeddings lazily.
4. Qdrant stores vectors with metadata payloads and performs HNSW/cosine search.
5. `RetrievalService` builds RAG context from retrieved chunks.
6. `retrieval_traces` and `retrieval_trace_items` persist evidence when requested.

FAISS remains available through the same `VectorStore` abstraction, but Qdrant is the production retrieval provider.

## Phase 5 Analysis Flow

Phase 5 adds an analysis pipeline:

1. `AnalysisService` loads a feedback record.
2. `RetrievalService` retrieves evidence and persists a retrieval trace.
3. `prompts.py` builds a versioned grounded prompt.
4. `LLMProvider` returns raw structured output.
5. `output_parser.py` validates the output with Pydantic.
6. `llm_analysis_runs` stores the audit record.
7. `feedback_records` stores the latest operational result.

The API and Celery worker both use the same service layer, so synchronous and asynchronous analysis follow the same rules.

## Phase 6 Workflow Automation Flow

Phase 6 turns validated analysis into operational work:

1. `WorkflowService` loads the feedback record and latest `llm_analysis_runs` row.
2. Duplicate detection checks whether the same category/team/title already has an open ticket.
3. `workflow_tickets` stores the actionable internal ticket.
4. Deterministic workflow rules decide whether the ticket needs escalation or human review.
5. `workflow_review_items` stores low-confidence or high-risk human-review work.
6. `workflow_audit_logs` records ticket, review, duplicate, escalation, and manual decision events.
7. `NotificationProvider` emits mock/log notifications through an adapter, with no real Slack/Jira/Zendesk calls by default.

The ticket is separate from the feedback record because feedback is source data, analysis is AI interpretation, and workflow is operational execution. Keeping those concerns apart makes retries, audit, and manual overrides easier to reason about.

## Phase 7 Evaluation Flow

Phase 7 adds an evaluation domain that measures the AI pipeline without mixing benchmark logic into retrieval, analysis, or workflow modules:

1. `EvaluationDatasetLoader` loads golden examples from JSON.
2. `EvaluationService` runs retrieval and LLM analysis for each example.
3. Pure metric functions compare retrieved evidence and structured predictions against expected labels.
4. `EvaluationRepository` persists datasets, runs, and per-example results.
5. `EvaluationReportGenerator` exports JSON and Markdown reports under the configured report directory.
6. `app.api.v1.evaluation_routes` exposes run creation, listing, detail, and report retrieval.

Evaluation does not create workflow tickets or production feedback records. It benchmarks predictions and derived workflow decisions so normal operational state remains separate from quality measurement.

## Phase 8 Observability Flow

Phase 8 adds cross-cutting diagnostics:

1. Correlation middleware reads or creates a correlation ID and returns it in response headers.
2. Logging config injects the correlation ID into plain or JSON logs.
3. HTTP metrics middleware records request count and latency by method, route template, and status.
4. Domain services emit bounded metrics for ingestion, retrieval, analysis, workflow, processing, and evaluation.
5. Health routes expose liveness and readiness checks.
6. Celery tasks log task-level feedback IDs, task IDs, retries, and failures.

Observability code is kept in `app.core` and middleware modules so business logic remains focused on product behavior.

## Phase 9 Security Flow

Phase 9 adds defense-in-depth controls:

1. API key dependencies protect ingestion, retrieval, analysis, workflow, evaluation, and security endpoints when `AUTH_ENABLED=true`.
2. Rate-limit middleware throttles requests by API key hash or client IP.
3. Ingestion detects PII and prompt-injection patterns before persistence.
4. Analysis uses sanitized text when configured and applies output guardrails after schema validation.
5. Security-sensitive decisions are persisted in `security_audit_logs` and exposed as Prometheus metrics.
