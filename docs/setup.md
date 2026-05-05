# Setup

## Supported Python

Use Python 3.11 for local development. The current dependency set is not verified on Python 3.13.

On Windows, install Python 3.11 from:

```text
https://www.python.org/downloads/release/python-3119/
```

Verify that the launcher can find it:

```powershell
py -3.11 --version
```

## Local Environment

From the repository root:

```powershell
py -3.11 -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
copy .env.example .env
```

## Database

Phase 1 uses PostgreSQL for local app runtime and SQLite for automated tests.

Start Postgres and Redis with Docker Compose:

```powershell
docker compose up feedbackiq-db feedbackiq-redis feedbackiq-qdrant -d
```

The default local database URL is:

```env
DATABASE_URL=postgresql+psycopg://feedbackiq:feedbackiq@localhost:5432/feedbackiq
```

Apply migrations:

```powershell
alembic upgrade head
```

Create a new migration after changing SQLAlchemy models:

```powershell
alembic revision --autogenerate -m "describe change"
```

Start the API:

```powershell
uvicorn app.main:app --reload
```

Start the Celery worker in another terminal:

```powershell
celery -A app.workers.celery_app worker --loglevel=info --pool=solo
```

Redis and Celery settings are environment-driven:

```env
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1
PROCESSING_MAX_RETRIES=3
PROCESSING_RETRY_BACKOFF_SECONDS=5
CELERY_TASK_ALWAYS_EAGER=false
VECTOR_PROVIDER=qdrant
EMBEDDING_PROVIDER=bge_m3
EMBEDDING_MODEL_NAME=BAAI/bge-m3
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION_NAME=feedbackiq_knowledge
VECTOR_SIZE=1024
VECTOR_DISTANCE=cosine
LLM_PROVIDER=rule_based
LLM_FALLBACK_PROVIDER=rule_based
LLM_MODEL_NAME=rule-based-feedback-analyzer-v1
LLM_PROMPT_VERSION=feedback-analysis-v1
LLM_CONFIDENCE_THRESHOLD=0.5
WORKFLOW_LOW_CONFIDENCE_THRESHOLD=0.65
WORKFLOW_DEFAULT_SLA_HOURS=48
WORKFLOW_P0_SLA_HOURS=4
WORKFLOW_P1_SLA_HOURS=12
WORKFLOW_AUTO_CREATE_TICKETS=false
NOTIFICATION_PROVIDER=log
```

Open:

```text
http://localhost:8000/docs
```

## Tesseract OCR

Real OCR requires the native Tesseract binary in addition to the Python `pytesseract` package.

On Windows:

1. Install the UB Mannheim Tesseract build from `https://github.com/UB-Mannheim/tesseract/wiki`.
2. Select the language data needed by `OCR_LANGUAGES` in `.env`; the default is `eng+hin`.
3. Add the Tesseract install directory to `PATH`.
4. Open a new terminal after changing `PATH`.

Verify:

```powershell
tesseract --version
python -c "import pytesseract; print(pytesseract.get_tesseract_version())"
```

If `tesseract --version` fails, fix the native install or `PATH`. If the Python command fails, reinstall dependencies in the active virtual environment.

## PDF And CSV Ingestion

PDF text extraction uses the Python `pypdf` package from `requirements.txt`. It works best for PDFs that already contain selectable text. Scanned PDFs need OCR-based handling, which is intentionally not part of Phase 2.

File size limits are environment-driven:

```env
MAX_IMAGE_BYTES=5242880
MAX_PDF_BYTES=10485760
MAX_CSV_BYTES=2097152
```

CSV ingestion expects UTF-8 CSV with a `text` or `feedback_text` column:

```csv
text
Checkout failed during payment.
Shipping was delayed.
```

Blank rows are reported as row-level errors while valid rows are still persisted.

## Hugging Face Models

Retrieval and feedback analysis load models lazily on first use:

- `sentence-transformers/all-MiniLM-L6-v2`
- `distilbert-base-uncased-finetuned-sst-2-english`

The first request to `/api/v1/retrieval/search` or `/api/v1/feedback/analyze` may take longer because models are downloaded and cached. Offline environments must have the models pre-cached or use local model paths in `.env`:

```env
EMBEDDING_MODEL_NAME=sentence-transformers/all-MiniLM-L6-v2
SENTIMENT_MODEL_NAME=distilbert-base-uncased-finetuned-sst-2-english
```

## Tests

Run tests from the repository root:

```powershell
pytest
```

The repository includes `pytest.ini`, which restricts discovery to `tests/` and adds the repo root to the import path.

Tests build a temporary SQLite schema and override FastAPI dependencies where needed. They should not require Postgres, Tesseract, or Hugging Face model downloads.

Async processing tests use fake queues and fake analysis services, so normal `pytest` does not require Redis or a running Celery worker.

## Docker

Docker installs the native Tesseract package inside the container:

