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
- Persists feedback metadata with SQLAlchemy and PostgreSQL.
- Exposes feedback-record APIs with pagination and filtering.

## Architecture

FeedbackIQ is a modular monolith. API routes live in `app/api/v1`, shared backend infrastructure lives in `app/core`, and business logic lives in `app/domain`.

Phase 1 uses a Controller-Service-Repository shape:

- Controllers in `app/api/v1` handle HTTP input and output.
- Services in `app/domain/*/service.py` own business workflows.
- Repositories in `app/domain/*/repository.py` own database queries.
- SQLAlchemy models define database tables; Pydantic schemas define API contracts.
- Storage providers hide local file storage behind an interface that can later be replaced by S3.

See `docs/architecture.md` and `docs/design-decisions.md` for the design notes.

## Windows Setup

Use Python 3.11. The current dependency set is not verified on Python 3.13.

Install Python 3.11 from `https://www.python.org/downloads/release/python-3119/`, then verify:

```powershell
py -3.11 --version
```

Create and activate a virtual environment:

```powershell
py -3.11 -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
copy .env.example .env
```

Run PostgreSQL locally with Docker Compose:

```powershell
docker compose up feedbackiq-db -d
```

Apply database migrations:

```powershell
alembic upgrade head
```

Install Tesseract for OCR. On Windows, install the UB Mannheim build from `https://github.com/UB-Mannheim/tesseract/wiki`, select English and Hindi language data if needed, and ensure the install directory is on `PATH`.

Verify Tesseract:

```powershell
tesseract --version
python -c "import pytesseract; print(pytesseract.get_tesseract_version())"
```

The retrieval and feedback endpoints download Hugging Face models on first use:

- `sentence-transformers/all-MiniLM-L6-v2`
- `distilbert-base-uncased-finetuned-sst-2-english`

First use requires internet access and can be slow. Offline machines need the models already present in the Hugging Face cache or configured to local model paths through `.env`.

## Start The App

```powershell
uvicorn app.main:app --reload
```

API docs are available at:

```text
http://localhost:8000/docs
```

## Tests

```powershell
pytest
```

The project includes `pytest.ini`, so no `PYTHONPATH` workaround is required.

Tests use SQLite and dependency overrides, so they do not require Postgres, Tesseract, or Hugging Face model downloads.

## API Examples

Health:

```powershell
curl.exe http://localhost:8000/api/v1/health
```

Expected response:

```json
{
  "success": true,
  "message": "success",
  "data": {
    "status": "ok",
    "service": "FeedbackIQ",
    "environment": "local"
  },
  "error": null
}
```

OCR upload:

```powershell
curl.exe -X POST http://localhost:8000/api/v1/ocr/extract -F "file=@Images/letter-1.png;type=image/png"
```

Expected response shape:

```json
{
  "success": true,
  "message": "success",
  "data": {
    "text": "extracted text"
  },
  "error": null
}
```

Retrieval:

```powershell
Invoke-RestMethod -Uri http://localhost:8000/api/v1/retrieval/search -Method Post -ContentType "application/json" -Body '{"query":"checkout payment failed","top_k":2}'
```

Expected response shape:

```json
{
  "success": true,
  "message": "success",
  "data": {
    "query": "checkout payment failed",
    "results": [
      {
        "text": "The Payment Team introduced instant refunds, reducing customer complaints by 18%.",
        "score": 0.82
      }
    ],
    "rag_context": "Relevant context for: checkout payment failed\n..."
  },
  "error": null
}
```

Feedback analysis:

```powershell
Invoke-RestMethod -Uri http://localhost:8000/api/v1/feedback/analyze -Method Post -ContentType "application/json" -Body '{"text":"Checkout payment failed during transaction.","top_k":2}'
```

Expected response shape:

```json
{
  "success": true,
  "message": "success",
  "data": {
    "text": "Checkout payment failed during transaction.",
    "sentiment": {
      "label": "NEGATIVE",
      "score": 0.99
    },
    "routing": {
      "team": "Payment Team",
      "matched_keyword": "payment"
    },
    "retrieval": [
      {
        "text": "The Payment Team introduced instant refunds, reducing customer complaints by 18%.",
        "score": 0.82
      }
    ],
    "rag_context": "Relevant context for: Checkout payment failed during transaction.\n..."
  },
  "error": null
}
```

