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
