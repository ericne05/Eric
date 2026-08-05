"""
Eric AI Assistant — Root Application Entry Point.
Executable Entry Point for PyInstaller Single-File and Inno Setup Windows Release.
"""

import sys, asyncio
from dotenv import load_dotenv

from app.main import main

if __name__ == "__main__":
    load_dotenv()
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    asyncio.run(main())
