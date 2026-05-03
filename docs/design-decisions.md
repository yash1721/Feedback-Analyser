# Design Decisions

## FastAPI Instead Of Flask

FastAPI gives request validation, OpenAPI documentation, dependency injection, and strong test support. That makes it a better fit for a production backend learning project.

## Adapter Pattern

OCR, embeddings, vector storage, sentiment, and routing are behind interfaces. The concrete Phase 0 implementations are Tesseract, sentence-transformers, FAISS, Hugging Face, and keyword routing.

## Lazy Model Loading

Heavy AI models are loaded only when their services are first used. This keeps startup and basic tests lighter.

## Local FAISS For Phase 0

FAISS keeps retrieval local and close to the original prototype. The `VectorStore` interface allows Qdrant to be added later without rewriting API routes.

