"""
Playwright Adapter for Browser Runtime.
"""
from typing import Optional, List
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

from core.browser.interfaces import IBrowserRuntime, ISessionManager, IBrowserDOM, IBrowserScreenshot, IDownloadManager
from core.browser.models import BrowserTab, BrowserSession, BrowserContextState, BrowserActionResult, BrowserSelector
from core.logger.interface import ILogger


class PlaywrightSessionManager(ISessionManager):
    def __init__(self, browser: Browser, logger: ILogger):
        self._browser = browser
        self._logger = logger
        self._context: Optional[BrowserContext] = None
        self._session = BrowserSession()
        self._playwright_pages = {} # tab_id -> Page
        
    async def initialize(self):
        self._context = await self._browser.new_context()
        self._session.context = BrowserContextState()
        
    async def create_tab(self, url: str = "about:blank") -> BrowserTab:
        page = await self._context.new_page()
        await page.goto(url)
        
        tab = BrowserTab(url=url, title=await page.title())
        self._session.tabs.append(tab)
        self._session.current_tab_id = tab.id
        self._playwright_pages[tab.id] = page
        
        return tab

    async def switch_tab(self, tab_id: str) -> bool:
        if tab_id in self._playwright_pages:
            await self._playwright_pages[tab_id].bring_to_front()
            self._session.current_tab_id = tab_id
            return True
        return False

    async def close_tab(self, tab_id: str) -> bool:
        if tab_id in self._playwright_pages:
            await self._playwright_pages[tab_id].close()
            del self._playwright_pages[tab_id]
            self._session.tabs = [t for t in self._session.tabs if t.id != tab_id]
            if self._session.current_tab_id == tab_id:
                self._session.current_tab_id = self._session.tabs[-1].id if self._session.tabs else None
            return True
        return False

    def get_current_session(self) -> BrowserSession:
        return self._session

    def get_context_state(self) -> BrowserContextState:
        return self._session.context
        
    def get_active_page(self) -> Optional[Page]:
        if self._session.current_tab_id and self._session.current_tab_id in self._playwright_pages:
            return self._playwright_pages[self._session.current_tab_id]
        return None


class PlaywrightDOM(IBrowserDOM):
    def __init__(self, session_manager: PlaywrightSessionManager, logger: ILogger):
        self._sm = session_manager
        self._logger = logger
        
    async def click(self, selector: BrowserSelector, timeout_ms: int = 10000) -> BrowserActionResult:
        page = self._sm.get_active_page()
        if not page:
            return BrowserActionResult(success=False, error="No active page")
            
        try:
            # Simplistic resolution for now
            if selector.type == "css":
                await page.locator(selector.value).click(timeout=timeout_ms)
            else:
                await page.click(selector.value, timeout=timeout_ms)
            return BrowserActionResult(success=True)
        except Exception as e:
            return BrowserActionResult(success=False, error=str(e))

    async def type_text(self, selector: BrowserSelector, text: str, timeout_ms: int = 10000) -> BrowserActionResult:
        page = self._sm.get_active_page()
        if not page:
            return BrowserActionResult(success=False, error="No active page")
            
        try:
            if selector.type == "css":
                await page.locator(selector.value).fill(text, timeout=timeout_ms)
            else:
                await page.fill(selector.value, text, timeout=timeout_ms)
            return BrowserActionResult(success=True)
        except Exception as e:
            return BrowserActionResult(success=False, error=str(e))

    async def hover(self, selector: BrowserSelector, timeout_ms: int = 10000) -> BrowserActionResult:
        return BrowserActionResult(success=False, error="Not implemented")

    async def scroll(self, direction: str, distance: int = 500) -> BrowserActionResult:
        return BrowserActionResult(success=False, error="Not implemented")

    async def extract_text(self) -> BrowserActionResult:
        page = self._sm.get_active_page()
        if not page:
            return BrowserActionResult(success=False, error="No active page")
        try:
            text = await page.evaluate("document.body.innerText")
            return BrowserActionResult(success=True, data=text)
        except Exception as e:
            return BrowserActionResult(success=False, error=str(e))

    async def get_html(self) -> BrowserActionResult:
        page = self._sm.get_active_page()
        if not page:
            return BrowserActionResult(success=False, error="No active page")
        try:
            html = await page.content()
            return BrowserActionResult(success=True, data=html)
        except Exception as e:
            return BrowserActionResult(success=False, error=str(e))


class PlaywrightScreenshot(IBrowserScreenshot):
    def __init__(self, session_manager: PlaywrightSessionManager, logger: ILogger):
        self._sm = session_manager
        self._logger = logger
        
    async def capture_page(self) -> BrowserActionResult:
        return BrowserActionResult(success=False, error="Not implemented")
        
    async def capture_element(self, selector: BrowserSelector) -> BrowserActionResult:
        return BrowserActionResult(success=False, error="Not implemented")

    async def capture_fullpage(self) -> BrowserActionResult:
        page = self._sm.get_active_page()
        if not page:
            return BrowserActionResult(success=False, error="No active page")
            
        try:
            import base64
            screenshot_bytes = await page.screenshot(full_page=True)
            b64 = base64.b64encode(screenshot_bytes).decode('utf-8')
            return BrowserActionResult(success=True, screenshot_base64=b64)
        except Exception as e:
            return BrowserActionResult(success=False, error=str(e))


class PlaywrightAdapter(IBrowserRuntime):
    """
    Playwright adapter implementing the main Browser Runtime.
    """
    def __init__(self, logger: ILogger):
        self._logger = logger
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._sm: Optional[PlaywrightSessionManager] = None
        self._dom: Optional[PlaywrightDOM] = None
        self._screenshot: Optional[PlaywrightScreenshot] = None
        
    async def start(self) -> None:
        if self._playwright:
            return
            
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=True)
        
        self._sm = PlaywrightSessionManager(self._browser, self._logger)
        await self._sm.initialize()
        
        self._dom = PlaywrightDOM(self._sm, self._logger)
        self._screenshot = PlaywrightScreenshot(self._sm, self._logger)
        
        self._logger.info("[PlaywrightAdapter] Browser runtime started successfully.")

    async def stop(self) -> None:
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        self._logger.info("[PlaywrightAdapter] Browser runtime stopped.")

    @property
    def session_manager(self) -> ISessionManager:
        return self._sm

    @property
    def dom(self) -> IBrowserDOM:
        return self._dom

    @property
    def screenshot(self) -> IBrowserScreenshot:
        return self._screenshot
