"""
Browser Runtime Interfaces.
"""

from abc import ABC, abstractmethod
from typing import List, Optional

from core.browser.enums import BrowserPermissions
from core.browser.models import (
    BrowserAction,
    BrowserActionResult,
    BrowserContextState,
    BrowserSelector,
    BrowserSession,
    BrowserTab,
)


class IBrowserDOM(ABC):
    """Interface for DOM interactions."""
    @abstractmethod
    async def click(self, selector: BrowserSelector, timeout_ms: int = 10000) -> BrowserActionResult:
        pass

    @abstractmethod
    async def type_text(self, selector: BrowserSelector, text: str, timeout_ms: int = 10000) -> BrowserActionResult:
        pass

    @abstractmethod
    async def hover(self, selector: BrowserSelector, timeout_ms: int = 10000) -> BrowserActionResult:
        pass

    @abstractmethod
    async def scroll(self, direction: str, distance: int = 500) -> BrowserActionResult:
        pass

    @abstractmethod
    async def extract_text(self) -> BrowserActionResult:
        """Extracts cleaned text from the page."""
        pass

    @abstractmethod
    async def get_html(self) -> BrowserActionResult:
        pass


class IBrowserScreenshot(ABC):
    """Interface for taking screenshots."""
    @abstractmethod
    async def capture_page(self) -> BrowserActionResult:
        pass
        
    @abstractmethod
    async def capture_element(self, selector: BrowserSelector) -> BrowserActionResult:
        pass

    @abstractmethod
    async def capture_fullpage(self) -> BrowserActionResult:
        pass


class IDownloadManager(ABC):
    """Interface for managing downloads."""
    @abstractmethod
    async def get_all_downloads(self) -> List[Any]:
        pass





class ISessionManager(ABC):
    """Interface for managing browser tabs and contexts."""
    @abstractmethod
    async def create_tab(self, url: str = "about:blank") -> BrowserTab:
        pass

    @abstractmethod
    async def switch_tab(self, tab_id: str) -> bool:
        pass

    @abstractmethod
    async def close_tab(self, tab_id: str) -> bool:
        pass

    @abstractmethod
    def get_current_session(self) -> BrowserSession:
        pass

    @abstractmethod
    def get_context_state(self) -> BrowserContextState:
        pass


class IBrowserRuntime(ABC):
    """Main interface for controlling the browser lifecycle."""
    @abstractmethod
    async def start(self) -> None:
        pass

    @abstractmethod
    async def stop(self) -> None:
        pass

    @property
    @abstractmethod
    def session_manager(self) -> ISessionManager:
        pass

    @property
    @abstractmethod
    def dom(self) -> IBrowserDOM:
        pass

    @property
    @abstractmethod
    def screenshot(self) -> IBrowserScreenshot:
        pass
