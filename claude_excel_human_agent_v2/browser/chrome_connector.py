from playwright.sync_api import sync_playwright
from config import DEBUG_PORT
from browser.claude_agent import ClaudeAgent

class ChromeConnector:
    def __init__(self):
        self.pw=sync_playwright().start()
        try:
            self.browser=self.pw.chromium.connect_over_cdp(f"http://127.0.0.1:{DEBUG_PORT}")
        except Exception as e:
            self.pw.stop()
            raise RuntimeError(
                "Could not connect to Chrome on port 9222. "
                "Run start_chrome.bat first, log in to Claude, and keep Chrome open."
            ) from e

    def open_conversation(self,url):
        contexts=self.browser.contexts
        if not contexts:
            raise RuntimeError("No Chrome browser context found.")
        context=contexts[0]
        pages=context.pages
        page=pages[0] if pages else context.new_page()
        page.goto(url,wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        return ClaudeAgent(page)

    def close(self):
        try:
            self.browser.close()
        finally:
            self.pw.stop()
