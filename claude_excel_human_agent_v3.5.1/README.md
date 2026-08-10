# Claude Excel Human Automation Agent v3.5.1

This is the Claude.ai counterpart to the ChatGPT Excel Human Automation Agent. It does NOT automate Anthropic account login.

It connects to a Chrome instance that you start yourself with remote debugging enabled. You manually log in to Claude.ai in that Chrome window, then the agent attaches to the already-authenticated browser.

No Anthropic API key.

## Setup

1. Run `setup_windows.bat` once.
2. Run `start_chrome.bat`.
3. In the opened Chrome, manually log in to Claude.ai.
4. Keep Chrome open.
5. Run `python app.py` in another terminal.
6. Select an Excel file from `input/`.
7. Pick a sheet if there's more than one.
8. Choose what to run:
   - `[1]` Highlights + Description
   - `[2]` Weight (estimated shipping weight in kg)
   - `[3]` Both, in one combined message per row
9. Paste the Claude conversation URL (an existing `https://claude.ai/chat/...` conversation, or a fresh `https://claude.ai/new` chat).
10. The agent processes rows one by one and saves the result in `output/`.

You can run the same file through different modes on different occasions (e.g. Highlights+Description today, Weight tomorrow) — each task tracks its own completion, so re-running never redoes work that's already done, whichever mode you pick.

Important:
- Close all normal Chrome windows before `start_chrome.bat` if Chrome refuses the custom profile.
- The project uses a separate `chrome_agent_profile` folder so it does not need to touch your normal Chrome profile.
- Do not enter your password into the Python program.
- Any verification/CAPTCHA is always completed manually.
- Claude.ai's DOM selectors may change over time; if the agent can't find the input box or can't detect a response, update the selector lists in `browser/claude_agent.py`.

## Excel

Required input columns:
Product Name
Highlights
Description

(Weight mode only needs `Product Name` - `Highlights`/`Description` are used too when present, for a better estimate.)

Output columns (auto-added to your output file if missing - no manual setup needed):
- Highlights + Description mode: `Highlights HTML`, `Description HTML`, `Status`, `Retry`, `Error`
- Weight mode: `Weight (kg)`, `Weight Status`, `Weight Retry`, `Weight Error` (a plain number, e.g. `0.35` - no unit text; `unknown` if there's truly not enough information to estimate)

A demo file is included at `input/DEMO_products.xlsx`.
