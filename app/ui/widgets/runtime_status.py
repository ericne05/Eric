"""
Runtime Status Widget Component.
Displays live health status badges for Browser 🟢, Desktop 🟢, Vision 🟢, Knowledge 🟢.
"""

from typing import Dict


class RuntimeStatusWidget:
    """
    Runtime Status Health Badge Widget.
    """

    def __init__(self):
        self._health: Dict[str, str] = {"browser": "ready", "desktop": "ready", "vision": "ready", "knowledge": "ready"}

    def update_health(self, health: Dict[str, str]) -> None:
        self._health.update(health)

    def get_badges(self) -> Dict[str, str]:
        badges = {}
        for k, v in self._health.items():
            if v in ("ready", "active", "ok"):
                badges[k] = "🟢 Ready"
            elif v in ("warning", "recovering"):
                badges[k] = "🟡 Recovering"
            else:
                badges[k] = "🔴 Error"
        return badges
