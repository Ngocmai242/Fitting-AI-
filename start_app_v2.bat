@echo off
title AuraFit Server
cd /d "%~dp0"
echo ===================================================
echo   AURAFIT LAUNCHER (ROBUST MODE)
echo ===================================================
echo.
echo [1] Cleaning up old processes...
taskkill /F /IM python.exe >nul 2>&1

echo [2] Checking Python...
python --version
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Python not found! 
    echo Please install Python from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b
)
echo Python found.

echo [3] Checking Libraries...
echo Installing/Verifying required packages...
pip install -r backend/requirements.txt
if %errorlevel% neq 0 (
    echo.
    echo [WARNING] Pip install encountered errors.
    echo attempting to continue, but server might fail...
) else (
    echo Libraries are ready.
)

echo.
echo [4] STARTING SERVER...
echo ---------------------------------------------------
echo 1. The server will start in this window.
echo 2. The website will open in 5 seconds.
echo 3. DO NOT CLOSE THIS WINDOW.
echo ---------------------------------------------------

:: Start browser in 5 seconds
:: We use 127.0.0.1 explicitly to avoid 'localhost' IPv6 issues
start "" cmd /c "timeout /t 5 >nul && start http://127.0.0.1:8080/admin_login.html"

:: Run Python in THIS window with Auto-Restart Loop
cd backend

:SERVER_LOOP
echo.
echo ===================================================
echo [INFO] STARTING PRODUCTION SERVER (WAITRESS)
echo ===================================================
echo.
python server.py

:: If python crashes, we reach here
echo.
echo ===================================================
echo [CRITICAL] SERVER STOPPED UNEXPECTEDLY
echo ===================================================
echo Restarting in 2 seconds to ensure connectivity...
timeout /t 2 >nul
goto SERVER_LOOP
