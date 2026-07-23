"""
Conversation Manager Implementations.
"""

from typing import List

from core.llm.enums import MessageRole
from core.llm.interfaces import IConversationManager
from core.llm.models import LLMMessage


class InMemoryConversationManager(IConversationManager):
    def __init__(self):
        self._threads: dict[str, List[LLMMessage]] = {}

    def append_message(self, thread_id: str, message: LLMMessage) -> None:
        if thread_id not in self._threads:
            self._threads[thread_id] = []
        self._threads[thread_id].append(message)

    def get_history(self, thread_id: str) -> List[LLMMessage]:
        return self._threads.get(thread_id, [])

    def clear(self, thread_id: str) -> None:
        if thread_id in self._threads:
            self._threads.pop(thread_id)


class SlidingWindowConversationManager(IConversationManager):
    """
    A conversation manager that prunes oldest messages when the count exceeds a threshold,
    while always preserving the system instruction if present.
    """
    def __init__(self, max_messages: int = 50):
        self._threads: dict[str, List[LLMMessage]] = {}
        self._max = max_messages

    def append_message(self, thread_id: str, message: LLMMessage) -> None:
        if thread_id not in self._threads:
            self._threads[thread_id] = []
            
        thread = self._threads[thread_id]
        thread.append(message)
        
        # Prune if exceeded
        if len(thread) > self._max:
            # We want to keep system messages if they are at the start (usually they are)
            sys_msgs = [m for m in thread if m.role == MessageRole.SYSTEM]
            other_msgs = [m for m in thread if m.role != MessageRole.SYSTEM]
            
            # Trim oldest from other_msgs
            keep_count = self._max - len(sys_msgs)
            if keep_count > 0:
                other_msgs = other_msgs[-keep_count:]
            else:
                other_msgs = []
                
            self._threads[thread_id] = sys_msgs + other_msgs

    def get_history(self, thread_id: str) -> List[LLMMessage]:
        return self._threads.get(thread_id, [])

    def clear(self, thread_id: str) -> None:
        if thread_id in self._threads:
            self._threads.pop(thread_id)
