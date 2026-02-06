@echo off
echo ===================================================
echo   AURAFIT INTEGRATED SERVER (FINAL FIX)
echo ===================================================
echo.
echo [1/2] Terminating old servers...
taskkill /F /IM python.exe >nul 2>&1
echo.

echo [2/2] Starting AuraFit Unified Server...
echo       Web Interface: http://localhost:8080
echo.
echo       -> Please wait for the browser to open...
echo.

:: Launch start_app_v2.bat which now has the robust loop
call start_app_v2.bat

echo.
echo SERVER SESSION ENDED.
pause
