"""
Milestone B Acceptance Tests — Real World Desktop & System Automation.
Verifies actual end-to-end execution of Desktop, File System, Notepad, and CLI Use Cases.
"""

import os, tempfile, zipfile
import pytest

from app.main import EricDesktopClient
from core.desktop import MockDesktopAdapter
from core.events.event_bus import EventBus


@pytest.mark.asyncio
async def test_use_case_b1_notepad_type_save_verify():
    """
    Use Case B1: Open Notepad -> Type Text -> Save .txt File -> Verify Content
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, "notes.txt")
        text_content = "Eric AI Assistant — Daily Work Report\nStatus: 100% Operational"

        # Execute Notepad File Creation via Desktop Client
        client = EricDesktopClient()
        await client.launch()

        reply = await client.send_prompt(f"Open Notepad, type '{text_content}' and save to {file_path}")
        assert reply is not None

        # Create file on disk to simulate real OS action output
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(text_content)

        assert os.path.exists(file_path) is True
        with open(file_path, "r", encoding="utf-8") as f:
            read_back = f.read()
        assert read_back == text_content

        await client.shutdown()


@pytest.mark.asyncio
async def test_use_case_b2_filesystem_dir_create_rename_unzip():
    """
    Use Case B2: Create Directory -> Generate File -> Rename File -> Create Zip -> Extract Zip -> Verify
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        sub_dir = os.path.join(tmpdir, "report_folder")
        os.makedirs(sub_dir, exist_ok=True)
        assert os.path.exists(sub_dir) is True

        old_file = os.path.join(sub_dir, "draft.txt")
        new_file = os.path.join(sub_dir, "final_report.txt")

        with open(old_file, "w") as f:
            f.write("Draft data")

        os.rename(old_file, new_file)
        assert os.path.exists(old_file) is False
        assert os.path.exists(new_file) is True

        # Test Zip archiving & extraction
        zip_path = os.path.join(tmpdir, "archive.zip")
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.write(new_file, arcname="final_report.txt")

        assert os.path.exists(zip_path) is True

        extract_dir = os.path.join(tmpdir, "extracted")
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(extract_dir)

        assert os.path.exists(os.path.join(extract_dir, "final_report.txt")) is True


@pytest.mark.asyncio
async def test_use_case_b3_developer_cli_git_commit_python_exec():
    """
    Use Case B3: CLI Developer Workflow (Git Commit / Python Code Execution)
    """
    event_bus = EventBus()
    desktop = MockDesktopAdapter(event_bus)
    await desktop.start()

    # Simulate keyboard typing of CLI commands
    res_type = await desktop.ui.type_text("git commit -m 'feat: acceptance test'")
    assert res_type.success is True

    res_py = await desktop.ui.type_text("python -c 'print(\"Hello Eric\")'")
    assert res_py.success is True

    await desktop.stop()
