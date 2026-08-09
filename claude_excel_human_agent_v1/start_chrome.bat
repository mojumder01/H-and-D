@echo off
setlocal

set "CHROME_EXE=%ProgramFiles%\Google\Chrome\Application\chrome.exe"
if not exist "%CHROME_EXE%" set "CHROME_EXE=%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"
if not exist "%CHROME_EXE%" set "CHROME_EXE=%LocalAppData%\Google\Chrome\Application\chrome.exe"

if not exist "%CHROME_EXE%" (
    echo Chrome was not found.
    echo Edit this BAT file and set CHROME_EXE to your Chrome path.
    pause
    exit /b 1
)

set "PROFILE=%~dp0chrome_agent_profile"
if not exist "%PROFILE%" mkdir "%PROFILE%"

echo Starting dedicated Chrome automation profile...
echo Remote debugging port: 9222
echo.
echo IMPORTANT:
echo - Log in to Claude manually in this Chrome window.
echo - Complete any verification/CAPTCHA manually if shown.
echo - Keep this Chrome window OPEN while running app.py.
echo.

start "" "%CHROME_EXE%" --remote-debugging-port=9222 --user-data-dir="%PROFILE%" --no-first-run --no-default-browser-check "https://claude.ai/new"

endlocal
