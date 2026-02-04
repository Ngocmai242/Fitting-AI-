@echo off
echo ===================================================
echo   AURAFIT REFACTORED LAUNCHER
echo ===================================================
echo.

echo [1/4] Checking Environment...
cd /d "%~dp0"
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo CRITICAL ERROR: Python is not installed or not in PATH.
    echo Please install Python 3.9+ and try again.
    pause
    exit /b
)
echo Python found.

echo.
echo [2/4] Installing Dependencies (This may take a while)...
pip install Flask flask-sqlalchemy flask-cors werkzeug
if %errorlevel% neq 0 (
    echo Warning: Could not auto-install dependencies. 
    echo Assuming they are already installed...
) else (
    echo Dependencies installed.
)

echo.
echo [3/4] Starting Backend Server (Port 5050)...
echo       Starting from backend/run.py
taskkill /F /IM python.exe >nul 2>&1
start "AuraFit Backend" cmd /k "cd backend && python run.py || pause"

echo.
echo [4/4] Waiting 10 seconds for server to boot...
timeout /t 10 >nul

echo.
echo [DONE] Opening Application...
echo. 
echo IMPORTANT:
echo Please use the browser window that opens automatically (Port 5050).
echo DO NOT use "Go Live" or Port 5500 from VS Code.
echo.
start http://localhost:5050/
start http://localhost:5050/admin_login.html

echo.
echo ===================================================
echo   SYSTEM RUNNING
echo ===================================================
echo   - Backend: http://localhost:5050
echo   - Frontend: Served by Backend
echo.
echo   DO NOT CLOSE THE BLACK BACKEND WINDOW.
echo ===================================================
pause
