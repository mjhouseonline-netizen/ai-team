@echo off
echo.
echo ========================================
echo    Starting AI Team Web Interface
echo ========================================
echo.
echo Opening in your browser...
echo.
echo To stop: Close this window or press Ctrl+C
echo.

cd /d "%~dp0"
python web_app.py

pause
