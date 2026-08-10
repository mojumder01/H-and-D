# Agent Brief — Claude Excel Human Automation Agent v3.5.3

Bring this file (and, if relevant, the `output/*_processed.xlsx` you were running) back to a Claude chat when something breaks or the generated HTML looks wrong. This doc tells the assistant what the project expects, so it can diagnose from the symptom instead of re-reading everything from scratch.

## What this project does

`app.py` reads product rows from an Excel file, sends each row to a Claude.ai conversation already open in a human-logged-in Chrome (via CDP, `browser/chrome_connector.py`), waits for a reply, and writes the result back into the same workbook. It supports two independent tasks, selected at startup:

- `hd` (Highlights + Description): writes `Highlights HTML`, `Description HTML`, tracked via `Status`/`Retry`/`Error`.
- `weight` (Weight estimate): writes `Weight (kg)` (a plain number, no unit text, or `unknown`), tracked via `Weight Status`/`Weight Retry`/`Weight Error`.

Mode 3 runs both tasks in **one combined Claude message per row** (see `browser/prompt.py:build_prompt(row, tasks)`), not two separate exchanges — this keeps it just as fast as running either task alone. `TASKS` in `app.py` is the single source of truth mapping each task to its status/retry/error columns and its output column(s); add a new task there (plus a section in `prompt.py` and a case in `parser.py:extract_fields`) rather than hardcoding new columns elsewhere.

Per-row skip logic is per-task: a row is only skipped entirely if every task selected for *this run* already shows `COMPLETED` in its own status column (`app.py:remaining_tasks`). Running Highlights+Description today and Weight tomorrow on the same file never redoes finished work either way. `excel/writer.py:ensure_columns()` auto-adds any missing output columns to the copied output file at startup, so no manual Excel template setup is required when a new task is used for the first time.

**Resumable across interruptions.** Large files can take a very long time (multi-day) to fully process, so the run may need to stop and restart - power loss, closing the terminal, whatever. Every row's result is saved immediately (`ExcelWriter.write()` per row, not batched), and every save goes through `excel/writer.py:_atomic_save()` (write to a `.tmp` file, then `os.replace()`), so a save interrupted mid-write can't corrupt the output file - the on-disk file is always either the previous complete version or the new complete version, never partial. On startup, if `output/<name>_processed.xlsx` already exists, `app.py:choose_resume_or_restart()` asks whether to resume (skips rows already `COMPLETED` per the selected task(s), same as any other run) or start over (`shutil.copy2` from the original input, discarding prior progress). **Do not remove the `output.exists()` check before `shutil.copy2` in `main()`** - that check is the fix for what used to be a real bug: the app unconditionally re-copied the input over the output on every run, silently wiping out all progress from an interrupted previous run.

**File-lock resilience.** A real run hit `PermissionError: [WinError 32] The process cannot access the file because it is being used by another process` - Windows blocking a save because the output `.xlsx` was open in Excel (or locked by antivirus/OneDrive). For a job that can run for days, someone opening the file to check progress mid-run is expected, not exceptional - it must not crash the whole job and lose the row that was about to be saved. `excel/writer.py:wait_until_unlocked()` wraps every operation that can hit this (the atomic-save rename, and `shutil.copy2` in `app.py`): on `PermissionError` it prints which file to close and blocks on `input()` until the user presses Enter, then retries the same operation - no data lost, no restart needed. If a *new* file operation is added anywhere in this codebase, route it through `wait_until_unlocked()` too rather than calling the raw `os`/`shutil` function directly.

## The contract Claude's reply must satisfy

Defined in `browser/prompt.py:build_prompt()` (sections included depend on which tasks were requested) and enforced by `browser/parser.py:extract_fields()`:

```
HIGHLIGHTS_HTML
<ul><li>...</li></ul>

DESCRIPTION_HTML
<p>...</p><p>...</p>

WEIGHT_KG
<a single decimal number, e.g. 0.35>
```

