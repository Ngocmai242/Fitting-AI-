@echo off
echo ===================================================
echo   AURAFIT SYSTEM STARTUP
echo ===================================================
echo.
echo [1/3] Killing old processes...
taskkill /F /IM python.exe >nul 2>&1
echo.

echo [2/3] Starting Backend Server (Port 5050)...
start "AuraFit Backend" cmd /k "cd backend && python app.py"
timeout /t 5 >nul

echo [3/3] Starting Frontend Server (Port 3000)...
echo       Please wait for browser to open...
start "AuraFit Frontend" cmd /k "python -m http.server 3000"
timeout /t 2 >nul

echo.
echo [DONE] Opening Admin Login Page...
start http://localhost:3000/frontend/admin_login.html

echo.
echo SYSTEM IS RUNNING.
echo DO NOT CLOSE THIS WINDOW or the other Black Command Windows.
echo.
pause
