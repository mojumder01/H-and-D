# Claude Excel Human Automation Agent v2

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
7. Paste the Claude conversation URL (an existing `https://claude.ai/chat/...` conversation, or a fresh `https://claude.ai/new` chat).
8. The agent processes rows one by one and saves the result in `output/`.

Important:
- Close all normal Chrome windows before `start_chrome.bat` if Chrome refuses the custom profile.
- The project uses a separate `chrome_agent_profile` folder so it does not need to touch your normal Chrome profile.
- Do not enter your password into the Python program.
- Any verification/CAPTCHA is always completed manually.
- Claude.ai's DOM selectors may change over time; if the agent can't find the input box or can't detect a response, update the selector lists in `browser/claude_agent.py`.

## Excel

Required columns:
Product Name
Highlights
Description

Output columns:
Highlights HTML
Description HTML
Status
Retry
Error

A demo file is included at `input/DEMO_products.xlsx`.