- No preamble ("Here is the HTML...") — `parser.py` doesn't strip it, and if there's no preamble rule violation it usually means `prompt.py`'s "no preamble" rule needs to be stated more forcefully, or the parser's regex needs to tolerate it.
- Highlights must use `<ul>/<li>` only; description must use `<p>` only. Anything else fails `_extract_hd()` in `browser/parser.py`.
- Weight must be a plain decimal (or the literal word `unknown`) — no "kg" suffix, no other text. `_match_weight()` strips a `(kg)`/`kg` label if Claude adds one anyway, but the value itself should never contain unit text.
- Claude must not invent HTML facts not present in the row's `Highlights`/`Description`/`Product Name` columns. Weight, by contrast, is *meant* to be an estimate — `prompt.py`'s `WEIGHT_RULES` asks Claude to reason from product type/material/size/quantity rather than refuse.

## Failure modes and where to look

| Symptom | Likely cause | Fix location |
|---|---|---|
| Many rows in a long run fail with `no new Claude reply turn appeared` / `still generating`, even though the reply is visibly there when you check the chat manually. Failures cluster in the *later* rows of a run. | **Fixed — virtualization bug.** Claude.ai virtualizes the message list: once a conversation gets long, older `[role="article"]`/`div[data-is-streaming]` DOM nodes get unmounted. The old code counted those DOM nodes directly, so the raw count could stay flat (or drop) exactly when a new message arrived and an old one got unmounted at the same time - the agent falsely concluded nothing happened and burned the full `RESPONSE_TIMEOUT_MS` three times per row. Fixed by reading `aria-setsize` off any currently-rendered `[role="article"]` instead of counting nodes - it's the ARIA "feed" pattern's authored total message count, correct even when most of the conversation isn't mounted. | `browser/claude_agent.py` → `_total_messages()` |
| `Claude message input not found.` | Claude.ai changed its input DOM | `browser/claude_agent.py` → `_input()` selector list (`div[data-testid="chat-input"]` is the confirmed real one) |
| `Message was sent but the conversation's total message count never increased.` | `ARTICLE_SELECTOR` in `browser/claude_agent.py` doesn't match anything on the real page (Claude.ai changed its DOM again) | `browser/claude_agent.py` |
| `A new message appeared but no Claude reply turn showed up under it before the timeout.` | The user's message was confirmed sent (total count increased) but Claude's reply turn (`.font-claude-response`) hasn't rendered under the newest article yet | usually resolves on its own before the deadline; if it never does, `RESPONSE_SELECTOR`/`TURN_SELECTOR` may need updating |
| `Claude was still generating a reply when the timeout was reached.` | Response genuinely took longer than `RESPONSE_TIMEOUT_MS` (e.g. a "High" reasoning-effort model thinking longer, or a long product description) | `config.py`/`.env` → raise `RESPONSE_TIMEOUT_MS` |
| `Message was not accepted by Claude's composer after 3 attempts...` | The click/Enter didn't actually submit the message (composer still had the text). Previously this manifested as a silent 2-minute `TimeoutError` per row since the code waited the full `RESPONSE_TIMEOUT_MS` for a reply to a message that was never sent - fixed by confirming delivery via the same `aria-setsize` total-message check within ~8s and retrying the send instead of waiting it out | `browser/claude_agent.py` → `_submit()` |
| Output columns are filled with the literal prompt template (e.g. `Highlights HTML` = `<ul>\n<li>...</li>\n</ul>`, `Description HTML` ends with the `Rules:` block) marked `COMPLETED` | **Fixed — was the root cause of "doesn't wait after input".** The assistant-selector guesses matched nothing, so the old code fell back to `page.locator("body").inner_text()`. Since the prompt template itself contains the literal words `HIGHLIGHTS_HTML`/`DESCRIPTION_HTML`, the agent's own just-submitted (echoed) message satisfied the "response arrived" check instantly, before Claude ever replied. Fixed by confirming the real DOM against a live conversation (see below) and switching to `data-is-streaming="false"` for completion detection — never falls back to whole-page text. | `browser/claude_agent.py` |
| Description HTML column has a trailing sentence after the last `</p>` (e.g. "Note: I dropped X since...") | Claude appended an explanatory note after the code block, which `_match_hd_headings()` used to capture along with everything else to end-of-text | `browser/parser.py` → `_trim_after_last_closing_tag()` now truncates at the last `</ul>`/`</p>`; fixed |
| `Could not identify both HTML sections.` / `Invalid highlights HTML.` / `Invalid description HTML.` | Claude added conversational text, used markdown instead of raw HTML, or used the wrong tags | `browser/prompt.py` (tighten instructions) and/or `browser/parser.py:_extract_hd()` (loosen regex) |
| `Could not identify a weight value.` | Claude didn't produce a recognizable `WEIGHT_KG` marker or a `Weight`/`Weight (kg)` heading with a number after it | `browser/parser.py:_match_weight()` — paste the actual reply text and I'll extend the pattern |
| Output quality is bad (invented specs, wrong tone, missing facts, or a wildly wrong weight estimate) | Prompt wording, not code | `browser/prompt.py` — describe the bad example row and what you wanted instead |
| Rows silently marked `FAILED` after 3 tries | Real error captured in the `Error` column of the output Excel — read that first | `config.py` `MAX_RETRIES` / `RESPONSE_TIMEOUT_MS` if it's just timing |
| A row shows `COMPLETED` but you want to know if it needed a retry | `Error` column on a `COMPLETED` row now carries a note like `attempt 1 failed: ...` if earlier attempts failed before it eventually succeeded, instead of being silently wiped blank | `app.py` (`prior_errors` tracking) |
| Wrong/missing input columns | Excel doesn't have `Product Name` / `Highlights` / `Description` headers | `excel/reader.py` (column lookup is by header name, row 1) |

