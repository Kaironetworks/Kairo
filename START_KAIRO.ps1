# KAIRO local launcher. All paths are resolved relative to this script.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "KAIRO :: starting local services" -ForegroundColor Cyan

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { throw "Docker is required." }
if (-not (Get-Command node -ErrorAction SilentlyContinue)) { throw "Node.js is required." }

docker compose -f (Join-Path $Root "docker-compose.yml") up -d

$backend = Join-Path $Root "backend"
$venv = Join-Path $backend ".venv\Scripts\python.exe"
if (-not (Test-Path $venv)) {
  Write-Host "Creating backend virtual environment..." -ForegroundColor Yellow
  python -m venv (Join-Path $backend ".venv")
  & $venv -m pip install -r (Join-Path $backend "requirements.txt")
}

$frontend = Join-Path $Root "frontend"
if (-not (Test-Path (Join-Path $frontend "node_modules"))) {
  Write-Host "Installing frontend dependencies..." -ForegroundColor Yellow
  Push-Location $frontend
  npm ci
  Pop-Location
}

Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$backend'; & '$venv' -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$frontend'; npm run dev -- --host 127.0.0.1"

Start-Sleep -Seconds 2
Start-Process "http://127.0.0.1:5173"
Write-Host "KAIRO is starting: http://127.0.0.1:5173" -ForegroundColor Green
