$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Frontend = Join-Path $Root "frontend"

if (-not (Get-Command node -ErrorAction SilentlyContinue)) { throw "Node.js 18+ is required." }
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) { throw "npm is required." }

Push-Location $Frontend
try {
  if (-not (Test-Path "node_modules")) {
    Write-Host "Installing locked frontend dependencies..." -ForegroundColor Yellow
    npm ci
  }
  Write-Host "Building KAIRO frontend..." -ForegroundColor Cyan
  npm run build
} finally { Pop-Location }

Write-Host "KAIRO frontend build complete: frontend/dist" -ForegroundColor Green
