# Async Processing

Phase 3 moves long-running feedback analysis from synchronous HTTP requests into a queue-backed worker.

## Flow

```text
POST /ingestion/text
  -> creates feedback_records row with EXTRACTED

POST /processing/feedback-records/{id}/enqueue
  -> validates record
  -> marks QUEUED
  -> submits Celery task through Redis
  -> stores processing_task_id
  -> returns quickly

Celery worker
  -> receives feedback_id
  -> marks PROCESSING
  -> runs FeedbackAnalysisService
  -> persists sentiment/routing and COMPLETED
  -> or persists FAILED with error_code/error_message

GET /processing/feedback-records/{id}/status
  -> reads durable state from PostgreSQL
```

## Why Redis And Celery

Redis is the local broker. Celery is the worker framework. Together they teach production backend patterns: producer-consumer architecture, task IDs, retries, backoff, separate worker processes, and operational verification.

FastAPI `BackgroundTasks` is intentionally not used for this phase because it runs inside the API process. If the API restarts, in-process work can be lost. A broker-backed worker is a better model for reliable long-running workflows.

## State Machine

```text
PENDING -> QUEUED -> PROCESSING -> COMPLETED
EXTRACTED -> QUEUED -> PROCESSING -> COMPLETED
QUEUED -> FAILED
PROCESSING -> FAILED
```

`FAILED` is terminal in Phase 3. Reprocessing failed records should be added later as an explicit reset/retry feature.

## Idempotency

The enqueue endpoint is status-idempotent:

- `PENDING` and `EXTRACTED` enqueue normally.
- `QUEUED`, `PROCESSING`, and `COMPLETED` return the current state.
- `FAILED` returns a validation error.

This prevents duplicate active work for the same feedback record without adding a full jobs table.

## Retries And Failures

Transient processing failures are retried by Celery with bounded exponential backoff. Permanent failures are persisted immediately. Final retry exhaustion persists `FAILED` with `error_code` and `error_message`.

The database is the product source of truth. Celery result state is useful operational metadata, but clients poll FeedbackIQ's status endpoint.

## Commands

Start local infrastructure:

```powershell
docker compose up feedbackiq-db feedbackiq-redis -d
```

Apply migrations:

```powershell
python -m alembic upgrade head
```

Start the API:

```powershell
uvicorn app.main:app --reload
```

Start the worker:

```powershell
celery -A app.workers.celery_app worker --loglevel=info --pool=solo
```

Run normal tests:

```powershell
pytest
```

Run live verification:

```powershell
.\scripts\verify_phase3_live.ps1
```
