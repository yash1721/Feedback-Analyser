$ErrorActionPreference = "Stop"

Write-Host "Phase 6 live workflow automation verification"
Write-Host "This script uses local rule_based analysis and log notifications. No external ticketing credentials are required."

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
$env:WORKFLOW_AUTO_CREATE_TICKETS = "false"

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

try {
  Start-Sleep -Seconds 8

  Write-Host "`n[4/12] Health check..."
  Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/health" -Method Get | ConvertTo-Json -Depth 20

  Write-Host "`n[5/12] Creating and indexing knowledge document..."
  $document = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/knowledge/documents" -Method Post -ContentType "application/json" -Body '{"title":"Payment workflow runbook","text":"Urgent checkout payment failures should be routed to the Payment Team and escalated for fast resolution.","source_type":"manual","source_name":"phase6-live","metadata":{"team":"Payment Team","product_area":"checkout","language":"en","tags":["payment","workflow"]}}'
  $documentId = $document.data.id
  Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/knowledge/documents/$documentId/index" -Method Post | ConvertTo-Json -Depth 20

  Write-Host "`n[6/12] Ingesting feedback..."
  $feedback = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/ingestion/text" -Method Post -ContentType "application/json" -Body '{"text":"Urgent payment failed during checkout and blocked the purchase."}'
  $feedbackId = $feedback.data.feedback_id
  $feedback | ConvertTo-Json -Depth 20

  Write-Host "`n[7/12] Running analysis API..."
  $analysis = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/analysis/feedback-records/$feedbackId/run" -Method Post
  $analysis | ConvertTo-Json -Depth 20
  if ($analysis.data.validation_status -ne "VALID") { throw "Analysis output was not valid." }
  if ($null -eq $analysis.data.retrieval_trace_id) { throw "Retrieval trace was not created." }

  Write-Host "`n[8/12] Creating workflow ticket..."
  $workflow = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/workflows/feedback-records/$feedbackId/create-ticket" -Method Post
  $workflow | ConvertTo-Json -Depth 20
  $ticketId = $workflow.data.ticket.id
  if ($null -eq $ticketId) { throw "Workflow ticket was not created." }
  if ($workflow.data.ticket.status -ne "ESCALATED") { throw "Expected escalated ticket for urgent payment failure." }
  if ($workflow.data.review_created -ne $true) { throw "Expected human review for high severity feedback." }

  Write-Host "`n[9/12] Verifying tickets, reviews, and audit logs..."
  $tickets = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/tickets" -Method Get
  $reviews = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/reviews?status=PENDING" -Method Get
  $audit = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/workflows/audit-logs?entity_type=ticket&entity_id=$ticketId" -Method Get
  $tickets | ConvertTo-Json -Depth 20
  $reviews | ConvertTo-Json -Depth 20
  $audit | ConvertTo-Json -Depth 20
  if ($tickets.data.total -lt 1) { throw "Ticket list did not include created ticket." }
  if ($reviews.data.total -lt 1) { throw "Review list did not include pending review." }
  if ($audit.data.total -lt 1) { throw "Audit logs were not persisted." }

  Write-Host "`n[10/12] Verifying idempotent workflow creation..."
  $secondWorkflow = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/workflows/feedback-records/$feedbackId/create-ticket" -Method Post
  if ($secondWorkflow.data.ticket.id -ne $ticketId) { throw "Idempotent create returned a different ticket." }

  Write-Host "`n[11/12] Running normal test suite..."
  Invoke-Checked { & $Pytest } "Normal pytest suite failed."
}
finally {
  if ($api -and -not $api.HasExited) { Stop-Process -Id $api.Id -Force }
}

Write-Host "`n[12/12] Phase 6 checklist:"
Write-Host "- PostgreSQL, Redis, and Qdrant started"
Write-Host "- Migrations applied"
Write-Host "- Knowledge indexed"
Write-Host "- Feedback ingested and analyzed"
Write-Host "- Workflow ticket created"
Write-Host "- High severity payment issue escalated"
Write-Host "- Human review item created"
Write-Host "- Audit logs persisted"
Write-Host "- Idempotent ticket creation verified"
Write-Host "- Normal pytest completed"
