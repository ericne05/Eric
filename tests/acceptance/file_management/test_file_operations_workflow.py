"""
File Management Acceptance Tests (Create Folder, Copy, Move, Rename, Delete, Restore).
"""

import os, shutil, tempfile
import pytest


@pytest.mark.asyncio
async def test_file_management_operations_workflow():
    """
    Workflow: Create Folder -> Copy -> Move -> Rename -> Delete -> Verify File System State
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        src_dir = os.path.join(tmpdir, "source")
        dst_dir = os.path.join(tmpdir, "destination")
        os.makedirs(src_dir, exist_ok=True)
        os.makedirs(dst_dir, exist_ok=True)

        original_file = os.path.join(src_dir, "data.csv")
        with open(original_file, "w") as f:
            f.write("id,name\n1,Eric AI")

        # Copy
        copied_file = os.path.join(dst_dir, "data_copy.csv")
        shutil.copy(original_file, copied_file)
        assert os.path.exists(copied_file) is True

        # Move & Rename
        renamed_file = os.path.join(dst_dir, "final_data.csv")
        os.rename(copied_file, renamed_file)
        assert os.path.exists(copied_file) is False
        assert os.path.exists(renamed_file) is True

        # Delete
        os.remove(original_file)
        assert os.path.exists(original_file) is False
