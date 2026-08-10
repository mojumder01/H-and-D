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

    def process(self,row):
        before=self._turn_count()
        prompt=build_prompt(row)
        box=self._input()
        box.click()
        try: box.fill(prompt)
        except: self.page.keyboard.insert_text(prompt)
        if not self._send():
            box.press("Enter")

        from config import RESPONSE_TIMEOUT_MS
        deadline=time.time()+RESPONSE_TIMEOUT_MS/1000
        saw_new_turn=False
        while time.time()<deadline:
            time.sleep(1)
            after=self._turn_count()
            if after<=before:
                continue
            saw_new_turn=True
            turn=self._turn(after-1)
            if turn.get_attribute("data-is-streaming")!="false":
                continue  # still generating, keep waiting
            text=turn.locator(RESPONSE_SELECTOR).inner_text(timeout=3000)
            return extract_sections(text)
        if not saw_new_turn:
            raise TimeoutError(
                "No new Claude reply detected on the page. TURN_SELECTOR/"
                "RESPONSE_SELECTOR in browser/claude_agent.py likely don't "
                "match Claude.ai's current DOM - see AGENT_BRIEF.md."
            )
        raise TimeoutError("Timed out waiting for Claude response.")
