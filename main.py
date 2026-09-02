"""
Eric AI Assistant — Root Application Entry Point.
Executable Entry Point for PyInstaller Single-File and Inno Setup Windows Release.
"""

import os, sys, asyncio
from pathlib import Path
from dotenv import load_dotenv

env_paths = [
    Path.cwd() / ".env",
    Path(__file__).resolve().parent / ".env",
    Path(__file__).resolve().parent.parent / ".env",
]
for ep in env_paths:
    if ep.exists():
        load_dotenv(dotenv_path=ep, override=True)

from app.main import main

if __name__ == "__main__":
    if hasattr(sys.stdin, "reconfigure"):
        try:
            sys.stdin.reconfigure(encoding="utf-8")
        except Exception:
            pass
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    asyncio.run(main())
