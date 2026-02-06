@echo off
title AuraFit Debugger
cd /d "%~dp0"
echo.
echo ===================================================
echo   AURAFIT DEBUG LAUNCHER
echo ===================================================
echo.
echo [1] Killing old processes...
taskkill /F /IM python.exe 2>nul
echo.

echo [2] Checking Python...
python --version 
if %errorlevel% neq 0 (
    echo Python not found.
    pause
    exit
)
echo Python found.

echo [3] Installing Requirements...
pip install -r backend/requirements.txt
if %errorlevel% neq 0 (
    echo Warning: Pip install failed.
)

echo.
echo [4] STARTING SERVER...
echo Running: python backend/run.py
echo.
echo Please look closely at the output below.
echo ---------------------------------------------------
cd backend
python run.py
echo ---------------------------------------------------
echo.
echo Server has stopped.
pause
