# FeedbackIQ Architecture

FeedbackIQ is a modular monolith: one deployable API, split into clear modules by responsibility.

## Request Flow

1. `app.main` creates the FastAPI application.
2. `app.api.v1` receives HTTP requests and validates payloads.
3. `app.dependencies` wires routes to service objects.
4. Domain services coordinate business behavior.
5. Adapter classes call concrete tools such as Tesseract, sentence-transformers, FAISS, or Hugging Face.
6. `app.core.responses` returns a consistent response shape.

## Why This Shape

Routes stay thin, services hold workflows, and adapters isolate external libraries. This makes the project easier to test and prepares it for later replacements like Qdrant or BGE-M3.

