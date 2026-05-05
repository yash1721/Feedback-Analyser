$ErrorActionPreference = "Stop"

Write-Host "Phase 8 live observability verification"
Write-Host "This script verifies health, readiness, metrics, correlation headers, and core Phase 1-7 flows."

$RepoRoot = Split-Path -Parent $PSScriptRoot
$VenvScripts = Join-Path $RepoRoot ".venv\Scripts"
$Python = Join-Path $VenvScripts "python.exe"
$Alembic = Join-Path $VenvScripts "alembic.exe"
$Pytest = Join-Path $VenvScripts "pytest.exe"

if (-not (Test-Path $Python)) { $Python = "python" }
if (-not (Test-Path $Alembic)) { $Alembic = "alembic" }
if (-not (Test-Path $Pytest)) { $Pytest = "pytest" }

$env:VECTOR_PROVIDER = "qdrant"
$env:EMBEDDING_PROVIDER = "bge_m3"
$env:EMBEDDING_MODEL_NAME = "BAAI/bge-m3"
$env:QDRANT_URL = "http://localhost:6333"
$env:QDRANT_COLLECTION_NAME = "feedbackiq_knowledge"
$env:VECTOR_SIZE = "1024"
$env:VECTOR_DISTANCE = "cosine"
$env:LLM_PROVIDER = "rule_based"
$env:LLM_FALLBACK_PROVIDER = "rule_based"
$env:LLM_MODEL_NAME = "rule-based-feedback-analyzer-v1"
$env:NOTIFICATION_PROVIDER = "log"
$env:LOG_FORMAT = "json"
$env:LOG_LEVEL = "INFO"

function Invoke-Checked {
  param(
    [Parameter(Mandatory = $true)]
    [scriptblock]$Command,
    [Parameter(Mandatory = $true)]
    [string]$Message
  )
  & $Command
  if ($LASTEXITCODE -ne 0) {
    throw $Message
  }
}

function Assert-Contains {
  param(
    [Parameter(Mandatory = $true)]
    [string]$Text,
    [Parameter(Mandatory = $true)]
    [string]$Needle
  )
  if (-not $Text.Contains($Needle)) {
    throw "Expected output to contain '$Needle'."
  }
}

Write-Host "`n[0/12] Checking Docker availability..."
Invoke-Checked { docker info --format "{{.ServerVersion}}" } "Docker is not reachable. Start Docker Desktop, then rerun this script."

Write-Host "`n[1/12] Starting PostgreSQL, Redis, and Qdrant..."
Invoke-Checked { docker compose up feedbackiq-db feedbackiq-redis feedbackiq-qdrant -d } "Could not start Docker services."

Write-Host "`n[2/12] Running Alembic migrations..."
Invoke-Checked { & $Alembic upgrade head } "Alembic migrations failed."

Write-Host "`n[3/12] Starting API..."
$api = Start-Process -FilePath $Python -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000" -WindowStyle Hidden -PassThru

try {
  Start-Sleep -Seconds 8

  Write-Host "`n[4/12] Health, liveness, and readiness..."
  $health = Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/v1/health" -Method Get -Headers @{ "X-Correlation-ID" = "phase8-live" } -UseBasicParsing
  if ($health.Headers["X-Correlation-ID"] -ne "phase8-live") { throw "Correlation header was not preserved." }
  $health.Content | ConvertFrom-Json | ConvertTo-Json -Depth 20
  Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/health/live" -Method Get | ConvertTo-Json -Depth 20
  $ready = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/health/ready" -Method Get
  $ready | ConvertTo-Json -Depth 20
  if ($ready.data.status -ne "ready") { throw "Readiness check did not report ready." }

  Write-Host "`n[5/12] Creating and indexing knowledge document..."
  $document = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/knowledge/documents" -Method Post -ContentType "application/json" -Body '{"title":"Phase 8 Payment Observability Runbook","text":"Payment failures during checkout should route to the Payment Team and include operational metrics for analysis.","source_type":"manual","source_name":"phase8-live","metadata":{"team":"Payment Team","tags":["payment","observability"]}}'
  $documentId = $document.data.id
  Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/knowledge/documents/$documentId/index" -Method Post | Out-Null

  Write-Host "`n[6/12] Ingesting feedback..."
  $feedback = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/ingestion/text" -Method Post -ContentType "application/json" -Body '{"text":"Payment failed during checkout and I need help."}'
  $feedbackId = $feedback.data.feedback_id
  $feedback | ConvertTo-Json -Depth 20

  Write-Host "`n[7/12] Running retrieval..."
  $retrieval = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/retrieval/search" -Method Post -ContentType "application/json" -Body '{"query":"payment checkout failure","top_k":3,"persist_trace":true}'
  $retrieval | ConvertTo-Json -Depth 20
  if ($retrieval.data.results.Count -lt 1) { throw "Expected retrieval results." }

  Write-Host "`n[8/12] Running analysis and workflow..."
  $analysis = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/analysis/feedback-records/$feedbackId/run" -Method Post
  $analysis | ConvertTo-Json -Depth 20
  if ($analysis.data.validation_status -ne "VALID") { throw "Analysis output was not valid." }
  $workflow = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/workflows/feedback-records/$feedbackId/create-ticket" -Method Post
  $workflow | ConvertTo-Json -Depth 20

  Write-Host "`n[9/12] Running evaluation..."
  $evaluation = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/evaluations/runs" -Method Post -ContentType "application/json" -Body '{"provider":"rule_based","top_k":3,"write_report":true}'
  $evaluation | ConvertTo-Json -Depth 20

  Write-Host "`n[10/12] Verifying Prometheus metrics..."
  $metrics = (Invoke-WebRequest -Uri "http://127.0.0.1:8000/metrics" -Method Get -UseBasicParsing).Content
  Assert-Contains $metrics "feedbackiq_http_requests_total"
  Assert-Contains $metrics "feedbackiq_retrieval_requests_total"
  Assert-Contains $metrics "feedbackiq_analysis_runs_total"
  Assert-Contains $metrics "feedbackiq_workflow_tickets_created_total"
  Assert-Contains $metrics "feedbackiq_evaluation_runs_total"

  Write-Host "`n[11/12] Running normal test suite..."
  Invoke-Checked { & $Pytest } "Normal pytest suite failed."
}
finally {
  if ($api -and -not $api.HasExited) { Stop-Process -Id $api.Id -Force }
}

Write-Host "`n[12/12] Phase 8 checklist:"
Write-Host "- Docker services started"
Write-Host "- Migrations applied"
Write-Host "- API started"
Write-Host "- Health, liveness, readiness verified"
Write-Host "- Correlation header verified"
Write-Host "- Ingestion, retrieval, analysis, workflow, and evaluation exercised"
Write-Host "- Prometheus metrics verified"
Write-Host "- Normal pytest completed"
