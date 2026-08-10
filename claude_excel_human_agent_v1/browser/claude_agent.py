import time
from browser.prompt import build_prompt
from browser.parser import extract_sections

# Confirmed against a live claude.ai DOM dump:
#   <div data-is-streaming="false" class="group relative ...">
#       <h2 class="sr-only">Claude responded: ...</h2>
#       <div class="font-claude-response ...">...actual reply markup...</div>
#   </div>
# data-is-streaming flips to "false" once generation is complete, and
# .font-claude-response wraps only Claude's own reply body (never the user's
# message, never the sr-only summary heading).
TURN_SELECTOR='div[data-is-streaming]'
RESPONSE_SELECTOR='.font-claude-response'
# Wraps only the user's own submitted message bubble - confirmed in the same
# DOM dump. Used to confirm a send actually registered, fast, instead of
# waiting the full RESPONSE_TIMEOUT_MS for a reply that will never come
# because the click/Enter silently didn't submit anything.
USER_MESSAGE_SELECTOR='[data-testid="user-message"]'
SEND_CONFIRM_TIMEOUT_S=8
SEND_ATTEMPTS=3

class ClaudeAgent:
    def __init__(self,page):
        self.page=page

    def _input(self):
        selectors=[
            'div[data-testid="chat-input"]',
            'div[contenteditable="true"].ProseMirror',
            'div[contenteditable="true"]',
            'textarea',
        ]
        for s in selectors:
            loc=self.page.locator(s)
            try:
                if loc.count() and loc.last.is_visible():
                    return loc.last
            except: pass
        raise RuntimeError("Claude message input not found.")

    def _send(self):
        # Confirmed against a live claude.ai DOM dump (composer populated
        # with text): <button aria-label="Send message" ...>.
        selectors=[
            'button[aria-label="Send message"]',
            'button[aria-label="Send Message"]',
        ]
        for s in selectors:
            loc=self.page.locator(s)
            try:
                if loc.count() and loc.last.is_visible() and loc.last.is_enabled():
                    loc.last.click()
                    return True
            except: pass
        return False

    def _turn_count(self):
        try: return self.page.locator(TURN_SELECTOR).count()
        except: return 0

    def _turn(self,index):
        return self.page.locator(TURN_SELECTOR).nth(index)

    def _user_message_count(self):
        try: return self.page.locator(USER_MESSAGE_SELECTOR).count()
        except: return 0

    def _submit(self,box,prompt):
        before=self._user_message_count()
        box.click()
        try: box.fill(prompt)
        except: self.page.keyboard.insert_text(prompt)

        for attempt in range(1,SEND_ATTEMPTS+1):
            if not self._send():
                box.press("Enter")
            deadline=time.time()+SEND_CONFIRM_TIMEOUT_S
            while time.time()<deadline:
                if self._user_message_count()>before:
                    return  # delivery confirmed - the message bubble appeared
                time.sleep(0.5)
            # not delivered within the confirm window - the text is likely
            # still sitting unsent in the box; re-focus and try sending again
            # instead of waiting the full RESPONSE_TIMEOUT_MS for nothing.
            box.click()
        raise RuntimeError(
            f"Message was not accepted by Claude's composer after "
            f"{SEND_ATTEMPTS} attempts (click/Enter did not submit it)."
        )

    def process(self,row):
        before=self._turn_count()
        prompt=build_prompt(row)
        box=self._input()
        self._submit(box,prompt)

        from config import RESPONSE_TIMEOUT_MS
        deadline=time.time()+RESPONSE_TIMEOUT_MS/1000
        saw_new_turn=False
        was_streaming=False
        while time.time()<deadline:
            time.sleep(1)
            after=self._turn_count()
            if after<=before:
                continue
            saw_new_turn=True
            turn=self._turn(after-1)
            if turn.get_attribute("data-is-streaming")!="false":
                was_streaming=True
                continue  # still generating, keep waiting
            text=turn.locator(RESPONSE_SELECTOR).inner_text(timeout=3000)
            return extract_sections(text)
        if not saw_new_turn:
            raise TimeoutError(
                "Message was sent but no new Claude reply turn appeared on "
                "the page within the timeout. TURN_SELECTOR/RESPONSE_SELECTOR "
                "in browser/claude_agent.py likely don't match Claude.ai's "
                "current DOM - see AGENT_BRIEF.md."
            )
        if was_streaming:
            raise TimeoutError(
                "Claude was still generating a reply when the timeout was "
                "reached. Increase RESPONSE_TIMEOUT_MS in .env if this "
                "product routinely needs a long response."
            )
        raise TimeoutError("Timed out waiting for Claude response.")
