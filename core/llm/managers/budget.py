"""
Token Budget Manager Implementation.
"""

from core.llm.interfaces import ITokenBudgetManager


class TokenBudgetManager(ITokenBudgetManager):
    def __init__(self, max_tokens_per_thread: int = 100000):
        self._usage: dict[str, int] = {}
        self._max = max_tokens_per_thread

    def record_usage(self, thread_id: str, tokens: int, cost: float = 0.0) -> None:
        if thread_id not in self._usage:
            self._usage[thread_id] = 0
        self._usage[thread_id] += tokens

    def check_budget(self, thread_id: str) -> bool:
        return self._usage.get(thread_id, 0) < self._max
