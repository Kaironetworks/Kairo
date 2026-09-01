$ErrorActionPreference = "Continue"
Write-Host "KAIRO FINAL DEMO CHECK" -ForegroundColor Cyan
Write-Host "======================="
function Check-Url($name, $url) {
  try { $r=Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 5; Write-Host "[PASS] $name -> $($r.StatusCode)"; return $true }
  catch { Write-Host "[FAIL] $name -> $($_.Exception.Message)" -ForegroundColor Red; return $false }
}
$core=Check-Url "FastAPI health" "http://127.0.0.1:8000/api/health"
$gateway=Check-Url "Fabric Gateway health" "http://127.0.0.1:8090/health"
$frontend=Check-Url "Frontend" "http://127.0.0.1:5173"
Write-Host ""
if($core -and $frontend){Write-Host "CORE STACK: READY" -ForegroundColor Green}else{Write-Host "CORE STACK: NOT READY" -ForegroundColor Yellow}
if($gateway){Write-Host "FABRIC GATEWAY: REACHABLE" -ForegroundColor Green}else{Write-Host "FABRIC GATEWAY: OPTIONAL / NOT REACHABLE" -ForegroundColor Yellow}
