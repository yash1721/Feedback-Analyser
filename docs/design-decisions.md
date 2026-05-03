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
