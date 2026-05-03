$ErrorActionPreference = "Stop"

Write-Host "Phase 1.1.5 live runtime verification"
Write-Host "This script requires Docker, Python dependencies, and a free localhost:8000."

Write-Host "`n[1/9] Starting PostgreSQL..."
docker compose up feedbackiq-db -d

Write-Host "`n[2/9] Docker Compose status..."
docker compose ps

Write-Host "`n[3/9] Running Alembic migrations against live PostgreSQL..."
python -m alembic upgrade head

Write-Host "`n[4/9] Verifying feedback_records table exists..."
docker compose exec feedbackiq-db psql -U feedbackiq -d feedbackiq -c "\dt"

Write-Host "`n[5/9] Starting API on http://127.0.0.1:8000 ..."
$server = Start-Process `
  -FilePath python `
  -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000" `
  -WindowStyle Hidden `
  -PassThru

try {
  Start-Sleep -Seconds 5

  Write-Host "`n[6/9] Health check..."
  Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/health" -Method Get | ConvertTo-Json -Depth 20

  Write-Host "`n[7/9] Creating feedback record..."
  $created = Invoke-RestMethod `
    -Uri "http://127.0.0.1:8000/api/v1/feedback-records" `
    -Method Post `
    -ContentType "application/json" `
    -Body '{"text":"Checkout payment failed during live verification."}'
  $created | ConvertTo-Json -Depth 20
  $feedbackId = $created.data.id

  Write-Host "`n[8/9] Reading, listing, and updating feedback record..."
  Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/feedback-records/$feedbackId" -Method Get | ConvertTo-Json -Depth 20
  Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/feedback-records?limit=10&offset=0" -Method Get | ConvertTo-Json -Depth 20
  Invoke-RestMethod `
    -Uri "http://127.0.0.1:8000/api/v1/feedback-records/$feedbackId/status" `
    -Method Patch `
    -ContentType "application/json" `
    -Body '{"processing_status":"FAILED","error_code":"live_verification","error_message":"Phase 1.1.5 live verification status update."}' |
    ConvertTo-Json -Depth 20

  Write-Host "`n[9/9] Running normal test suite..."
  pytest
}
finally {
  if ($server -and -not $server.HasExited) {
    Stop-Process -Id $server.Id -Force
  }
}

Write-Host "`nPhase 1.1.5 live runtime verification complete."
