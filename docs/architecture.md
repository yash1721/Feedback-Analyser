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