```powershell
copy .env.example .env
docker compose up --build
```

For a fresh Compose database, apply migrations:

```powershell
docker compose exec feedbackiq-api alembic upgrade head
```

## Phase 1.1.5 Live Runtime Verification

Use this gate before moving past Phase 1.1. It verifies the app against live PostgreSQL. It is intentionally separate from normal tests so `pytest` stays fast and Docker-free.

Prerequisites:

- Docker Desktop is installed and running.
- Python 3.11 virtual environment is active.
- Dependencies are installed with `pip install -r requirements-dev.txt`.
- `.env` exists.
- `DATABASE_URL` points from Windows to local Postgres:

```env
DATABASE_URL=postgresql+psycopg://feedbackiq:feedbackiq@localhost:5432/feedbackiq
```

Start PostgreSQL:

```powershell
docker compose up feedbackiq-db -d
docker compose ps
```

Expected: `feedbackiq-db` is running and reports healthy after the Compose healthcheck passes.

Run migrations:

```powershell
python -m alembic upgrade head
```

Verify the feedback table:

```powershell
docker compose exec feedbackiq-db psql -U feedbackiq -d feedbackiq -c "\dt"
```

Start the API:

```powershell
uvicorn app.main:app --reload
```

In another PowerShell window, create a record:

```powershell
$created = Invoke-RestMethod `
  -Uri http://localhost:8000/api/v1/feedback-records `
  -Method Post `
  -ContentType "application/json" `
  -Body '{"text":"Checkout payment failed during live verification."}'

$feedbackId = $created.data.id
```

Read the record:

```powershell
Invoke-RestMethod "http://localhost:8000/api/v1/feedback-records/$feedbackId"
```

List records with pagination:

```powershell
Invoke-RestMethod "http://localhost:8000/api/v1/feedback-records?limit=10&offset=0"
```

Update status:

```powershell
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

Optional helper script:

```powershell
.\scripts\verify_phase1_live.ps1
```

## Phase 3 Live Runtime Verification

Use this gate after async processing changes. It verifies PostgreSQL, Redis, FastAPI, Celery, migrations, ingestion, enqueue, polling, and tests:

```powershell
.\scripts\verify_phase3_live.ps1
```

On Windows, the worker command uses Celery's solo pool:

```powershell
celery -A app.workers.celery_app worker --loglevel=info --pool=solo
```

## Phase 4 Live Runtime Verification

Use this gate after retrieval changes. It verifies PostgreSQL, Qdrant, migrations, knowledge indexing, retrieval, evidence persistence, and tests:

```powershell
.\scripts\verify_phase4_live.ps1
```

BGE-M3 loads lazily on first indexing/search use. The first run may download the model.

## Phase 5 Live Runtime Verification

Use this gate after LLM analysis changes. It verifies retrieval evidence, structured analysis, latest feedback fields, async worker integration, and tests:

```powershell
.\scripts\verify_phase5_live.ps1
```

The default provider is `rule_based`, so no paid API key is required.

## Phase 6 Live Runtime Verification

Use this gate after workflow automation changes. It verifies analysis, ticket creation, escalation, human review, audit logs, idempotency, and tests:

```powershell
.\scripts\verify_phase6_live.ps1
```

The default notification provider is `log`, so no Slack, Jira, or Zendesk credentials are required.

## Common Setup Failures

`ModuleNotFoundError: No module named 'app'`

Run tests from the repository root with the included `pytest.ini`.

`ModuleNotFoundError: No module named 'sentence_transformers'`

Activate the virtual environment and run `pip install -r requirements-dev.txt`.

`pytesseract is not installed`

Activate the virtual environment and run `pip install -r requirements-dev.txt`.

`Tesseract binary is not installed or not available on PATH`

Install native Tesseract and verify `tesseract --version` in a new terminal.

`sqlalchemy.exc.OperationalError`

Verify PostgreSQL is running, `DATABASE_URL` points to the right host, and migrations have been applied.
# Phase 7 Evaluation Setup

Normal tests remain Docker-free:

```powershell
pytest
```

Run a local evaluation through the CLI:

```powershell
python .\scripts\run_evaluation.py --provider rule_based --top-k 3

Run a specific dataset from the repo root:

```powershell
python .\scripts\run_evaluation.py --dataset .\app\domain\evaluation\fixtures\feedback_eval_seed.json --provider rule_based --top-k 3
```

The CLI defaults to a deterministic fixture retriever so the command works from the repo root without downloading embedding models. Add `--live-retrieval` to benchmark the configured vector and embedding providers.
```

The default seed dataset is:

```text
app/domain/evaluation/fixtures/feedback_eval_seed.json
```

Reports are written to:

```text
eval_reports/
```

For full-stack verification with PostgreSQL, Redis, Qdrant, Alembic, API, CLI, and pytest:

```powershell
.\scripts\verify_phase7_live.ps1
```
