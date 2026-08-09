import time
from browser.prompt import build_prompt
from browser.parser import extract_sections

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

    def _assistant_text(self):
        for s in ['.font-claude-message','[data-testid="chat-message"]','article']:
            loc=self.page.locator(s)
            try:
                if loc.count():
                    t=loc.last.inner_text(timeout=3000)
                    if t.strip(): return t
            except: pass
        return self.page.locator("body").inner_text()

    def process(self,row):
        old=self._assistant_text()
        prompt=build_prompt(row)
        box=self._input()
        box.click()
        try: box.fill(prompt)
        except: self.page.keyboard.insert_text(prompt)
        if not self._send():
            box.press("Enter")

        from config import RESPONSE_TIMEOUT_MS
        deadline=time.time()+RESPONSE_TIMEOUT_MS/1000
        while time.time()<deadline:
            time.sleep(1)
            text=self._assistant_text()
            if text.strip()!=old.strip() and "HIGHLIGHTS_HTML" in text and "DESCRIPTION_HTML" in text:
                time.sleep(2)
                return extract_sections(self._assistant_text())
        raise TimeoutError("Timed out waiting for Claude response.")
