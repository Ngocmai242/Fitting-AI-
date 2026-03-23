@echo off
echo ===================================================
echo   AURAFIT SYSTEM STARTUP (FIXED)
echo ===================================================
echo.
echo [1/2] Killing old processes...
taskkill /F /IM python.exe >nul 2>&1
echo.

echo [2/2] Starting AuraFit Server (Waitress Port 8080)...
echo       The backend will serve both API and Frontend.
start "AuraFit Backend" cmd /k "cd backend && python server.py"
timeout /t 5 >nul

echo.
echo [DONE] Opening Admin Login Page...
start http://127.0.0.1:8080/admin_login.html

echo.
echo SYSTEM IS RUNNING.
echo DO NOT CLOSE THIS WINDOW or the other Black Command Windows.
echo.
pause
