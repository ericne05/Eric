"""
Timeline Widget Component.
Displays visual task pipeline timeline (✓ Open Browser -> ✓ Login -> ✓ Search -> ⏳ Download).
"""

from typing import Any, Dict, List


class TimelineWidget:
    """
    Visual Task Pipeline Timeline Widget.
    """

    def __init__(self):
        self._steps: List[Dict[str, Any]] = []

    def set_steps(self, steps: List[Dict[str, Any]]) -> None:
        self._steps = steps

    def get_steps(self) -> List[Dict[str, Any]]:
        return self._steps
