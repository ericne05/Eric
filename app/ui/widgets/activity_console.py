"""
Activity Console Component.
Provides a terminal-like real-time activity log stream for debugging and transparency.
"""

import datetime
from typing import List


class ActivityConsole:
    """
    Terminal-style Realtime Activity Stream Widget.
    """

    def __init__(self):
        self._logs: List[str] = []

    def log(self, message: str) -> str:
        timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%H:%M:%S")
        entry = f"[{timestamp}] {message}"
        self._logs.append(entry)
        return entry

    def get_logs(self) -> List[str]:
        return list(self._logs)

    def clear(self) -> None:
        self._logs.clear()
