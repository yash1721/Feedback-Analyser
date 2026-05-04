# API

Base URL:

```text
http://localhost:8000/api/v1
```

All application responses use this envelope:

```json
{
  "success": true,
  "message": "success",
  "data": {},
  "error": null
}
```

Error responses use the same shape:

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

## Health

```http
GET /health
```

```powershell
curl.exe http://localhost:8000/api/v1/health
```

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

## OCR Upload

```http
POST /ocr/extract
Content-Type: multipart/form-data
```

Form field: `file`

```powershell
curl.exe -X POST http://localhost:8000/api/v1/ocr/extract -F "file=@Images/letter-1.png;type=image/png"
```

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

Unsupported media type:

```json
{
  "success": false,
  "message": "Uploaded file must be an image.",
  "data": null,
  "error": {
    "code": "unsupported_media_type",
    "details": {
      "content_type": "text/plain"
    }
  }
}
```

OCR setup error:

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

## OCR From URL

```http
POST /ocr/extract-from-url
Content-Type: application/json

{"url": "https://example.com/image.png"}
```

```powershell
Invoke-RestMethod -Uri http://localhost:8000/api/v1/ocr/extract-from-url -Method Post -ContentType "application/json" -Body '{"url":"https://example.com/image.png"}'
```

```json
{
  "success": true,
  "message": "success",
  "data": {
    "text": "extracted text",
    "url": "https://example.com/image.png"
  },
  "error": null
}
```

Unsafe URL error:

```json
{
  "success": false,
  "message": "URL must resolve to a public IP address.",
  "data": null,
  "error": {
    "code": "unsafe_url",
    "details": null
  }
}
```

## Retrieval Search

```http
POST /retrieval/search
Content-Type: application/json

{"query": "Shipping was delayed", "top_k": 3}
```

```powershell
Invoke-RestMethod -Uri http://localhost:8000/api/v1/retrieval/search -Method Post -ContentType "application/json" -Body '{"query":"checkout payment failed","top_k":2}'
```

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

Model setup error:

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

## Feedback Analysis

```http
POST /feedback/analyze
Content-Type: application/json

{"text": "Checkout failed during payment.", "top_k": 3, "persist": false}
```

```powershell
Invoke-RestMethod -Uri http://localhost:8000/api/v1/feedback/analyze -Method Post -ContentType "application/json" -Body '{"text":"Checkout payment failed during transaction.","top_k":2}'
```

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

Set `persist` to `true` to create a feedback record and include `record_id` in the response:

```powershell
Invoke-RestMethod -Uri http://localhost:8000/api/v1/feedback/analyze -Method Post -ContentType "application/json" -Body '{"text":"Checkout payment failed during transaction.","top_k":2,"persist":true}'
```

## Feedback Records

Create a text feedback record:

```http
POST /feedback-records
Content-Type: application/json

{"text": "Checkout payment failed during transaction."}
```

```json
{
  "success": true,
  "message": "success",
  "data": {
    "id": 1,
    "source_type": "TEXT",
    "original_input_reference": null,
    "raw_text": "Checkout payment failed during transaction.",
    "extracted_text": "Checkout payment failed during transaction.",
    "normalized_text": "Checkout payment failed during transaction.",
    "sentiment_label": null,
    "sentiment_score": null,
    "routed_team": null,
    "matched_keyword": null,
    "processing_status": "PENDING",
    "error_code": null,
    "error_message": null,
    "created_at": "2026-05-04T00:00:00",
    "updated_at": "2026-05-04T00:00:00"
  },
  "error": null
}
```

List feedback records:

```http
GET /feedback-records?limit=20&offset=0&processing_status=PENDING
```

Supported filters:

- `source_type`
- `processing_status`
- `routed_team`
- `sentiment_label`

```json
{
  "success": true,
  "message": "success",
  "data": {
    "items": [],
    "total": 0,
    "limit": 20,
    "offset": 0
  },
  "error": null
}
```

Get a feedback record:

