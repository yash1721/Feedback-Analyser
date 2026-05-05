$ErrorActionPreference = "Stop"

Write-Host "Phase 7 live evaluation verification"
Write-Host "This script uses local rule_based analysis. No paid external API is required."

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
$env:EVALUATION_REPORT_DIR = "eval_reports"

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

function Invoke-JsonApi {
  param(
    [Parameter(Mandatory = $true)]
    [string]$Uri,
    [Parameter(Mandatory = $true)]
    [string]$Method,
    [string]$Body = $null
  )
  try {
    if ($null -eq $Body) {
      return Invoke-RestMethod -Uri $Uri -Method $Method
    }
    return Invoke-RestMethod -Uri $Uri -Method $Method -ContentType "application/json" -Body $Body
  }
  catch {
    Write-Host "API request failed: $Method $Uri"
    if ($_.Exception.Response -and $_.Exception.Response.GetResponseStream()) {
      $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
      $responseBody = $reader.ReadToEnd()
      Write-Host "Response body:"
      Write-Host $responseBody
    }
    throw
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

  Write-Host "`n[5/12] Creating and indexing seed knowledge documents..."
  $documents = @(
    @{ title = "Payments Knowledge Base"; text = "Payment failures during checkout and refund delays should route to the Payment Team and may require escalation."; source_type = "manual"; source_name = "phase7-live" },
    @{ title = "Delivery Knowledge Base"; text = "Shipment delays, delivery tracking problems, and logistics issues should route to the Logistics Team."; source_type = "manual"; source_name = "phase7-live" },
    @{ title = "Frontend Experience Guide"; text = "Mobile screen, checkout button, design, and UI confusion should route to the Frontend Team."; source_type = "manual"; source_name = "phase7-live" },
    @{ title = "Security Incident Runbook"; text = "Fraud, security breach, and account risk reports should route to the Backend Team and escalate immediately."; source_type = "manual"; source_name = "phase7-live" }
  )
  foreach ($doc in $documents) {
    $body = $doc | ConvertTo-Json -Depth 20
    $created = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/knowledge/documents" -Method Post -ContentType "application/json" -Body $body
    $documentId = $created.data.id
    Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/knowledge/documents/$documentId/index" -Method Post | Out-Null
  }

  Write-Host "`n[6/12] Running evaluation through API..."
  $evaluation = Invoke-JsonApi -Uri "http://127.0.0.1:8000/api/v1/evaluations/runs" -Method Post -Body '{"provider":"rule_based","top_k":3,"write_report":true}'
  $evaluation | ConvertTo-Json -Depth 20
  $runId = $evaluation.data.run.id
  if ($null -eq $runId) { throw "Evaluation run was not created." }

  Write-Host "`n[7/12] Verifying evaluation run and items..."
  $run = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/evaluations/runs/$runId" -Method Get
  $run | ConvertTo-Json -Depth 20
  if ($run.data.items.Count -lt 1) { throw "Evaluation run items were not persisted." }

  Write-Host "`n[8/12] Verifying report endpoint..."
  $report = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/evaluations/runs/$runId/report" -Method Get
  if (-not ($report -match "FeedbackIQ Evaluation Run")) { throw "Markdown report did not render expected title." }

  Write-Host "`n[9/12] Running evaluation through CLI..."
  Invoke-Checked { & $Python "scripts/run_evaluation.py" "--provider" "rule_based" "--top-k" "3" } "CLI evaluation failed."

  Write-Host "`n[10/12] Verifying reports exist..."
  $reports = Get-ChildItem -Path (Join-Path $RepoRoot "eval_reports") -Filter "evaluation_run_*.md"
  if ($reports.Count -lt 1) { throw "No evaluation markdown reports were written." }

  Write-Host "`n[11/12] Running normal test suite..."
  Invoke-Checked { & $Pytest } "Normal pytest suite failed."
}
finally {
  if ($api -and -not $api.HasExited) { Stop-Process -Id $api.Id -Force }
}

Write-Host "`n[12/12] Phase 7 checklist:"
Write-Host "- PostgreSQL, Redis, and Qdrant started"
Write-Host "- Migrations applied"
Write-Host "- Seed knowledge indexed"
Write-Host "- Evaluation dataset loaded"
Write-Host "- Evaluation API created run and items"
Write-Host "- Retrieval, analysis, workflow, groundedness, and latency metrics computed"
Write-Host "- Markdown report endpoint verified"
Write-Host "- CLI evaluation verified"
Write-Host "- Normal pytest completed"
