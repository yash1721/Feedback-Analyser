# Evaluation and LLMOps

Phase 7 adds a benchmark layer for FeedbackIQ. The purpose is to prove that retrieval, LLM analysis, routing, severity classification, and workflow decisions are measurable instead of only manually inspected.

## Evaluation Flow

The evaluation pipeline is:

1. Load a golden dataset example.
2. Retrieve evidence from the configured retrieval provider.
3. Build the normal analysis prompt with retrieved evidence.
4. Run the configured LLM provider.
5. Validate structured output.
6. Compare predicted labels with expected labels.
7. Check whether retrieved evidence supports the answer.
8. Record latency, failures, per-item metrics, and aggregate metrics.
9. Persist the run and write JSON/Markdown reports.

This is an Evaluation Pipeline Pattern. Each stage is observable, and one failed example is stored as a failed item instead of failing the whole run.

## Dataset Format

The built-in seed dataset lives at `app/domain/evaluation/fixtures/feedback_eval_seed.json`.

Each example contains:

- `id`: stable benchmark example id.
- `feedback_text`: input text to evaluate.
- `expected_sentiment`: expected sentiment label.
- `expected_category`: expected analysis category.
- `expected_severity`: expected priority.
- `expected_routed_team`: expected owning team.
- `expected_keywords`: evidence words expected in retrieved context.
- `expected_relevant_chunk_ids`: optional exact relevant chunks.
- `expected_relevant_document_titles`: optional expected source documents.
- `expected_escalate`: optional workflow escalation expectation.
- `expected_needs_review`: optional human-review expectation.
- `notes`: human reason for the label.

A golden dataset is required because AI quality needs a stable target. Without expected labels, a run can tell you that the system produced output, but not whether the output was correct.

## Metrics

Retrieval metrics:

- `precision@k`: how many returned results were relevant.
- `recall@k`: how many expected relevant results were found.
- `hit@k`: whether at least one relevant result was found.
- `MRR`: how early the first relevant result appeared.
- `average_retrieval_score`: average vector similarity score.
- `no_result_rate`: how often retrieval returned nothing.

Analysis metrics:

- sentiment accuracy
- category accuracy
- severity accuracy
- routed team accuracy
- exact label match rate
- invalid output rate
- low-confidence rate
- provider failure rate

Workflow metrics:

- escalation accuracy when `expected_escalate` is present
- review accuracy when `expected_needs_review` is present

Latency metrics:

- total item latency
- p50, p95, p99, and average latency across the run

## Groundedness

Phase 7 uses a lightweight groundedness check:

- `PASS`: retrieved evidence supports the prediction through cited chunks, expected chunks, expected document titles, or expected keywords.
- `WARN`: retrieval returned evidence, but it did not match expected evidence signals.
- `FAIL`: no evidence exists or analysis failed.

This intentionally avoids external RAG evaluation dependencies. It is simple, deterministic, and Docker-free in normal tests.

## Experiment Tracking

Each `evaluation_runs` row stores:

- dataset name/version
- provider/model
- prompt version
- vector provider
- embedding model
- top_k
- aggregate metrics
- report path

This makes prompt/provider comparisons possible without a dashboard.

## Running Evaluation

Run through the API:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/evaluations/runs" -Method Post -ContentType "application/json" -Body '{"provider":"rule_based","top_k":3}'
```

Run through CLI:

```powershell
python .\scripts\run_evaluation.py --provider rule_based --top-k 3
```

Run a specific dataset:

```powershell
python .\scripts\run_evaluation.py --dataset .\app\domain\evaluation\fixtures\feedback_eval_seed.json --provider rule_based --top-k 3
```

The CLI defaults to deterministic fixture retrieval for local benchmarking. Add `--live-retrieval` when you want it to use the configured Qdrant/BGE-M3 retrieval stack.

Run full live verification:

```powershell
.\scripts\verify_phase7_live.ps1
```

Normal pytest remains Docker-free and uses fake retrieval/LLM providers.

## Interview Story

The SDE-2 backend/AI talking point is: FeedbackIQ treats AI output as a measurable production subsystem. It stores golden examples, runs retrieval and LLM analysis through the same service boundaries as production, computes quality and latency metrics, persists run history, and generates reports. This shows practical LLMOps without overbuilding dashboards, paid model dependencies, or distributed tracing too early.
