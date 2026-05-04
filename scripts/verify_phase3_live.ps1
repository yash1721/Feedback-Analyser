$ErrorActionPreference = "Stop"

Write-Host "Phase 3 live async processing verification"
Write-Host "This script requires Docker, Python dependencies, and free localhost ports 8000, 5432, and 6379."

$RepoRoot = Split-Path -Parent $PSScriptRoot
$VenvScripts = Join-Path $RepoRoot ".venv\Scripts"
$Python = Join-Path $VenvScripts "python.exe"
$Alembic = Join-Path $VenvScripts "alembic.exe"
$Celery = Join-Path $VenvScripts "celery.exe"
$Pytest = Join-Path $VenvScripts "pytest.exe"

if (-not (Test-Path $Python)) {
  $Python = "python"
}
if (-not (Test-Path $Alembic)) {
  $Alembic = "alembic"
}
if (-not (Test-Path $Celery)) {
  $Celery = "celery"
}
if (-not (Test-Path $Pytest)) {
  $Pytest = "pytest"
}

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

Write-Host "`n[0/10] Checking Docker availability..."
Invoke-Checked { docker info --format "{{.ServerVersion}}" } "Docker is not reachable. Start Docker Desktop, then rerun this script."

Write-Host "`n[1/10] Starting PostgreSQL and Redis..."
Invoke-Checked { docker compose up feedbackiq-db feedbackiq-redis -d } "Could not start PostgreSQL and Redis through Docker Compose."

Write-Host "`n[2/10] Docker Compose status..."
Invoke-Checked { docker compose ps } "Could not read Docker Compose service status."

Write-Host "`n[3/10] Running Alembic migrations..."
Invoke-Checked { & $Alembic upgrade head } "Alembic migrations failed."

Write-Host "`n[4/10] Starting API on http://127.0.0.1:8000 ..."
$api = Start-Process `
  -FilePath $Python `
  -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000" `
  -WindowStyle Hidden `
  -PassThru

Write-Host "`n[5/10] Starting Celery worker..."
$worker = Start-Process `
  -FilePath $Celery `
  -ArgumentList "-A", "app.workers.celery_app", "worker", "--loglevel=info", "--pool=solo" `
  -WindowStyle Hidden `
  -PassThru

try {
  Start-Sleep -Seconds 8

  Write-Host "`n[6/10] Health check..."
  Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/health" -Method Get | ConvertTo-Json -Depth 20

  Write-Host "`n[7/10] Creating text ingestion record..."
  $created = Invoke-RestMethod `
    -Uri "http://127.0.0.1:8000/api/v1/ingestion/text" `
    -Method Post `
    -ContentType "application/json" `
    -Body '{"text":"Checkout payment failed during Phase 3 live verification."}'
  $created | ConvertTo-Json -Depth 20
  $feedbackId = $created.data.feedback_id

  Write-Host "`n[8/10] Enqueueing background processing..."
  $enqueued = Invoke-RestMethod `
    -Uri "http://127.0.0.1:8000/api/v1/processing/feedback-records/$feedbackId/enqueue" `
    -Method Post
  $enqueued | ConvertTo-Json -Depth 20

  Write-Host "`n[9/10] Polling processing status..."
  $finalStatus = $null
  for ($i = 0; $i -lt 24; $i++) {
    $status = Invoke-RestMethod `
      -Uri "http://127.0.0.1:8000/api/v1/processing/feedback-records/$feedbackId/status" `
      -Method Get
    $status | ConvertTo-Json -Depth 20
    $finalStatus = $status.data.processing_status
    if ($finalStatus -eq "COMPLETED" -or $finalStatus -eq "FAILED") {
      break
    }
    Start-Sleep -Seconds 5
  }

  if ($finalStatus -ne "COMPLETED" -and $finalStatus -ne "FAILED") {
    throw "Processing did not reach a terminal status. Last status: $finalStatus"
  }

  Write-Host "`n[10/10] Running normal test suite..."
  Invoke-Checked { & $Pytest } "Normal pytest suite failed."
}
finally {
  if ($api -and -not $api.HasExited) {
    Stop-Process -Id $api.Id -Force
  }
  if ($worker -and -not $worker.HasExited) {
    Stop-Process -Id $worker.Id -Force
  }
}

Write-Host "`nPhase 3 checklist:"
Write-Host "- PostgreSQL started"
Write-Host "- Redis started"
Write-Host "- Alembic migrations applied"
Write-Host "- FastAPI started"
Write-Host "- Celery worker started"
Write-Host "- Text ingestion created a feedback record"
Write-Host "- Processing enqueue returned a task"
Write-Host "- Status polling reached a terminal state"
Write-Host "- Normal pytest completed"
