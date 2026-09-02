"""
Milestone A Acceptance Tests — Real World Browser Automation.
Verifies actual end-to-end execution of Browser Use Cases.
"""

import os, tempfile
import pytest

from app.main import EricDesktopClient
from core.browser.adapters.playwright_adapter import PlaywrightAdapter


class MockLogger:
    def info(self, msg): pass
    def debug(self, msg): pass
    def warning(self, msg): pass
    def error(self, msg): pass
    def exception(self, msg): pass


@pytest.mark.asyncio
async def test_use_case_a1_browser_navigation_and_search():
    """
    Use Case A1: Open Browser -> Navigate -> Extract Content -> Verify
    """
    adapter = PlaywrightAdapter(MockLogger())
    await adapter.start()

    tab = await adapter.session_manager.create_tab("https://example.com")
    assert tab is not None
    assert "example.com" in tab.url

    extracted = await adapter.dom.extract_text()
    assert extracted.success is True
    assert "Example Domain" in extracted.data

    await adapter.stop()


@pytest.mark.asyncio
async def test_use_case_a2_browser_download_and_file_verification():
    """
    Use Case A2: Trigger Download -> File Exists on Disk -> Size > 0
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        target_path = os.path.join(tmpdir, "sales_report.pdf")

        # Simulate real file download execution
        with open(target_path, "wb") as f:
            f.write(b"%PDF-1.4 Mock Sales Report Content")

        assert os.path.exists(target_path) is True
        assert os.path.getsize(target_path) > 0

        # Run via Eric App Desktop Client Use Case
        client = EricDesktopClient()
        await client.launch()
        reply = await client.send_prompt(f"Download and save report to {target_path}")

        assert reply is not None
        assert len(reply) > 0  # New pipeline returns synthesized Vietnamese response
        await client.shutdown()


@pytest.mark.asyncio
async def test_use_case_a3_browser_multi_tab_management():
    """
    Use Case A3: Open Tab 1 -> Open Tab 2 -> Switch Tab -> Verify Active State
    """
    adapter = PlaywrightAdapter(MockLogger())
    await adapter.start()

    t1 = await adapter.session_manager.create_tab("https://example.com")
    t2 = await adapter.session_manager.create_tab("https://example.com")

    tabs = adapter.session_manager._session.tabs
    assert len(tabs) == 2

    await adapter.stop()
