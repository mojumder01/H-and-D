import time
from browser.prompt import build_prompt
from browser.parser import extract_fields

# Confirmed against a live claude.ai DOM dump:
#   <div role="feed" aria-label="Chat messages" ...>
#     <div role="article" aria-setsize="4" aria-posinset="1" aria-label="Message 1 of 4">...</div>
#     <div role="article" aria-setsize="4" aria-posinset="2" aria-label="Message 2 of 4">
#       <div data-is-streaming="false" class="group relative ...">
#         <h2 class="sr-only">Claude responded: ...</h2>
#         <div class="font-claude-response ...">...actual reply markup...</div>
#       </div>
#     </div>
#     ...
#   </div>
#
# IMPORTANT: claude.ai virtualizes this list once the conversation gets long -
# older [role="article"]/div[data-is-streaming] nodes get unmounted from the
# DOM to save memory. Counting those nodes directly (an earlier version of
# this file did) is unreliable: the raw DOM count can stay flat or even drop
# as a new message arrives if an old one gets unmounted at the same time,
# causing the agent to falsely conclude "nothing new happened" and burn the
# full RESPONSE_TIMEOUT_MS waiting for a reply that had already arrived.
#
# aria-setsize is the fix: it's the ARIA "feed" pattern's declared TOTAL
# message count, authored from the app's real conversation state - it stays
# correct even when most of the conversation isn't mounted in the DOM. Any
# currently-rendered article (e.g. the last one) reports the true total.
ARTICLE_SELECTOR='[role="article"]'
TURN_SELECTOR='div[data-is-streaming]'
RESPONSE_SELECTOR='.font-claude-response'
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

    def _total_messages(self):
        # None means "couldn't tell" (e.g. no articles rendered yet), treated
        # as 0 by callers - never treated as "definitely no new message".
        loc=self.page.locator(ARTICLE_SELECTOR)
        try:
            if loc.count()==0: return None
            v=loc.last.get_attribute("aria-setsize")
            return int(v) if v else None
        except: return None

    def _last_article(self):
        return self.page.locator(ARTICLE_SELECTOR).last

    def _submit(self,box,prompt):
        before=self._total_messages() or 0
        box.click()
        try: box.fill(prompt)
        except: self.page.keyboard.insert_text(prompt)

        for attempt in range(1,SEND_ATTEMPTS+1):
            if not self._send():
                box.press("Enter")
            deadline=time.time()+SEND_CONFIRM_TIMEOUT_S
            while time.time()<deadline:
                if (self._total_messages() or 0)>before:
                    return  # delivery confirmed - a new message appeared
                time.sleep(0.5)
            # not delivered within the confirm window - the text is likely
            # still sitting unsent in the box; re-focus and try sending again
            # instead of waiting the full RESPONSE_TIMEOUT_MS for nothing.
            box.click()
        raise RuntimeError(
            f"Message was not accepted by Claude's composer after "
            f"{SEND_ATTEMPTS} attempts (click/Enter did not submit it)."
        )

    def process(self,row,tasks):
        before=self._total_messages() or 0
        prompt=build_prompt(row,tasks)
        box=self._input()
        self._submit(box,prompt)

        from config import RESPONSE_TIMEOUT_MS
        deadline=time.time()+RESPONSE_TIMEOUT_MS/1000
        saw_new_message=False
        saw_assistant_turn=False
        while time.time()<deadline:
            time.sleep(1)
            after=self._total_messages() or 0
            if after<=before:
                continue
            saw_new_message=True
            article=self._last_article()
            response=article.locator(RESPONSE_SELECTOR)
            if response.count()==0:
                continue  # the newest message so far is still just the echoed user turn
            saw_assistant_turn=True
            turn=article.locator(TURN_SELECTOR)
            if turn.count()==0 or turn.first.get_attribute("data-is-streaming")!="false":
                continue  # still generating, keep waiting
            text=response.inner_text(timeout=3000)
            return extract_fields(text,tasks)
        if not saw_new_message:
            raise TimeoutError(
                "Message was sent but the conversation's total message count "
                "never increased. ARTICLE_SELECTOR in browser/claude_agent.py "
                "likely doesn't match Claude.ai's current DOM - see AGENT_BRIEF.md."
            )
        if not saw_assistant_turn:
            raise TimeoutError(
                "A new message appeared but no Claude reply turn showed up "
                "under it before the timeout."
            )
        raise TimeoutError(
            "Claude was still generating a reply when the timeout was "
            "reached. Increase RESPONSE_TIMEOUT_MS in .env if this product "
            "routinely needs a long response."
        )
