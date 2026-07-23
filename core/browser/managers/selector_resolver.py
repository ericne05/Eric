"""
Selector Resolver.
"""
from typing import List

from core.browser.enums import SelectorType
from core.browser.models import BrowserSelector
from core.logger.interface import ILogger


class SelectorResolver:
    """
    Resolves higher-level intent into the best possible Playwright selector.
    Fallback chain: ROLE -> TEXT -> CSS -> XPATH -> AI_FALLBACK
    """
    def __init__(self, logger: ILogger):
        self._logger = logger
        
    def generate_fallbacks(self, intent_text: str) -> List[BrowserSelector]:
        """
        Given an intent like 'login button', generates a chain of selectors to try.
        """
        # A real implementation would parse intent_text (e.g. using an LLM or regex)
        # Here we demonstrate the fallback chain structure.
        fallbacks = []
        
        # 1. Try Role first (Most semantic)
        fallbacks.append(BrowserSelector(type=SelectorType.ROLE, value="button", options={"name": intent_text}))
        
        # 2. Try Exact Text
        fallbacks.append(BrowserSelector(type=SelectorType.TEXT, value=intent_text))
        
        # 3. Try CSS (rough guess)
        fallbacks.append(BrowserSelector(type=SelectorType.CSS, value=f"[aria-label*='{intent_text}' i]"))
        
        # 4. Try XPath (rough guess)
        fallbacks.append(BrowserSelector(type=SelectorType.XPATH, value=f"//*[contains(text(), '{intent_text}')]"))
        
        # 5. AI Fallback indicator (If everything else fails, the Runtime will trigger Screenshot Vision)
        fallbacks.append(BrowserSelector(type=SelectorType.AI_FALLBACK, value=intent_text))
        
        return fallbacks
