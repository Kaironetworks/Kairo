@echo off
setlocal
cd /d "%~dp0"
if "%~1"=="" (
  echo Usage: ATTACKVECTOR.bat http://HOST-IP:8000 EVIDENCE_ID VERSION
  exit /b 1
)
set HOST=%~1
set EID=%~2
set VER=%~3
if "%VER%"=="" set VER=1
if exist .venv\Scripts\python.exe (
  .venv\Scripts\python.exe attackvector\attack.py tamper --host %HOST% --evidence-id %EID% --version %VER%
) else (
  py -3 attackvector\attack.py tamper --host %HOST% --evidence-id %EID% --version %VER%
)