```http
GET /feedback-records/{feedback_id}
```

Update processing status:

```http
PATCH /feedback-records/{feedback_id}/status
Content-Type: application/json

{"processing_status": "FAILED", "error_code": "manual_review", "error_message": "Needs review."}
```

Missing record:

```json
{
  "success": false,
  "message": "Feedback record was not found.",
  "data": null,
  "error": {
    "code": "not_found",
    "details": {
      "feedback_id": 999
    }
  }
}
```

Validation error:

```json
{
  "success": false,
  "message": "Invalid request payload.",
  "data": null,
  "error": {
    "code": "validation_error",
    "details": [
      {
        "type": "missing",
        "loc": ["body", "text"],
        "msg": "Field required"
      }
    ]
  }
}
```

## Ingestion

Text ingestion creates a feedback record without running sentiment, routing, retrieval, or RAG:

```http
POST /ingestion/text
Content-Type: application/json

{"text": "Checkout failed during payment."}
```

```json
{
  "success": true,
  "message": "success",
  "data": {
    "feedback_id": 1,
    "source_type": "TEXT",
    "processing_status": "EXTRACTED",
    "original_input_reference": null,
    "raw_text": "Checkout failed during payment.",
    "extracted_text": "Checkout failed during payment.",
    "normalized_text": "Checkout failed during payment.",
    "error_code": null,
    "error_message": null
  },
  "error": null
}
```

Image upload:

```http
POST /ingestion/image
Content-Type: multipart/form-data
```

Form field: `file`. The service accepts `image/*`, enforces `MAX_IMAGE_BYTES`, stores the original file, runs OCR, and persists an `IMAGE` feedback record.

Image URL ingestion:

```http
POST /ingestion/image-url
Content-Type: application/json

{"url": "https://example.com/image.png"}
```

Only `http` and `https` URLs are accepted. Localhost, private, loopback, link-local, reserved, and oversized image responses are rejected.

PDF ingestion:

```http
POST /ingestion/pdf
Content-Type: multipart/form-data
```

Form field: `file`. The service accepts `application/pdf`, enforces `MAX_PDF_BYTES`, stores the original file, extracts selectable text with `pypdf`, and persists a `PDF` feedback record.

CSV ingestion:

```http
POST /ingestion/csv
Content-Type: multipart/form-data
```

Expected CSV columns: `text` or `feedback_text`.

```json
{
  "success": true,
  "message": "success",
  "data": {
    "source_type": "CSV",
    "original_input_reference": "stored-file-key.csv",
    "created_count": 2,
    "failed_count": 1,
    "feedback_ids": [10, 11],
    "row_errors": [
      {
        "row_number": 3,
        "error_code": "invalid_row",
        "error_message": "Feedback text is required."
      }
    ]
  },
  "error": null
}
```

Extraction failure example:

```json
{
  "success": true,
  "message": "success",
  "data": {
    "feedback_id": 5,
    "source_type": "IMAGE",
    "processing_status": "FAILED",
    "original_input_reference": "stored-file-key.png",
    "raw_text": null,
    "extracted_text": null,
    "normalized_text": null,
    "error_code": "ocr_error",
    "error_message": "OCR processing timed out or failed."
  },
  "error": null
}
```

Phase 2 verification checklist:

- `POST /ingestion/text` creates an `EXTRACTED` `TEXT` record.
- `POST /ingestion/image` validates file type and size, stores the image, and persists OCR output or `FAILED`.
- `POST /ingestion/image-url` blocks unsafe URLs and persists downloaded image OCR output.
- `POST /ingestion/pdf` validates PDF upload and persists extracted text or `FAILED`.
- `POST /ingestion/csv` creates records for valid rows and returns row-level errors.
- `pytest` passes without Postgres, Tesseract, external network, paid APIs, or model downloads.

## Async Processing

Enqueue a feedback record:

```http
POST /processing/feedback-records/{feedback_id}/enqueue
```

