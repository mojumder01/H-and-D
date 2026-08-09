# Agent Brief — Claude Excel Human Automation Agent v1

Bring this file (and, if relevant, the `output/*_processed.xlsx` you were running) back to a Claude chat when something breaks or the generated HTML looks wrong. This doc tells the assistant what the project expects, so it can diagnose from the symptom instead of re-reading everything from scratch.

## What this project does

`app.py` reads product rows from an Excel file, sends each row to a Claude.ai conversation already open in a human-logged-in Chrome (via CDP, `browser/chrome_connector.py`), waits for a reply containing two tagged HTML sections, and writes them back into the same workbook (`Highlights HTML`, `Description HTML`, `Status`, `Retry`, `Error` columns).

## The contract Claude's reply must satisfy

Defined in `browser/prompt.py` and enforced by `browser/parser.py`:

```
HIGHLIGHTS_HTML
<ul><li>...</li></ul>

DESCRIPTION_HTML
<p>...</p><p>...</p>
```

- No preamble ("Here is the HTML...") — `parser.py` doesn't strip it, and if there's no preamble rule violation it usually means `prompt.py`'s "no preamble" rule needs to be stated more forcefully, or the parser's regex needs to tolerate it.
- Highlights must use `<ul>/<li>` only; description must use `<p>` only. Anything else fails `extract_sections()` in `browser/parser.py`.
- Claude must not invent facts not present in the row's `Highlights`/`Description`/`Product Name` columns.

## Failure modes and where to look

| Symptom | Likely cause | Fix location |
|---|---|---|
| `Claude message input not found.` | Claude.ai changed its input DOM (contenteditable class, placeholder text) | `browser/claude_agent.py` → `_input()` selector list |
| Agent sends the prompt but never detects a reply (times out) | Message container selector stale, or Claude wrapped the answer in extra markup | `browser/claude_agent.py` → `_assistant_text()` selector list |
| `Could not identify both HTML sections.` / `Invalid highlights HTML.` / `Invalid description HTML.` | Claude added conversational text, used markdown instead of raw HTML, or used the wrong tags | `browser/prompt.py` (tighten instructions) and/or `browser/parser.py` (loosen regex) |
| Output quality is bad (invented specs, wrong tone, missing facts) | Prompt wording, not code | `browser/prompt.py` — describe the bad example row and what you wanted instead |
| Rows silently marked `FAILED` after 3 tries | Real error captured in the `Error` column of the output Excel — read that first | `config.py` `MAX_RETRIES` / `RESPONSE_TIMEOUT_MS` if it's just timing |
| Wrong/missing input columns | Excel doesn't have `Product Name` / `Highlights` / `Description` headers | `excel/reader.py` (column lookup is by header name, row 1) |

## What to paste back into the chat when asking for a fix

1. The exact error message or the row's `Error` column value.
2. If it's a selector problem: the relevant `view-source:` HTML snippet around the chat input box or the assistant message container (Claude's DOM does change between releases — this project's selectors were written from general patterns, not a live inspection, so they may need one round of correction against the real page).
3. If it's an output-quality problem: one example row (`Product Name` / `Highlights` / `Description` in, vs. what Claude returned) and what's wrong with it.

## Current known limitation

`browser/claude_agent.py`'s selectors (`div[contenteditable="true"].ProseMirror`, `.font-claude-message`, `[data-testid="chat-message"]`, `button[aria-label="Send Message"]`) are best-guess from known Claude.ai UI patterns, not verified against a live DOM dump. Treat the first real run as a validation pass — if the input box or reply detection fails, that's expected on the first try; paste the real markup back here and the selectors will be corrected.
