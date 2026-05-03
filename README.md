# FeedbackIQ

FeedbackIQ is a FastAPI backend for OCR-based feedback extraction, vector retrieval, RAG-style context building, sentiment analysis, and team routing.

## What It Does

- Extracts text from uploaded images or safe public image URLs.
- Preprocesses images with OpenCV before OCR.
- Uses Tesseract as the Phase 0 OCR engine.
- Retrieves related team knowledge with embeddings and FAISS.
- Builds RAG-style context from retrieved records.
- Runs sentiment analysis with Hugging Face.
- Routes feedback to a team using keyword routing.

## Architecture

FeedbackIQ is a modular monolith. API routes live in `app/api/v1`, shared backend infrastructure lives in `app/core`, and business logic lives in `app/domain`.

See `docs/architecture.md` and `docs/design-decisions.md` for the learning notes behind the structure.

## Setup

Use Python 3.11.

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
copy .env.example .env
uvicorn app.main:app --reload
```

API docs are available at:

```text
http://localhost:8000/docs
```

## API Examples

```bash
curl http://localhost:8000/api/v1/health
```

```bash
curl -X POST http://localhost:8000/api/v1/feedback/analyze ^
  -H "Content-Type: application/json" ^
  -d "{\"text\":\"Checkout payment failed during transaction.\",\"top_k\":3}"
```

## Tests

```bash
pytest
```

## Docker

```bash
copy .env.example .env
docker compose up --build
```

## Troubleshooting

- If OCR fails locally, install Tesseract and ensure it is on `PATH`.
- If FAISS or PyTorch installation fails, use Python 3.11.
- If model-backed endpoints are slow on first request, that is expected because models load lazily.

## Roadmap

Phase 0 keeps the system local and modular. Later phases can add Qdrant, stronger embedding models, advanced routing, dashboards, background jobs, and deployment infrastructure.
