@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title KAIRO - Start

echo.
echo ==========================================
echo              KAIRO START
echo ==========================================
echo.

where py >nul 2>&1
if errorlevel 1 goto PYTHON_ERROR

if not exist ".venv\Scripts\python.exe" (
  echo [INFO] Creating Python environment...
  py -3 -m venv ".venv"
  if errorlevel 1 goto VENV_ERROR
)

echo [INFO] Checking backend dependencies...
".venv\Scripts\python.exe" -c "import fastapi,uvicorn,jwt,multipart,cryptography" >nul 2>&1
if errorlevel 1 (
  echo [INFO] Installing backend dependencies...
  ".venv\Scripts\python.exe" -m pip install -r "backend\requirements.txt"
  if errorlevel 1 goto INSTALL_ERROR
)

echo.
echo ==========================================
echo       KAIRO IS READY - NO DOCKER/NO NODE
echo ==========================================
echo.
echo The same server is shared by all laptops.
echo Keep this window open.
echo.

".venv\Scripts\python.exe" start.py
goto END

:PYTHON_ERROR
echo [ERROR] Python 3.11+ is required.
goto FAIL
:VENV_ERROR
echo [ERROR] Could not create the Python environment.
goto FAIL
:INSTALL_ERROR
echo [ERROR] Backend dependencies could not be installed.
goto FAIL
:FAIL
pause
:END
