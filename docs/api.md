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
