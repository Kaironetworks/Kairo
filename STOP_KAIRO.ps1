$ErrorActionPreference = "SilentlyContinue"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
docker compose -f (Join-Path $Root "docker-compose.yml") stop
Write-Host "KAIRO core containers stopped. Existing data volumes are preserved." -ForegroundColor Yellow
