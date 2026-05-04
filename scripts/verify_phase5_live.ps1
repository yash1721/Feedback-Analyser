$ErrorActionPreference = "Stop"

Write-Host "Phase 5 live LLM/RAG analysis verification"
Write-Host "This script uses the local rule_based LLM provider. No paid API key is required."

$RepoRoot = Split-Path -Parent $PSScriptRoot
$VenvScripts = Join-Path $RepoRoot ".venv\Scripts"
$Python = Join-Path $VenvScripts "python.exe"
$Alembic = Join-Path $VenvScripts "alembic.exe"
$Celery = Join-Path $VenvScripts "celery.exe"
$Pytest = Join-Path $VenvScripts "pytest.exe"

if (-not (Test-Path $Python)) { $Python = "python" }
if (-not (Test-Path $Alembic)) { $Alembic = "alembic" }
if (-not (Test-Path $Celery)) { $Celery = "celery" }
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

Write-Host "`n[0/12] Checking Docker availability..."
Invoke-Checked { docker info --format "{{.ServerVersion}}" } "Docker is not reachable. Start Docker Desktop, then rerun this script."

Write-Host "`n[1/12] Starting PostgreSQL, Redis, and Qdrant..."
Invoke-Checked { docker compose up feedbackiq-db feedbackiq-redis feedbackiq-qdrant -d } "Could not start Docker services."

Write-Host "`n[2/12] Running Alembic migrations..."
Invoke-Checked { & $Alembic upgrade head } "Alembic migrations failed."

Write-Host "`n[3/12] Starting API..."
$api = Start-Process -FilePath $Python -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000" -WindowStyle Hidden -PassThru

Write-Host "`n[4/12] Starting Celery worker..."
$worker = Start-Process -FilePath $Celery -ArgumentList "-A", "app.workers.celery_app", "worker", "--loglevel=info", "--pool=solo" -WindowStyle Hidden -PassThru

try {
  Start-Sleep -Seconds 8

  Write-Host "`n[5/12] Health check..."
  Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/health" -Method Get | ConvertTo-Json -Depth 20

  Write-Host "`n[6/12] Creating and indexing knowledge document..."
  $document = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/knowledge/documents" -Method Post -ContentType "application/json" -Body '{"title":"Payment analysis runbook","text":"Checkout payment failures and transaction errors should be routed to the Payment Team for log review and customer follow-up.","source_type":"manual","source_name":"phase5-live","metadata":{"team":"Payment Team","product_area":"checkout","language":"en","tags":["payment","checkout"]}}'
  $documentId = $document.data.id
  Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/knowledge/documents/$documentId/index" -Method Post | ConvertTo-Json -Depth 20

  Write-Host "`n[7/12] Ingesting feedback..."
  $feedback = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/ingestion/text" -Method Post -ContentType "application/json" -Body '{"text":"Customer had payment failure during checkout and could not complete the transaction."}'
  $feedbackId = $feedback.data.feedback_id
  $feedback | ConvertTo-Json -Depth 20

  Write-Host "`n[8/12] Running analysis API..."
  $analysis = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/analysis/feedback-records/$feedbackId/run" -Method Post
  $analysis | ConvertTo-Json -Depth 20
  if ($null -eq $analysis.data.analysis_run_id) { throw "Analysis run was not created." }
  if ($null -eq $analysis.data.retrieval_trace_id) { throw "Retrieval trace was not created." }
  if ($analysis.data.validation_status -ne "VALID") { throw "Analysis output was not valid." }

  Write-Host "`n[9/12] Verifying latest analysis..."
  $latest = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/analysis/feedback-records/$feedbackId/latest" -Method Get
  $latest | ConvertTo-Json -Depth 20
  if ($latest.data.category -ne "PAYMENT") { throw "Latest analysis category was not PAYMENT." }

  Write-Host "`n[10/12] Verifying async processing uses analysis..."
  $queuedFeedback = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/ingestion/text" -Method Post -ContentType "application/json" -Body '{"text":"Another checkout payment failed and blocked the purchase."}'
  $queuedFeedbackId = $queuedFeedback.data.feedback_id
  Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/processing/feedback-records/$queuedFeedbackId/enqueue" -Method Post | ConvertTo-Json -Depth 20

  $finalStatus = $null
  for ($i = 0; $i -lt 24; $i++) {
    $status = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/processing/feedback-records/$queuedFeedbackId/status" -Method Get
    $status | ConvertTo-Json -Depth 20
    $finalStatus = $status.data.processing_status
    if ($finalStatus -eq "COMPLETED" -or $finalStatus -eq "FAILED") { break }
    Start-Sleep -Seconds 5
  }
  if ($finalStatus -ne "COMPLETED") { throw "Async analysis did not complete. Last status: $finalStatus" }

  Write-Host "`n[11/12] Running normal test suite..."
  Invoke-Checked { & $Pytest } "Normal pytest suite failed."
}
finally {
  if ($api -and -not $api.HasExited) { Stop-Process -Id $api.Id -Force }
  if ($worker -and -not $worker.HasExited) { Stop-Process -Id $worker.Id -Force }
}

Write-Host "`n[12/12] Phase 5 checklist:"
Write-Host "- PostgreSQL, Redis, and Qdrant started"
Write-Host "- Migrations applied"
Write-Host "- Knowledge indexed"
Write-Host "- Feedback ingested"
Write-Host "- Analysis API created retrieval trace and analysis run"
Write-Host "- Latest feedback analysis fields updated"
Write-Host "- Celery async processing completed with Phase 5 analysis"
Write-Host "- Normal pytest completed"
