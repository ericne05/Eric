import pytest
import asyncio
from core.browser.models import BrowserAction, BrowserTab
from core.browser.managers.action_queue import BrowserActionQueue
from core.browser.managers.resource import BrowserResourceManager
from core.browser.managers.selector_resolver import SelectorResolver

class MockLogger:
    def info(self, msg): pass
    def debug(self, msg): pass
    def warning(self, msg): pass
    def error(self, msg): pass
    def exception(self, msg): pass

@pytest.mark.asyncio
async def test_action_queue():
    logger = MockLogger()
    queue = BrowserActionQueue(logger)
    
    # Mock executor that succeeds on 2nd try
    execution_count = 0
    
    from core.browser.models import BrowserActionResult
    
    async def mock_executor(**kwargs):
        nonlocal execution_count
        execution_count += 1
        if execution_count == 1:
            raise Exception("Fail first time")
        return BrowserActionResult(success=True)
        
    action = BrowserAction(name="test_click", max_retries=3)
    await queue.enqueue(action, mock_executor)
    
    result = await queue.process_next()
    
    assert result.success is True
    assert execution_count == 2
    assert action.retry_count == 1
    
def test_resource_manager():
    logger = MockLogger()
    rm = BrowserResourceManager(logger, max_tabs=2)
    
    tabs = [
        BrowserTab(id="1"),
        BrowserTab(id="2"),
        BrowserTab(id="3"),
    ]
    
    to_close = rm.enforce_tab_limit(tabs)
    assert len(to_close) == 1
    assert to_close[0].id == "1"

def test_selector_resolver():
    logger = MockLogger()
    sr = SelectorResolver(logger)
    
    fallbacks = sr.generate_fallbacks("Login")
    assert len(fallbacks) == 5
    assert fallbacks[0].type == "role"
    assert fallbacks[1].type == "text"
    assert fallbacks[-1].type == "ai_fallback"
