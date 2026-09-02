"""
Navigation Manager.
"""
from core.browser.models import BrowserActionResult
from core.logger.interface import ILogger


class NavigationManager:
    """
    Manages navigation strategies like waiting for network idle or domcontentloaded.
    """
    def __init__(self, logger: ILogger):
        self._logger = logger

    def build_navigation_options(self, wait_strategy: str = "load", timeout_ms: int = 30000) -> dict:
        """
        Translates a high-level wait strategy into Playwright options.
        Strategies: 'load', 'domcontentloaded', 'networkidle', 'commit'
        """
        return {
            "timeout": timeout_ms,
            "wait_until": wait_strategy
        }
