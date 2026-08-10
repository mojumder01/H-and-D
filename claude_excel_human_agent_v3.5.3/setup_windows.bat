@echo off
setlocal
echo ==========================================
echo Claude Excel Human Automation Agent v3.5.3
echo ==========================================
python -m venv .venv
if errorlevel 1 (
    echo Failed to create the virtual environment. Is Python installed and on PATH?
    exit /b 1
)
call .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 (
    echo Failed to install dependencies - see the error above.
    exit /b 1
)
python -m playwright install chromium
if errorlevel 1 (
    echo Failed to install the Playwright browser - see the error above.
    exit /b 1
)
if not exist input mkdir input
if not exist output mkdir output
if not exist logs mkdir logs
echo.
echo Setup complete.
echo Next:
echo 1. Run start_chrome.bat
echo 2. Log in to Claude manually
echo 3. Run python app.py
pause
