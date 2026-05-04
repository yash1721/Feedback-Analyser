$ErrorActionPreference = "Stop"

Write-Host "Phase 4 live retrieval verification"
Write-Host "This script starts PostgreSQL, Redis, Qdrant, FastAPI, indexes a document, searches it, persists evidence, and runs pytest."
Write-Host "First BGE-M3 use can download a large model and may take several minutes."

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

Write-Host "`n[0/9] Checking Docker availability..."
Invoke-Checked { docker info --format "{{.ServerVersion}}" } "Docker is not reachable. Start Docker Desktop, then rerun this script."

Write-Host "`n[1/9] Starting PostgreSQL, Redis, and Qdrant..."
Invoke-Checked { docker compose up feedbackiq-db feedbackiq-redis feedbackiq-qdrant -d } "Could not start Docker services."

Write-Host "`n[2/9] Docker Compose status..."
Invoke-Checked { docker compose ps } "Could not read Docker Compose status."

Write-Host "`n[3/9] Running Alembic migrations..."
Invoke-Checked { & $Alembic upgrade head } "Alembic migrations failed."

Write-Host "`n[4/9] Starting API on http://127.0.0.1:8000 ..."
$api = Start-Process `
  -FilePath $Python `
  -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000" `
  -WindowStyle Hidden `
  -PassThru

try {
  Start-Sleep -Seconds 8

  Write-Host "`n[5/9] Health check..."
  Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/health" -Method Get | ConvertTo-Json -Depth 20

  Write-Host "`n[6/9] Creating and indexing knowledge document..."
  $document = Invoke-RestMethod `
    -Uri "http://127.0.0.1:8000/api/v1/knowledge/documents" `
    -Method Post `
    -ContentType "application/json" `
    -Body '{"title":"Payment runbook","text":"Payment failures and checkout transaction issues should be routed to the Payment Team.","source_type":"manual","source_name":"phase4-live","metadata":{"team":"Payment Team","product_area":"checkout","language":"en","tags":["payment","checkout"]}}'
  $document | ConvertTo-Json -Depth 20
  $documentId = $document.data.id

  $indexed = Invoke-RestMethod `
    -Uri "http://127.0.0.1:8000/api/v1/knowledge/documents/$documentId/index" `
    -Method Post
  $indexed | ConvertTo-Json -Depth 20
  if ($indexed.data.indexed_chunks -lt 1) {
    throw "Document indexing did not create chunks."
  }

  Write-Host "`n[7/9] Running Qdrant-backed retrieval with persisted trace..."
  $retrieval = Invoke-RestMethod `
    -Uri "http://127.0.0.1:8000/api/v1/retrieval/search" `
    -Method Post `
    -ContentType "application/json" `
    -Body '{"query":"checkout payment failed","top_k":3,"filters":{"team":"Payment Team"},"persist_trace":true}'
  $retrieval | ConvertTo-Json -Depth 20
  if ($retrieval.data.results.Count -lt 1) {
    throw "Retrieval did not return any results."
  }
  if ($null -eq $retrieval.data.trace_id) {
    throw "Retrieval trace was not persisted."
  }

  Write-Host "`n[8/9] Running normal test suite..."
  Invoke-Checked { & $Pytest } "Normal pytest suite failed."
}
finally {
  if ($api -and -not $api.HasExited) {
    Stop-Process -Id $api.Id -Force
  }
}

Write-Host "`n[9/9] Phase 4 checklist:"
Write-Host "- PostgreSQL started"
Write-Host "- Redis started"
Write-Host "- Qdrant started"
Write-Host "- Alembic migrations applied"
Write-Host "- FastAPI started"
Write-Host "- Knowledge document created"
Write-Host "- Knowledge chunks indexed into Qdrant"
Write-Host "- Metadata-filtered retrieval returned results"
Write-Host "- Retrieval trace persisted"
Write-Host "- Normal pytest completed"