## What to paste back into the chat when asking for a fix

1. The exact error message or the row's `Error` column value.
2. If it's a selector problem: the relevant `view-source:` HTML snippet around the chat input box or the assistant message container (Claude's DOM does change between releases — this project's selectors were written from general patterns, not a live inspection, so they may need one round of correction against the real page).
3. If it's an output-quality problem: one example row (`Product Name` / `Highlights` / `Description` in, vs. what Claude returned) and what's wrong with it.

## Confirmed selectors (verified against a live claude.ai DOM dump)

- Input box: `div[data-testid="chat-input"]` (a `contenteditable` div with class `tiptap ProseMirror`).
- Every message (user or assistant): `[role="article"]`, each carrying `aria-setsize` (total conversation length) and `aria-posinset` (its own position) - part of the standard ARIA "feed" pattern for virtualized lists. **Use `aria-setsize`, not DOM node counts**, to detect whether a new message has arrived - node counts are unreliable once the conversation is long enough that claude.ai virtualizes (unmounts) older messages.
- Each reply turn: `div[data-is-streaming="..."]` (nested inside the article) — `"true"` while Claude is still generating, `"false"` once done. This is the authoritative completion signal `browser/claude_agent.py` waits on, instead of guessing from text stability.
- The reply body itself: `.font-claude-response` (nested inside the turn div above). **Not** `.font-claude-message` — that was the original wrong guess and the actual root cause of the very first "doesn't wait" bug: the guessed class matched nothing, so the old code fell back to whole-page text and grabbed the echoed prompt instead.
- Claude often formats the reply as a bold **Highlights**/**Description** heading followed by a rendered code block, rather than obeying the literal `HIGHLIGHTS_HTML`/`DESCRIPTION_HTML` tokens from the prompt. `browser/parser.py` handles both shapes.
- Send button: `button[aria-label="Send message"]` (only appears once the composer has text — an empty composer shows a voice/mic button instead). Confirmed against a live DOM dump captured with text typed into the box.

All selectors in `browser/claude_agent.py` are now confirmed against real DOM dumps, not guesses. If the automation still misbehaves after a Claude.ai UI update, the fix is the same process: type into the composer, right-click the input/send button/a reply → Inspect → copy `outerHTML`, and update the relevant selector.
