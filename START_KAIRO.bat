@echo off
setlocal
cd /d "%~dp0"
title KAIRO - Secure Evidence Platform
if not exist ".venv\Scripts\python.exe" (
  echo [INFO] Creating Python environment...
  py -3 -m venv .venv || goto :fail
)
if not exist ".venv\Lib\site-packages\fastapi" (
  echo [INFO] Installing backend dependencies...
  .venv\Scripts\python.exe -m pip install -r backend\requirements.txt || goto :fail
)
echo.
echo KAIRO is starting on all network interfaces.
echo Other laptops on the same Wi-Fi can use the LAN address printed below.
echo.
.venv\Scripts\python.exe start.py
exit /b %errorlevel%
:fail
echo.
echo KAIRO could not start. Install Python 3.11+ and check your network connection.
pause
exit /b 1
