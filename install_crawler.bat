@echo off
echo Installing dependencies...
pip install -r backend/requirements.txt
echo Installing Playwright browsers...
playwright install
echo Done! Please restart your server.
pause
