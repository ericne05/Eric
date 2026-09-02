"""
Browser Context Manager.
"""
from typing import Dict, Any

from core.browser.models import BrowserContextState
from core.logger.interface import ILogger


class BrowserContextManager:
    """
    Manages browser contexts, including cookies, permissions, and proxies.
    """
    def __init__(self, logger: ILogger):
        self._logger = logger
        self._contexts: Dict[str, BrowserContextState] = {}
        
    def create_context(self) -> BrowserContextState:
        """Creates a new isolated browser context state."""
        ctx = BrowserContextState()
        self._contexts[ctx.id] = ctx
        self._logger.info(f"[ContextManager] Created new context: {ctx.id}")
        return ctx
        
    def set_cookie(self, context_id: str, cookie: Dict[str, Any]) -> None:
        if context_id in self._contexts:
            self._contexts[context_id].cookies.append(cookie)
            
    def grant_permission(self, context_id: str, permission: str) -> None:
        if context_id in self._contexts:
            if permission not in self._contexts[context_id].permissions:
                self._contexts[context_id].permissions.append(permission)
