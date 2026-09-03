$ErrorActionPreference = "Continue"
Write-Host "KAIRO CORE RELEASE CHECK" -ForegroundColor Cyan
Write-Host "========================"
$root = Split-Path -Parent $PSScriptRoot
$checks = @()
$checks += @{Name="Docker"; Ok=[bool](Get-Command docker -ErrorAction SilentlyContinue)}
$checks += @{Name="Node"; Ok=[bool](Get-Command node -ErrorAction SilentlyContinue)}
$checks += @{Name="Python"; Ok=[bool](Get-Command python -ErrorAction SilentlyContinue)}
$checks += @{Name="Frontend manifest"; Ok=Test-Path (Join-Path $root "frontend/package.json")}
$checks += @{Name="Backend requirements"; Ok=Test-Path (Join-Path $root "backend/requirements.txt")}
$checks += @{Name="Docker compose"; Ok=Test-Path (Join-Path $root "docker-compose.yml")}
$checks += @{Name="KAIRO README"; Ok=Test-Path (Join-Path $root "README.md")}
foreach($c in $checks){ if($c.Ok){Write-Host "[PASS] $($c.Name)" -ForegroundColor Green}else{Write-Host "[FAIL] $($c.Name)" -ForegroundColor Red} }
try { Invoke-WebRequest http://127.0.0.1:8000/api/health -UseBasicParsing -TimeoutSec 3 | Out-Null; Write-Host "[PASS] API health" -ForegroundColor Green } catch { Write-Host "[WARN] API not running" -ForegroundColor Yellow }
try { Invoke-WebRequest http://127.0.0.1:5173 -UseBasicParsing -TimeoutSec 3 | Out-Null; Write-Host "[PASS] Frontend" -ForegroundColor Green } catch { Write-Host "[WARN] Frontend not running" -ForegroundColor Yellow }
try { Invoke-RestMethod http://127.0.0.1:8090/health | Out-Null; Write-Host "[PASS] Fabric gateway" -ForegroundColor Green } catch { Write-Host "[INFO] Fabric gateway not running (optional until blockchain demo)" -ForegroundColor Yellow }
