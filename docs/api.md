# API

Base URL: `http://localhost:8000/api/v1`

## Health

```http
GET /health
```

## OCR Upload

```http
POST /ocr/extract
Content-Type: multipart/form-data
```

Field: `file`

## OCR From URL

```http
POST /ocr/extract-from-url
Content-Type: application/json

{"url": "https://example.com/image.png"}
```

## Feedback Analysis

```http
POST /feedback/analyze
Content-Type: application/json

{"text": "Checkout failed during payment.", "top_k": 3}
```

## Retrieval Search

```http
POST /retrieval/search
Content-Type: application/json

{"query": "Shipping was delayed", "top_k": 3}
```

