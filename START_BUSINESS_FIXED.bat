@echo off
echo.
echo ========================================
echo    Starting AI Team (Business Model)
echo ========================================
echo.

REM Set your central API key here
set ANTHROPIC_API_KEY=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

echo Checking API key...
if "%ANTHROPIC_API_KEY%"=="your-api-key-here" (
    echo.
    echo ERROR: Please edit this file and add your API key!
    echo Open START_BUSINESS.bat in Notepad and replace 'your-api-key-here'
    echo with your actual Anthropic API key.
    echo.
    pause
    exit
)

echo API key configured!
echo Opening in your browser...
echo.
echo To stop: Close this window or press Ctrl+C
echo.

cd /d "%~dp0"
python web_app_auth.py

pause
