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
| `Claude message input not found.` | Claude.ai changed its input DOM | `browser/claude_agent.py` → `_input()` selector list (`div[data-testid="chat-input"]` is the confirmed real one) |
| `Message was sent but no new Claude reply turn appeared on the page within the timeout.` | `TURN_SELECTOR`/`RESPONSE_SELECTOR` in `browser/claude_agent.py` don't match anything on the real page (Claude.ai changed its DOM again) | `browser/claude_agent.py` |
| `Claude was still generating a reply when the timeout was reached.` | Response genuinely took longer than `RESPONSE_TIMEOUT_MS` (e.g. a "High" reasoning-effort model thinking longer, or a long product description) | `config.py`/`.env` → raise `RESPONSE_TIMEOUT_MS` |
| `Message was not accepted by Claude's composer after 3 attempts...` | The click/Enter didn't actually submit the message (composer still had the text). Previously this manifested as a silent 2-minute `TimeoutError` per row since the code waited the full `RESPONSE_TIMEOUT_MS` for a reply to a message that was never sent - fixed by confirming delivery via `[data-testid="user-message"]` bubble count within ~8s and retrying the send instead of waiting it out | `browser/claude_agent.py` → `_submit()` |
| Output columns are filled with the literal prompt template (e.g. `Highlights HTML` = `<ul>\n<li>...</li>\n</ul>`, `Description HTML` ends with the `Rules:` block) marked `COMPLETED` | **Fixed — was the root cause of "doesn't wait after input".** The assistant-selector guesses matched nothing, so the old code fell back to `page.locator("body").inner_text()`. Since the prompt template itself contains the literal words `HIGHLIGHTS_HTML`/`DESCRIPTION_HTML`, the agent's own just-submitted (echoed) message satisfied the "response arrived" check instantly, before Claude ever replied. Fixed by confirming the real DOM against a live conversation (see below) and switching to `data-is-streaming="false"` for completion detection — never falls back to whole-page text. | `browser/claude_agent.py` |
| Description HTML column has a trailing sentence after the last `</p>` (e.g. "Note: I dropped X since...") | Claude appended an explanatory note after the code block, which `_match_headings()` used to capture along with everything else to end-of-text | `browser/parser.py` → `_trim_after_last_closing_tag()` now truncates at the last `</ul>`/`</p>`; fixed |
| `Could not identify both HTML sections.` / `Invalid highlights HTML.` / `Invalid description HTML.` | Claude added conversational text, used markdown instead of raw HTML, or used the wrong tags | `browser/prompt.py` (tighten instructions) and/or `browser/parser.py` (loosen regex) |
| Output quality is bad (invented specs, wrong tone, missing facts) | Prompt wording, not code | `browser/prompt.py` — describe the bad example row and what you wanted instead |
| Rows silently marked `FAILED` after 3 tries | Real error captured in the `Error` column of the output Excel — read that first | `config.py` `MAX_RETRIES` / `RESPONSE_TIMEOUT_MS` if it's just timing |
| A row shows `COMPLETED` but you want to know if it needed a retry | `Error` column on a `COMPLETED` row now carries a note like `attempt 1 failed: ...` if earlier attempts failed before it eventually succeeded, instead of being silently wiped blank | `app.py` (`prior_errors` tracking) |
| Wrong/missing input columns | Excel doesn't have `Product Name` / `Highlights` / `Description` headers | `excel/reader.py` (column lookup is by header name, row 1) |

## What to paste back into the chat when asking for a fix

1. The exact error message or the row's `Error` column value.
2. If it's a selector problem: the relevant `view-source:` HTML snippet around the chat input box or the assistant message container (Claude's DOM does change between releases — this project's selectors were written from general patterns, not a live inspection, so they may need one round of correction against the real page).
3. If it's an output-quality problem: one example row (`Product Name` / `Highlights` / `Description` in, vs. what Claude returned) and what's wrong with it.

## Confirmed selectors (verified against a live claude.ai DOM dump)

- Input box: `div[data-testid="chat-input"]` (a `contenteditable` div with class `tiptap ProseMirror`).
- Each reply turn: `div[data-is-streaming="..."]` — `"true"` while Claude is still generating, `"false"` once done. This is the authoritative completion signal `browser/claude_agent.py` waits on, instead of guessing from text stability.
- The reply body itself: `.font-claude-response` (nested inside the turn div above). **Not** `.font-claude-message` — that was the original wrong guess and the actual root cause of the "doesn't wait" bug: the guessed class matched nothing, so the old code fell back to whole-page text and grabbed the echoed prompt instead.
- Claude often formats the reply as a bold **Highlights**/**Description** heading followed by a rendered code block, rather than obeying the literal `HIGHLIGHTS_HTML`/`DESCRIPTION_HTML` tokens from the prompt. `browser/parser.py` handles both shapes.
- Send button: `button[aria-label="Send message"]` (only appears once the composer has text — an empty composer shows a voice/mic button instead). Confirmed against a live DOM dump captured with text typed into the box.

All selectors in `browser/claude_agent.py` are now confirmed against real DOM dumps, not guesses. If the automation still misbehaves after a Claude.ai UI update, the fix is the same process: type into the composer, right-click the input/send button/a reply → Inspect → copy `outerHTML`, and update the relevant selector.
