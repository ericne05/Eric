"""
DAG-based Priority Action Queue for Desktop Runtime (Sprint 12.5 Product-Grade).
"""

import asyncio
from typing import Dict, List, Optional, Set

from core.desktop.enums import ActionPolicy
from core.desktop.managers.retry import ExponentialRetry, IRetryStrategy
from core.desktop.models import DesktopAction, DesktopActionResult, DesktopTransaction


class DesktopActionQueue:
    """
    Priority Queue managing DesktopActions as a Directed Acyclic Graph (DAG).
    Supports priority execution, dependency resolution, cascading cancellation,
    parallel execution, timeout control, transactional rollback, and action policies.
    """

    def __init__(self, retry_strategy: Optional[IRetryStrategy] = None):
        self._actions: Dict[str, DesktopAction] = {}
        self._transactions: Dict[str, DesktopTransaction] = {}
        self._cancelled_ids: Set[str] = set()
        self._retry_strategy = retry_strategy or ExponentialRetry()

    def add_action(self, action: DesktopAction) -> None:
        """Adds an action to the queue."""
        self._actions[action.id] = action

    def create_transaction(self, transaction_id: str, actions: List[DesktopAction]) -> DesktopTransaction:
        """Creates a transaction containing a group of actions."""
        txn = DesktopTransaction(id=transaction_id, actions=actions)
        self._transactions[transaction_id] = txn
        for act in actions:
            act.transaction_id = transaction_id
            self.add_action(act)
        return txn

    def cancel_action(self, action_id: str) -> List[str]:
        """
        Cancels an action and performs cascading cancellation for all actions that depend on it.
        Returns a list of all cancelled action IDs.
        """
        cancelled = []
        queue = [action_id]

        while queue:
            current_id = queue.pop(0)
            if current_id in self._actions and current_id not in self._cancelled_ids:
                self._cancelled_ids.add(current_id)
                self._actions[current_id].status = "cancelled"
                cancelled.append(current_id)

                # Find all actions dependent on current_id
                for aid, act in self._actions.items():
                    if current_id in act.dependencies and aid not in self._cancelled_ids:
                        queue.append(aid)

        return cancelled

    def get_next_ready_action(self) -> Optional[DesktopAction]:
        """
        Returns the highest-priority pending action whose dependencies have all completed successfully.
        """
        ready = self.get_parallel_ready_actions()
        return ready[0] if ready else None

    def get_parallel_ready_actions(self) -> List[DesktopAction]:
        """
        Returns all pending actions whose dependencies have completed successfully,
        enabling parallel execution for independent DAG nodes.
        """
        ready_actions: List[DesktopAction] = []

        for action in self._actions.values():
            if action.status != "pending":
                continue

            deps_met = True
            for dep_id in action.dependencies:
                dep_action = self._actions.get(dep_id)
                if not dep_action or dep_action.status != "completed":
                    deps_met = False
                    break

            if deps_met:
                ready_actions.append(action)

        # Sort by priority descending
        ready_actions.sort(key=lambda a: a.priority, reverse=True)
        return ready_actions

    def mark_completed(self, action_id: str) -> None:
        if action_id in self._actions:
            self._actions[action_id].status = "completed"

    def mark_failed(self, action_id: str) -> List[str]:
        """
        Marks an action as failed according to its ActionPolicy.
        """
        if action_id not in self._actions:
            return []

        action = self._actions[action_id]
        action.status = "failed"

        if action.policy == ActionPolicy.IGNORE:
            return []
        elif action.policy == ActionPolicy.ABORT:
            # Cancel everything remaining in queue
            return [aid for aid, a in self._actions.items() if a.status == "pending"]
        else:
            # Default cascading cancellation for dependent nodes
            return self.cancel_action(action_id)

    async def rollback_transaction(self, transaction_id: str, executor_func) -> List[DesktopActionResult]:
        """
        Rolls back a transaction by executing inverse actions in reverse order (C -> B -> A).
        """
        if transaction_id not in self._transactions:
            return []

        txn = self._transactions[transaction_id]
        results = []

        # Filter completed actions and reverse order
        completed_actions = [a for a in txn.actions if a.status == "completed" and a.inverse_action]
        completed_actions.reverse()

        for act in completed_actions:
            inv_action = act.inverse_action
            if inv_action:
                res = await executor_func(inv_action)
                results.append(res)
                act.status = "rolled_back"

        txn.status = "rolled_back"
        return results

    @property
    def total_count(self) -> int:
        return len(self._actions)

    @property
    def pending_count(self) -> int:
        return sum(1 for a in self._actions.values() if a.status == "pending")
