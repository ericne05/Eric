import pytest
import asyncio

from core.browser.adapters.playwright_adapter import PlaywrightAdapter
from core.browser.models import BrowserSelector, SelectorType

class MockLogger:
    def info(self, msg): pass
    def debug(self, msg): pass
    def warning(self, msg): pass
    def error(self, msg): pass
    def exception(self, msg): pass


@pytest.mark.asyncio
async def test_playwright_adapter():
    logger = MockLogger()
    adapter = PlaywrightAdapter(logger)
    
    # Start runtime
    await adapter.start()
    
    # Create Tab
    tab = await adapter.session_manager.create_tab("https://example.com")
    assert tab is not None
    assert "example.com" in tab.url
    
    # Extract Text
    res = await adapter.dom.extract_text()
    assert res.success is True
    assert "Example Domain" in res.data
    
    # Stop runtime
    await adapter.stop()
