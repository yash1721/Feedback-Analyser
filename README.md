# FeedbackIQ

## Phase 7: Evaluation and LLMOps

FeedbackIQ now includes a lightweight evaluation layer for RAG and LLM quality. It supports golden datasets, retrieval metrics, analysis label accuracy, workflow decision checks, groundedness checks, latency summaries, persisted benchmark runs, and JSON/Markdown reports.

Run the default benchmark:

```powershell
python .\scripts\run_evaluation.py --provider rule_based --top-k 3
```

Use `--live-retrieval` when you want the CLI to call the configured vector and embedding providers instead of the built-in fixture retriever.

API entry point:

```text
POST /api/v1/evaluations/runs
```

Detailed notes are in `docs/evaluation-and-llmops.md`.

## Phase 8: Observability

FeedbackIQ exposes structured logging, correlation IDs, readiness/liveness checks, and Prometheus-compatible metrics.

```powershell
curl.exe http://localhost:8000/metrics
curl.exe http://localhost:8000/api/v1/health/live
curl.exe http://localhost:8000/api/v1/health/ready
```

Detailed notes are in `docs/observability.md`.

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
- Ingests feedback from text, image uploads, safe image URLs, PDFs, and CSV files.
- Enqueues feedback records for background processing with Celery and Redis.
- Persists async processing status, task IDs, analysis results, and failures.
- Indexes knowledge documents into Qdrant for metadata-aware retrieval.
- Stores retrieval traces as RAG evidence.
- Produces RAG-grounded structured feedback analysis with a local LLM provider abstraction.
- Creates internal workflow tickets, escalations, human reviews, audit logs, and mock/log notifications from analysis results.
- Adds API key protection, rate limiting, PII redaction, prompt-injection detection, output guardrails, and security audit logs.

## Architecture

FeedbackIQ is a modular monolith. API routes live in `app/api/v1`, shared backend infrastructure lives in `app/core`, and business logic lives in `app/domain`.

Phase 1 uses a Controller-Service-Repository shape:

- Controllers in `app/api/v1` handle HTTP input and output.
- Services in `app/domain/*/service.py` own business workflows.
- Repositories in `app/domain/*/repository.py` own database queries.
- SQLAlchemy models define database tables; Pydantic schemas define API contracts.
- Storage providers hide local file storage behind an interface that can later be replaced by S3.

See `docs/architecture.md` and `docs/design-decisions.md` for the design notes.

Phase 3 adds queue-based processing. The API enqueues work, a Celery worker consumes it, and PostgreSQL remains the source of truth for `QUEUED`, `PROCESSING`, `COMPLETED`, and `FAILED` states.

Phase 4 adds Qdrant-backed retrieval. PostgreSQL stores documents, chunks, and retrieval evidence; Qdrant stores vector points and metadata payloads for fast semantic search.

Phase 5 adds structured analysis. Feedback records are analyzed with retrieved evidence, validated JSON output, analysis run history, and latest operational fields on `feedback_records`.

Phase 6 adds workflow automation. The latest analysis can create an internal ticket, apply deterministic escalation/review rules, detect simple duplicates, persist audit logs, and notify through a local adapter.

Phase 9 adds security and privacy guardrails. Auth is disabled by default for local development, but API keys, roles, rate limiting, redaction, prompt-injection detection, security audit logs, and security metrics can be enabled through environment variables.

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
docker compose up feedbackiq-db feedbackiq-redis feedbackiq-qdrant -d
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

Start the background worker in a second terminal:

```powershell
celery -A app.workers.celery_app worker --loglevel=info --pool=solo
```

`--pool=solo` is recommended for local Windows development.

Workflow automation is manual by default. To create a ticket after analysis:

```powershell
Invoke-RestMethod -Uri http://localhost:8000/api/v1/workflows/feedback-records/1/create-ticket -Method Post
```

Set `WORKFLOW_AUTO_CREATE_TICKETS=true` only if you want async processing to create tickets automatically after successful analysis.

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

Live Phase 6 verification:

```powershell
.\scripts\verify_phase6_live.ps1
```

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

Ingest text without running analysis:

```powershell
Invoke-RestMethod -Uri http://localhost:8000/api/v1/ingestion/text -Method Post -ContentType "application/json" -Body '{"text":"Checkout payment failed during transaction."}'
```

Ingest an image, PDF, or CSV:

```powershell
curl.exe -X POST http://localhost:8000/api/v1/ingestion/image -F "file=@Images/letter-1.png;type=image/png"
curl.exe -X POST http://localhost:8000/api/v1/ingestion/pdf -F "file=@data.pdf;type=application/pdf"
curl.exe -X POST http://localhost:8000/api/v1/ingestion/csv -F "file=@feedback.csv;type=text/csv"
```

Ingest a public image URL:

```powershell
Invoke-RestMethod -Uri http://localhost:8000/api/v1/ingestion/image-url -Method Post -ContentType "application/json" -Body '{"url":"https://example.com/image.png"}'
```

Successful ingestion returns `feedback_id`, `source_type`, `processing_status`, extracted text, normalized text, and the stored file key when a file was stored. File-based extraction failures are persisted as `FAILED` feedback records with `error_code` and `error_message`.

Enqueue an ingested record for async processing:

```powershell
$created = Invoke-RestMethod -Uri http://localhost:8000/api/v1/ingestion/text -Method Post -ContentType "application/json" -Body '{"text":"Checkout payment failed during transaction."}'
$feedbackId = $created.data.feedback_id
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/processing/feedback-records/$feedbackId/enqueue" -Method Post
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/processing/feedback-records/$feedbackId/status" -Method Get
```

Repeated enqueue calls are idempotent for records that are already `QUEUED`, `PROCESSING`, or `COMPLETED`.

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

Docker Compose includes `feedbackiq-api`, `feedbackiq-worker`, `feedbackiq-db`, and `feedbackiq-redis`.

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

## Phase 3 Live Verification

Phase 3 verifies PostgreSQL, Redis, FastAPI, and Celery together:

```powershell
.\scripts\verify_phase3_live.ps1
```

The script starts PostgreSQL and Redis, applies migrations, starts the API and worker, ingests text, enqueues processing, polls status, and runs the Docker-free test suite.

## Phase 4 Live Verification

Phase 4 verifies PostgreSQL, Qdrant, FastAPI, indexing, metadata-filtered retrieval, trace persistence, and pytest:

```powershell
.\scripts\verify_phase4_live.ps1
```

First use of BGE-M3 may download a large model.

## Phase 5 Live Verification

Phase 5 verifies RAG-grounded analysis and async integration with the local `rule_based` provider:

```powershell
.\scripts\verify_phase5_live.ps1
```

## Troubleshooting

- Use Python 3.11 for local setup.
- If OCR fails locally, verify `tesseract --version` and `pytesseract.get_tesseract_version()`.
- If FAISS, PyTorch, or sentence-transformers installation fails, recreate the virtual environment with Python 3.11.
- If model-backed endpoints are slow on first request, wait for the initial Hugging Face model download.
