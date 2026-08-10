import time
from browser.prompt import build_prompt
from browser.parser import extract_sections

ASSISTANT_SELECTORS=[
    '.font-claude-message',
    '[data-testid="chat-message"]',
]

class ClaudeAgent:
    def __init__(self,page):
        self.page=page

    def _input(self):
        selectors=[
            'div[contenteditable="true"].ProseMirror',
            'div[contenteditable="true"]',
            'textarea[placeholder*="Reply"]',
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
        selectors=[
            'button[aria-label="Send Message"]',
            'button[aria-label="Send message"]',
        ]
        for s in selectors:
            loc=self.page.locator(s)
            try:
                if loc.count() and loc.last.is_visible() and loc.last.is_enabled():
                    loc.last.click()
                    return True
            except: pass
        return False

    def _assistant_locator(self):
        # Only matches selectors known to wrap Claude's OWN reply. No whole-page
        # fallback here on purpose: falling back to body text previously caused
        # the agent to read back the user's own just-submitted prompt (which
        # literally contains the words HIGHLIGHTS_HTML/DESCRIPTION_HTML) as if
        # it were Claude's answer, without ever waiting for a real response.
        for s in ASSISTANT_SELECTORS:
            loc=self.page.locator(s)
            try:
                if loc.count(): return loc
            except: pass
        return None

    def _assistant_count(self):
        loc=self._assistant_locator()
        return loc.count() if loc else 0

    def _assistant_text_at(self,index):
        loc=self._assistant_locator()
        if loc is None: raise RuntimeError("No Claude assistant message elements found on page.")
        return loc.nth(index).inner_text(timeout=3000)

    def process(self,row):
        before=self._assistant_count()
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
        stable_text=None
        while time.time()<deadline:
            time.sleep(1)
            after=self._assistant_count()
            if after<=before:
                continue
            saw_new_turn=True
            text=self._assistant_text_at(after-1)
            if "HIGHLIGHTS_HTML" not in text or "DESCRIPTION_HTML" not in text:
                stable_text=None
                continue
            # require the text to stop changing for a beat before trusting it,
            # so we don't cut off a still-streaming reply mid-generation.
            if text==stable_text:
                return extract_sections(text)
            stable_text=text
        if not saw_new_turn:
            raise TimeoutError(
                "No new Claude reply detected on the page. The selectors in "
                "ASSISTANT_SELECTORS (browser/claude_agent.py) likely don't "
                "match Claude.ai's current DOM - see AGENT_BRIEF.md."
            )
        raise TimeoutError("Timed out waiting for Claude response.")
