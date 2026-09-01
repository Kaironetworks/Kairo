$ErrorActionPreference = 'Stop'
Write-Host "KAIRO final stack check"
Write-Host "[1] PostgreSQL/MinIO containers"
docker ps --format "table {{.Names}}\t{{.Status}}" | Select-String 'kairo-postgres|kairo-minio'
Write-Host "[2] API"
try { (Invoke-WebRequest http://127.0.0.1:8000/docs -UseBasicParsing -TimeoutSec 3).StatusCode } catch { Write-Warning "API is not reachable on :8000" }
Write-Host "[3] Fabric Gateway"
try { Invoke-RestMethod http://127.0.0.1:8090/health | ConvertTo-Json } catch { Write-Warning "Gateway is not reachable on :8090" }
