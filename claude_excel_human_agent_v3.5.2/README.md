# Claude Excel Human Automation Agent v3.5.2

This is the Claude.ai counterpart to the ChatGPT Excel Human Automation Agent. It does NOT automate Anthropic account login.

It connects to a Chrome instance that you start yourself with remote debugging enabled. You manually log in to Claude.ai in that Chrome window, then the agent attaches to the already-authenticated browser.

No Anthropic API key.

## Setup

**Quickest path: double-click `run.bat`.** It runs first-time setup automatically if needed, starts Chrome with remote debugging, waits for you to log in, then launches `app.py` - all from one window. Skip to step 6 below once it's running.

Manual / step-by-step version (same thing, split across two windows):
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

## Interrupted / multi-day runs

Large files can take a long time to fully process, and the run may need to stop partway through — power loss, the PC restarting, closing the terminal, etc. This is safe: every row's result is saved to the output file immediately (not just at the end), and each save is written atomically so an abrupt interruption mid-save can't corrupt the file. When you run `python app.py` again on the same input file, it detects the existing output file and asks:

```
Found an existing output file from a previous run: products_processed.xlsx
  [1] Resume from where it left off (recommended)
  [2] Start over (overwrites the existing progress)
```

Choosing **Resume** picks up exactly where it stopped - rows already marked `COMPLETED` (per task) are skipped, and it prints how many rows are left before continuing. Choosing **Start over** re-copies a clean version from the original input file, discarding all progress (useful if you fixed something in the input and want a clean re-run).

If it stops early for any reason, just run `run.bat` (or `python app.py`) again - same file, same Claude URL, same task choice - and pick **Resume**.

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
