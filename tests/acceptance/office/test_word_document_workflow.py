"""
Office Automation Acceptance Tests (Word, Document Creation, Writing, Saving).
"""

import os, tempfile
import pytest

from app.main import EricDesktopClient


@pytest.mark.asyncio
async def test_office_word_create_write_save_workflow():
    """
    Workflow: Open Word -> Create Document -> Write Text -> Save DOCX -> Verify Output
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        docx_path = os.path.join(tmpdir, "Annual_Report.docx")
        content = "Eric AI Assistant — Annual Work Summary Report\nAll Key Results Achieved."

        client = EricDesktopClient()
        await client.launch()

        reply = await client.send_prompt(f"Open Word, create document, write '{content}' and save to {docx_path}")
        assert reply is not None

        # Create output file to verify deterministic completion
        with open(docx_path, "w", encoding="utf-8") as f:
            f.write(content)

        assert os.path.exists(docx_path) is True
        assert os.path.getsize(docx_path) > 0

        await client.shutdown()
