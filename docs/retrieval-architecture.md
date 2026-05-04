# Retrieval Architecture

Phase 4 upgrades FeedbackIQ from prototype in-memory retrieval to production-style vector retrieval.

## Flow

```text
Knowledge document
  -> PostgreSQL document row
  -> text chunks
  -> PostgreSQL chunk rows
  -> BGE-M3 dense embeddings
  -> Qdrant vector points with metadata payload
  -> metadata-aware retrieval
  -> RAG context
  -> optional PostgreSQL retrieval trace
```

PostgreSQL stores business truth and evidence. Qdrant stores the vector index used for fast approximate nearest-neighbor search.

## Why Qdrant

Qdrant is used because it runs cleanly in Docker, exposes an API service, supports HNSW vector indexes, cosine similarity, and payload metadata filters. FAISS remains available as a local provider, but Qdrant is the production-oriented path.

## Why BGE-M3

BGE-M3 is the default embedding provider because it is a strong open-source multilingual retrieval model. It is a better fit than MiniLM for English/Hindi feedback and enterprise knowledge. The model is loaded lazily on first use.

## Metadata Filtering

Chunks are indexed with payload fields such as:

- `document_id`
- `chunk_id`
- `source_type`
- `source_name`
- custom metadata such as `team`, `product_area`, `language`, or `tags`

Filters reduce irrelevant context before RAG context is built.

## Evidence

Retrieval traces record the query, provider, embedding model, collection, filters, scores, ranks, and text previews. This makes retrieval explainable and prepares the system for future RAG evaluation without storing large prompts on `feedback_records`.

## Local Commands

```powershell
docker compose up feedbackiq-db feedbackiq-redis feedbackiq-qdrant -d
python -m alembic upgrade head
uvicorn app.main:app --reload
```

First BGE-M3 use may download a large model:

```env
EMBEDDING_PROVIDER=bge_m3
EMBEDDING_MODEL_NAME=BAAI/bge-m3
VECTOR_PROVIDER=qdrant
```

Run live verification:

```powershell
.\scripts\verify_phase4_live.ps1
```
