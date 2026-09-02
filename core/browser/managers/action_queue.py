"""
Browser Action Queue with Priority, Dependencies, and Cancellation.
"""
import asyncio
from typing import Callable, Any, Dict, List

from core.browser.models import BrowserAction, BrowserActionResult
from core.logger.interface import ILogger


class BrowserActionQueue:
    """
    Manages a DAG/Priority queue of browser actions to execute.
    """
    def __init__(self, logger: ILogger):
        self._logger = logger
        # asyncio.PriorityQueue uses tuples (priority, item)
        # We negate priority because asyncio.PriorityQueue returns lowest first
        self._queue = asyncio.PriorityQueue()
        self._actions: Dict[str, BrowserAction] = {}
        
    async def enqueue(self, action: BrowserAction, executor_func: Callable) -> None:
        """Enqueue an action along with the async function to execute it."""
        self._actions[action.id] = action
        # -action.priority so higher number = higher priority
        await self._queue.put((-action.priority, action.id, executor_func))
        self._logger.debug(f"[ActionQueue] Enqueued {action.name} (id: {action.id}, priority: {action.priority})")
        
    def cancel_action(self, action_id: str) -> None:
        """Cancels an action and all its dependencies recursively."""
        if action_id not in self._actions:
            return
            
        action = self._actions[action_id]
        if action.status not in ["completed", "failed", "cancelled"]:
            action.status = "cancelled"
            self._logger.info(f"[ActionQueue] Cancelled action {action.name} ({action.id})")
            
            # Find and cancel dependents
            for dep_action in self._actions.values():
                if action_id in dep_action.dependencies and dep_action.status not in ["completed", "failed", "cancelled"]:
                    self._logger.info(f"[ActionQueue] Cascading cancellation to {dep_action.name}")
                    self.cancel_action(dep_action.id)
                    
    async def process_next(self) -> BrowserActionResult | None:
        """Processes the next action in the queue."""
        if self._queue.empty():
            return None
            
        _, action_id, executor_func = await self._queue.get()
        action = self._actions.get(action_id)
        
        if not action or action.status == "cancelled":
            self._queue.task_done()
            return BrowserActionResult(success=False, error="Action was cancelled.")
            
        # Check dependencies
        for dep_id in action.dependencies:
            dep_action = self._actions.get(dep_id)
            if dep_action and dep_action.status != "completed":
                self._logger.warning(f"[ActionQueue] Dependencies not met for {action.name}. Cancelling.")
                self.cancel_action(action.id)
                self._queue.task_done()
                return BrowserActionResult(success=False, error="Dependencies not met.")
        
        action.status = "running"
        
        while action.retry_count <= action.max_retries and action.status == "running":
            try:
                self._logger.debug(f"[ActionQueue] Executing {action.name} (attempt {action.retry_count + 1})")
                
                # Execute with timeout
                result = await asyncio.wait_for(
                    executor_func(**action.arguments), 
                    timeout=action.timeout_ms / 1000.0
                )
                
                if result.success:
                    action.status = "completed"
                    self._queue.task_done()
                    return result
                
                self._logger.warning(f"[ActionQueue] Action {action.name} failed: {result.error}")
                
            except asyncio.TimeoutError:
                self._logger.warning(f"[ActionQueue] Action {action.name} timed out.")
            except Exception as e:
                self._logger.exception(f"[ActionQueue] Exception during {action.name}: {e}")
                
            action.retry_count += 1
            if action.retry_count <= action.max_retries:
                # Backoff
                await asyncio.sleep(0.5 * (2 ** (action.retry_count - 1)))
                
        action.status = "failed"
        self._queue.task_done()
        return BrowserActionResult(success=False, error=f"Action {action.name} failed after {action.max_retries} retries.")