Persisted feedback record:

```powershell
Invoke-RestMethod -Uri http://localhost:8000/api/v1/feedback-records -Method Post -ContentType "application/json" -Body '{"text":"Checkout payment failed during transaction."}'
```

List feedback records:

```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/feedback-records?limit=20&offset=0&processing_status=PENDING" -Method Get
```

Analyze and persist:

```powershell
Invoke-RestMethod -Uri http://localhost:8000/api/v1/feedback/analyze -Method Post -ContentType "application/json" -Body '{"text":"Checkout payment failed during transaction.","top_k":2,"persist":true}'
```

When `persist` is omitted or `false`, `/feedback/analyze` keeps the original stateless behavior. When `persist` is `true`, the response also includes `record_id`.

Common error response:

```json
{
  "success": false,
  "message": "Invalid request payload.",
  "data": null,
  "error": {
    "code": "validation_error",
    "details": []
  }
}
```

Model or OCR setup error examples:

```json
{
  "success": false,
  "message": "sentence-transformers is not installed.",
  "data": null,
  "error": {
    "code": "model_unavailable",
    "details": null
  }
}
```

```json
{
  "success": false,
  "message": "Tesseract binary is not installed or not available on PATH.",
  "data": null,
  "error": {
    "code": "ocr_error",
    "details": null
  }
}
```

## Docker

```powershell
copy .env.example .env
docker compose up --build
```

In a fresh database, run migrations inside the API container:

```powershell
docker compose exec feedbackiq-api alembic upgrade head
```

## Phase 1.1.5 Live Runtime Verification

This gate verifies the real PostgreSQL path. Normal `pytest` still uses SQLite and does not require Docker.

Prerequisites:

- Docker Desktop is installed and running.
- Python 3.11 virtual environment is active.
- Dependencies are installed with `pip install -r requirements-dev.txt`.
- `.env` exists and contains `DATABASE_URL=postgresql+psycopg://feedbackiq:feedbackiq@localhost:5432/feedbackiq`.

Run the database:

```powershell
docker compose up feedbackiq-db -d
docker compose ps
```

Expected: `feedbackiq-db` is running and reports healthy after the healthcheck passes.

Apply migrations against live PostgreSQL:

```powershell
python -m alembic upgrade head
```

Verify the feedback table exists:

```powershell
docker compose exec feedbackiq-db psql -U feedbackiq -d feedbackiq -c "\dt"
```

Start the API:

```powershell
uvicorn app.main:app --reload
```

In a second PowerShell window, verify the records API:

```powershell
$created = Invoke-RestMethod `
  -Uri http://localhost:8000/api/v1/feedback-records `
  -Method Post `
  -ContentType "application/json" `
  -Body '{"text":"Checkout payment failed during live verification."}'

$feedbackId = $created.data.id

Invoke-RestMethod "http://localhost:8000/api/v1/feedback-records/$feedbackId"
Invoke-RestMethod "http://localhost:8000/api/v1/feedback-records?limit=10&offset=0"

Invoke-RestMethod `
  -Uri "http://localhost:8000/api/v1/feedback-records/$feedbackId/status" `
  -Method Patch `
  -ContentType "application/json" `
  -Body '{"processing_status":"FAILED","error_code":"live_verification","error_message":"Phase 1.1.5 live verification status update."}'
```

Run normal tests:

```powershell
pytest
```

Optional one-command helper:

```powershell
.\scripts\verify_phase1_live.ps1
```

## Troubleshooting

- Use Python 3.11 for local setup.
- If OCR fails locally, verify `tesseract --version` and `pytesseract.get_tesseract_version()`.
- If FAISS, PyTorch, or sentence-transformers installation fails, recreate the virtual environment with Python 3.11.
- If model-backed endpoints are slow on first request, wait for the initial Hugging Face model download.
