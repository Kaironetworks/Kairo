@echo off
setlocal
cd /d "%~dp0"
title KAIRO - Install
py -3 --version >nul 2>&1 || (echo Python 3.11+ is required.&pause&exit /b 1)
if not exist ".venv\Scripts\python.exe" py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
.venv\Scripts\python.exe -c "import fastapi,uvicorn,jwt,multipart,sqlalchemy,boto3,cryptography; print('KAIRO dependencies verified.')"
echo.
echo Installation complete. Run START_KAIRO.bat
pause
