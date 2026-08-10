@echo off
setlocal
cd /d "%~dp0"

echo ==========================================
echo Claude Excel Human Automation Agent v3.5.1
echo ==========================================
echo.

if not exist ".venv" (
    echo No virtual environment found - running first-time setup...
    echo.
    call setup_windows.bat
    if errorlevel 1 (
        echo Setup failed. Fix the error above and run this again.
        pause
        exit /b 1
    )
)

echo Starting Chrome with remote debugging...
start "" "%~dp0start_chrome.bat"

echo.
echo ==========================================
echo  In the Chrome window that just opened:
echo  - Log in to Claude.ai manually if needed.
echo  - Complete any verification/CAPTCHA manually.
echo  - Leave that Chrome window OPEN.
echo ==========================================
echo.
pause

call .venv\Scripts\activate
python app.py

echo.
echo ==========================================
echo  If this stopped early (closed window, power
echo  loss, Chrome crash, etc.), just run this file
echo  again - it resumes from where it left off,
echo  it will not redo finished rows.
echo ==========================================
pause
