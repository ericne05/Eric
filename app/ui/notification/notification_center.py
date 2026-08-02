"""
Notification Center Component.
Manages in-app notification queue (Downloading..., Goal Completed, Goal Failed, Need Confirmation).
"""

from dataclasses import dataclass, field
import datetime
from typing import List


@dataclass
class NotificationItem:
    title: str
    message: str
    level: str = "info"  # 'info', 'success', 'warning', 'error'
    timestamp: datetime.datetime = field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))


class NotificationCenter:
    """
    In-App Notification Queue Manager.
    """

    def __init__(self):
        self._queue: List[NotificationItem] = []

    def notify(self, title: str, message: str, level: str = "info") -> NotificationItem:
        item = NotificationItem(title=title, message=message, level=level)
        self._queue.append(item)
        return item

    def get_unread(self) -> List[NotificationItem]:
        return list(self._queue)

    def clear(self) -> None:
        self._queue.clear()
