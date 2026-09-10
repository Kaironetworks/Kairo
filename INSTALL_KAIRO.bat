@echo off
setlocal EnableExtensions
title KAIRO - Installation Check

echo.
echo ==========================================
echo          KAIRO INSTALLER / PREFLIGHT
echo ==========================================
echo.

where py >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python Launcher ^(py^) was not found.
    echo Install Python 3.11+ and try again.
    pause
    exit /b 1
)

echo [OK] Python Launcher found.
py --version
echo.

if not exist "%~dp0backend\requirements.txt" (
    echo [ERROR] backend\requirements.txt is missing.
    pause
    exit /b 1
)

if not exist "%~dp0.venv\Scripts\python.exe" (
    echo [INFO] Creating KAIRO virtual environment...
    py -3 -m venv "%~dp0.venv"
    if errorlevel 1 (
        echo [ERROR] Could not create the virtual environment.
        pause
        exit /b 1
    )
)

echo [OK] Virtual environment ready.
echo.
echo [INFO] Installing KAIRO dependencies...
"%~dp0.venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 (
    echo [ERROR] pip upgrade failed.
    pause
    exit /b 1
)

"%~dp0.venv\Scripts\python.exe" -m pip install -r "%~dp0backend\requirements.txt"
if errorlevel 1 (
    echo [ERROR] Dependency installation failed.
    echo Check your internet connection and run this installer again.
    pause
    exit /b 1
)

echo.
echo [INFO] Verifying installed dependencies...
"%~dp0.venv\Scripts\python.exe" -c "import fastapi, uvicorn, jwt, multipart; print('KAIRO dependencies verified.')"
if errorlevel 1 (
    echo [ERROR] Dependency verification failed.
    pause
    exit /b 1
)

echo.
echo ==========================================
echo       KAIRO INSTALLATION COMPLETE
echo ==========================================
echo.
echo Next step: run START_KAIRO.bat
echo.
pause
