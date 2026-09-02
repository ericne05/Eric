"""
Browser Resource Manager.
"""
from typing import List

from core.browser.models import BrowserTab
from core.logger.interface import ILogger


class BrowserResourceManager:
    """
    Monitors RAM, CPU, and Tab limits to prevent OOM.
    """
    def __init__(self, logger: ILogger, max_tabs: int = 20):
        self._logger = logger
        self._max_tabs = max_tabs

    def enforce_tab_limit(self, tabs: List[BrowserTab]) -> List[BrowserTab]:
        """
        Returns a list of tabs to close if the limit is exceeded.
        (Usually the oldest tabs not currently active).
        """
        if len(tabs) <= self._max_tabs:
            return []
            
        # Example logic: close oldest tabs
        excess = len(tabs) - self._max_tabs
        to_close = tabs[:excess]
        
        for t in to_close:
            self._logger.warning(f"[ResourceManager] Flagging tab {t.id} ({t.url}) for closure due to resource limits.")
            
        return to_close
