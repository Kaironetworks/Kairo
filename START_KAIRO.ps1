$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Write-Host "KAIRO :: secure local environment" -ForegroundColor Cyan

foreach ($tool in @("docker","node","npm","python")) {
  if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) { throw "$tool is required." }
}

docker compose -f (Join-Path $Root "docker-compose.yml") up -d

$backend = Join-Path $Root "backend"
$venv = Join-Path $backend ".venv\Scripts\python.exe"
if (-not (Test-Path $venv)) {
  Write-Host "Creating backend virtual environment..." -ForegroundColor Yellow
  python -m venv (Join-Path $backend ".venv")
  & $venv -m pip install -r (Join-Path $backend "requirements.txt")
}

$envFile = Join-Path $backend ".env"
if (-not (Test-Path $envFile)) {
  $secret = (& $venv -c "import secrets; print(secrets.token_urlsafe(48))")
  @"
DATABASE_URL=postgresql+psycopg://kairo:kairo_dev_password@127.0.0.1:5433/kairo
JWT_SECRET=$secret
JWT_EXPIRE_MINUTES=120
MINIO_ENDPOINT=http://127.0.0.1:9000
MINIO_ACCESS_KEY=kairoadmin
MINIO_SECRET_KEY=kairo_minio_password
MINIO_BUCKET=kairo-documents
CORS_ORIGINS=http://127.0.0.1:5173
"@ | Set-Content $envFile
  Write-Host "Created local backend/.env with a random session secret." -ForegroundColor Yellow
}

Push-Location $backend
try { & $venv -m app.seed } finally { Pop-Location }

$frontend = Join-Path $Root "frontend"
if (-not (Test-Path (Join-Path $frontend "node_modules"))) {
  Push-Location $frontend
  try { npm ci } finally { Pop-Location }
}

Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$backend'; & '$venv' -m uvicorn app.main:app --host 127.0.0.1 --port 8000"

if (Test-Path (Join-Path $frontend "dist")) {
  Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$frontend'; npm run preview -- --host 127.0.0.1 --port 5173"
} else {
  Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$frontend'; npm run dev -- --host 127.0.0.1 --port 5173"
}

Start-Sleep -Seconds 3
Start-Process "http://127.0.0.1:5173"
Write-Host "KAIRO started at http://127.0.0.1:5173" -ForegroundColor Green
Write-Host "Run BUILD_KAIRO.ps1 before a release/demo build to use the production frontend bundle." -ForegroundColor DarkGray
