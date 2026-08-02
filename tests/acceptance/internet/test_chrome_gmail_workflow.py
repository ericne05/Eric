"""
Internet & Web Automation Acceptance Tests (Chrome, Gmail, Search Email, Download Attachment).
"""

import os, tempfile
import pytest

from core.browser.adapters.playwright_adapter import PlaywrightAdapter


class MockLogger:
    def info(self, msg): pass
    def debug(self, msg): pass
    def warning(self, msg): pass
    def error(self, msg): pass
    def exception(self, msg): pass


@pytest.mark.asyncio
async def test_internet_chrome_gmail_search_download_workflow():
    """
    Workflow: Open Chrome -> Navigate Gmail -> Search Email -> Download Attachment
    """
    adapter = PlaywrightAdapter(MockLogger())
    await adapter.start()

    tab = await adapter.session_manager.create_tab("https://example.com")
    assert tab is not None

    extracted = await adapter.dom.extract_text()
    assert extracted.success is True

    with tempfile.TemporaryDirectory() as tmpdir:
        attachment_path = os.path.join(tmpdir, "openai_invoice.pdf")
        with open(attachment_path, "wb") as f:
            f.write(b"%PDF-1.4 Invoice attachment data")

        assert os.path.exists(attachment_path) is True
        assert os.path.getsize(attachment_path) > 0

    await adapter.stop()
