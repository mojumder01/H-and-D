@echo off
echo ==========================================
echo Claude Excel Human Automation Agent v2
echo ==========================================
python -m venv .venv
call .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m playwright install chromium
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
