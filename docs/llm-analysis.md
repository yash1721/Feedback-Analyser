# LLM Analysis

Phase 5 adds RAG-grounded structured analysis for persisted feedback records.

## Flow

```text
feedback_record
  -> normalized/extracted/raw text
  -> Qdrant retrieval with retrieval trace persistence
  -> grounded feedback analysis prompt
  -> configured LLMProvider
  -> JSON parsing and Pydantic validation
  -> confidence policy
  -> llm_analysis_runs audit row
  -> latest analysis fields on feedback_records
```

## Providers

`LLMProvider` is an adapter interface. Phase 5 includes:

- `rule_based`: default local provider with deterministic behavior.
- `fake`: deterministic provider for tests.

Paid external providers are intentionally not required in Phase 5.

## Output Contract

The provider output is validated as strict structured data: sentiment, score, category, severity, routed team, summary, recommended action, confidence, concise reasoning summary, and evidence chunk IDs.

Invalid output is persisted as an invalid analysis run and is not used to update latest feedback fields.

## Evidence

Every analysis run can link to a retrieval trace. The trace records which chunks were retrieved, their scores/ranks, and metadata. This makes analysis auditable without storing private chain-of-thought.

## APIs

```http
POST /api/v1/analysis/feedback-records/{feedback_id}/run
GET  /api/v1/analysis/feedback-records/{feedback_id}/latest
GET  /api/v1/analysis/runs/{run_id}
```

## Verification

Normal tests remain Docker-free:

```powershell
pytest
```

Live verification:

```powershell
.\scripts\verify_phase5_live.ps1
```
