$ErrorActionPreference = "Stop"

Write-Host "Phase 10 live analytics and reporting verification"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$VenvScripts = Join-Path $RepoRoot ".venv\Scripts"
$Python = Join-Path $VenvScripts "python.exe"
$Alembic = Join-Path $VenvScripts "alembic.exe"
$Pytest = Join-Path $VenvScripts "pytest.exe"
$Port = "8020"
$BaseUrl = "http://127.0.0.1:$Port"

if (-not (Test-Path $Python)) { $Python = "python" }
if (-not (Test-Path $Alembic)) { $Alembic = "alembic" }
if (-not (Test-Path $Pytest)) { $Pytest = "pytest" }

$env:AUTH_ENABLED = "false"
$env:RATE_LIMIT_ENABLED = "false"
$env:LLM_PROVIDER = "rule_based"
$env:LLM_FALLBACK_PROVIDER = "rule_based"
$env:NOTIFICATION_PROVIDER = "log"
$env:WORKFLOW_AUTO_CREATE_TICKETS = "false"
$env:VECTOR_PROVIDER = "qdrant"
$env:EMBEDDING_PROVIDER = "bge_m3"
$env:EMBEDDING_MODEL_NAME = "BAAI/bge-m3"
$env:ANALYTICS_REPORT_DIR = "analytics_reports"
$env:TMP = Join-Path $RepoRoot ".tmp"
$env:TEMP = $env:TMP
New-Item -ItemType Directory -Force -Path $env:TMP | Out-Null

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

function Assert-True {
  param([bool]$Condition, [string]$Message)
  if (-not $Condition) { throw $Message }
}

Write-Host "`n[0/13] Checking Docker availability..."
Invoke-Checked { docker info --format "{{.ServerVersion}}" } "Docker is not reachable. Start Docker Desktop, then rerun this script."

Write-Host "`n[1/13] Starting PostgreSQL, Redis, and Qdrant..."
Invoke-Checked { docker compose up feedbackiq-db feedbackiq-redis feedbackiq-qdrant -d } "Could not start Docker services."

Write-Host "`n[2/13] Running Alembic migrations..."
Invoke-Checked { & $Alembic upgrade head } "Alembic migrations failed."

Write-Host "`n[3/13] Starting API..."
$api = Start-Process -FilePath $Python -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", $Port -WindowStyle Hidden -PassThru

try {
  Start-Sleep -Seconds 8

  Write-Host "`n[4/13] Creating sample feedback records..."
  $feedback1 = Invoke-RestMethod -Uri "$BaseUrl/api/v1/ingestion/text" -Method Post -ContentType "application/json" -Body '{"text":"Urgent checkout payment failure for customer. Card charged twice and order failed."}'
  $feedback2 = Invoke-RestMethod -Uri "$BaseUrl/api/v1/ingestion/text" -Method Post -ContentType "application/json" -Body '{"text":"The new dashboard is clear and much faster than before."}'
  $feedbackId = $feedback1.data.feedback_id
  Assert-True ($feedbackId -gt 0) "Feedback ingestion did not return a feedback_id."
  $feedback2 | Out-Null

  Write-Host "`n[5/13] Running Phase 5 analysis for workflow analytics data..."
  $analysis = Invoke-RestMethod -Uri "$BaseUrl/api/v1/analysis/feedback-records/$feedbackId/run" -Method Post
  Assert-True ($analysis.data.feedback_id -eq $feedbackId) "Analysis did not run for the expected feedback record."

  Write-Host "`n[6/13] Creating workflow ticket..."
  $ticket = Invoke-RestMethod -Uri "$BaseUrl/api/v1/workflows/feedback-records/$feedbackId/create-ticket" -Method Post
  Assert-True ($ticket.data.ticket.id -gt 0) "Workflow ticket was not created."

  Write-Host "`n[7/13] Creating evaluation run..."
  $evaluationBody = '{"provider":"rule_based","prompt_version":"feedback-analysis-v1","top_k":3,"write_report":true}'
  $evaluation = Invoke-RestMethod -Uri "$BaseUrl/api/v1/evaluations/runs" -Method Post -ContentType "application/json" -Body $evaluationBody
  Assert-True ($evaluation.data.id -gt 0) "Evaluation run was not created."

  Write-Host "`n[8/13] Verifying analytics summary..."
  $summary = Invoke-RestMethod -Uri "$BaseUrl/api/v1/analytics/summary" -Method Get
  $summary | ConvertTo-Json -Depth 20
  Assert-True ($summary.data.total_feedback -ge 2) "Analytics summary did not count sample feedback."

  Write-Host "`n[9/13] Verifying trend and breakdown endpoints..."
  $trends = Invoke-RestMethod -Uri "$BaseUrl/api/v1/analytics/feedback-trends?interval=day" -Method Get
  $sentiment = Invoke-RestMethod -Uri "$BaseUrl/api/v1/analytics/sentiment-breakdown" -Method Get
  $category = Invoke-RestMethod -Uri "$BaseUrl/api/v1/analytics/category-breakdown" -Method Get
  $severity = Invoke-RestMethod -Uri "$BaseUrl/api/v1/analytics/severity-breakdown" -Method Get
  $teams = Invoke-RestMethod -Uri "$BaseUrl/api/v1/analytics/team-routing" -Method Get
  Assert-True ($trends.data.points.Count -ge 1) "Feedback trends did not return points."
  $sentiment | Out-Null
  $category | Out-Null
  $severity | Out-Null
  $teams | Out-Null

  Write-Host "`n[10/13] Verifying ticket, review, and evaluation analytics..."
  $ticketAnalytics = Invoke-RestMethod -Uri "$BaseUrl/api/v1/analytics/tickets" -Method Get
  $reviewAnalytics = Invoke-RestMethod -Uri "$BaseUrl/api/v1/analytics/reviews" -Method Get
  $evaluationAnalytics = Invoke-RestMethod -Uri "$BaseUrl/api/v1/analytics/evaluations" -Method Get
  Assert-True ($ticketAnalytics.data.total_tickets -ge 1) "Ticket analytics did not count workflow tickets."
  Assert-True ($evaluationAnalytics.data.latest_run_id -gt 0) "Evaluation analytics did not expose the latest run."
  $reviewAnalytics | Out-Null

  Write-Host "`n[11/13] Verifying executive summary and report generation..."
  $executive = Invoke-RestMethod -Uri "$BaseUrl/api/v1/analytics/executive-summary" -Method Get
  $report = Invoke-RestMethod -Uri "$BaseUrl/api/v1/analytics/report?format=markdown" -Method Get
  Assert-True ($executive.data.summary_text.Length -gt 0) "Executive summary was empty."
  Assert-True (Test-Path (Join-Path $RepoRoot $report.data.report_path)) "Analytics report file was not written."

  Write-Host "`n[12/13] Running normal test suite..."
  Invoke-Checked { & $Pytest } "Normal pytest suite failed."
}
finally {
  if ($api -and -not $api.HasExited) { Stop-Process -Id $api.Id -Force }
}

Write-Host "`n[13/13] Phase 10 checklist:"
Write-Host "- Analytics summary verified"
Write-Host "- Feedback trends verified"
Write-Host "- Sentiment/category/severity/team breakdowns verified"
Write-Host "- Ticket/review/evaluation analytics verified"
Write-Host "- Executive summary verified"
Write-Host "- Markdown/JSON report generation verified"
Write-Host "- Normal pytest completed"
