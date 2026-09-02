# KAIRO core stack launcher (PowerShell)
# Starts only PostgreSQL/MinIO through Docker and the FastAPI API.
# Fabric is deliberately separate.

$ErrorActionPreference = "Stop"
Set-Location "$PSScriptRoot\backend"

if (-not (Test-Path ".venv\Scripts\Activate.ps1")) {
  Write-Host "Backend virtual environment not found. Create/use the existing KAIRO .venv first." -ForegroundColor Yellow
  exit 1
}

& ".venv\Scripts\Activate.ps1"
Write-Host "KAIRO backend starting on http://127.0.0.1:8000" -ForegroundColor Cyan
uvicorn app.main:app --reload
