@echo off
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0START_KAIRO.ps1"
if errorlevel 1 (
  echo.
  echo KAIRO failed to start. Keep this window open and read the error above.
  pause
)
