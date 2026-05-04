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
