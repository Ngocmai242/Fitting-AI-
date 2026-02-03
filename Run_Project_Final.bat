@echo off
echo ===================================================
echo   AURAFIT INTEGRATED SERVER (FINAL FIX)
echo ===================================================
echo.
echo [1/2] Terminating old servers...
taskkill /F /IM python.exe >nul 2>&1
echo.

echo [2/2] Starting AuraFit Unified Server...
echo       Web Interface: http://localhost:5050
echo.
echo       -> Please wait for the browser to open...
echo.

start "AuraFit Server" cmd /k "cd backend && python app.py"

REM Wait for server to boot
timeout /t 5 >nul

REM Open Admin Login directly from the backend server
start http://localhost:5050/admin_login.html

echo.
echo SERVER RUNNING.
echo If you close the black window, the website will stop.
pause