The record must be `PENDING` or `EXTRACTED`. Records already in `QUEUED`, `PROCESSING`, or `COMPLETED` return idempotently without creating another active task. `FAILED` records require an explicit reset in a future phase.

```json
{
  "success": true,
  "message": "success",
  "data": {
    "feedback_id": 1,
    "processing_status": "QUEUED",
    "task_id": "celery-task-id",
    "enqueued": true
  },
  "error": null
}
```

Poll processing status:

```http
GET /processing/feedback-records/{feedback_id}/status
```

```json
{
  "success": true,
  "message": "success",
  "data": {
    "feedback_id": 1,
    "processing_status": "COMPLETED",
    "task_id": "celery-task-id",
    "error_code": null,
    "error_message": null,
    "sentiment_label": "NEGATIVE",
    "sentiment_score": 0.99,
    "routed_team": "Payment Team",
    "matched_keyword": "payment"
  },
  "error": null
}
```

Status lifecycle:

```text
PENDING -> QUEUED -> PROCESSING -> COMPLETED
EXTRACTED -> QUEUED -> PROCESSING -> COMPLETED
QUEUED/PROCESSING -> FAILED
```

## Knowledge

Create a knowledge document:

```http
POST /knowledge/documents
Content-Type: application/json

{
  "title": "Payment runbook",
  "text": "Payment failures should be routed to the Payment Team.",
  "source_type": "manual",
  "source_name": "runbook",
  "metadata": {
    "team": "Payment Team",
    "product_area": "checkout",
    "language": "en",
    "tags": ["payment", "checkout"]
  }
}
```

Index a document:

```http
POST /knowledge/documents/{document_id}/index
```

Search with metadata filters and persisted evidence:

```http
POST /retrieval/search
Content-Type: application/json

{
  "query": "checkout payment failed",
  "top_k": 3,
  "filters": {"team": "Payment Team"},
  "persist_trace": true
}
```

The response preserves `query`, `results`, and `rag_context`, and now also includes `trace_id`, ranks, point IDs, chunk IDs, and metadata when available.

## Analysis

Run RAG-grounded structured analysis for a feedback record:

```http
POST /analysis/feedback-records/{feedback_id}/run
```

Get latest analysis fields for a feedback record:

```http
GET /analysis/feedback-records/{feedback_id}/latest
```

Get an analysis run audit record:

```http
GET /analysis/runs/{run_id}
```

Structured output includes sentiment, category, severity, routed team, summary, recommended action, confidence, concise reasoning summary, and evidence chunk IDs.

## Workflow Automation

Create an internal workflow ticket from the latest analysis:

```http
POST /workflows/feedback-records/{feedback_id}/create-ticket
```

The endpoint is idempotent for the same feedback record. If a ticket already exists, the existing ticket is returned without creating another one.

List or inspect tickets:

```http
GET /tickets
GET /tickets/{ticket_id}
```

Update ticket status, assignment, or escalation:

```http
PATCH /tickets/{ticket_id}/status
Content-Type: application/json

{"status": "RESOLVED", "reason": "Payment fix deployed."}
```

```http
POST /tickets/{ticket_id}/assign
Content-Type: application/json

{"assigned_team": "Payment Team", "assigned_owner": "engineer@example.com"}
```

```http
POST /tickets/{ticket_id}/escalate
Content-Type: application/json

{"reason": "P1 payment failure."}
```

List and decide human-review items:

```http
GET /reviews?status=PENDING
GET /reviews/{review_id}
POST /reviews/{review_id}/decision
Content-Type: application/json

{"action": "OVERRIDE_TEAM", "final_team": "Backend Team", "reviewer_note": "Checkout API owner."}
```

Supported review actions are `APPROVE`, `REJECT`, `OVERRIDE_TEAM`, `OVERRIDE_SEVERITY`, `MARK_DUPLICATE`, and `RESOLVE`.

Inspect workflow audit events:

```http
GET /workflows/audit-logs?entity_type=ticket&entity_id=1
```
