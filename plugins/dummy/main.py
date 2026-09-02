"""
Dummy Plugin Implementation.
"""

import asyncio

from core.di.interfaces import IDependencyModule
from core.events.event import Event
from core.plugins.interfaces import IPlugin, PluginContext
from core.tools.decorator import tool
from core.tools.enums import ToolPermission


@tool(
    namespace="dummy",
    name="search",
    description="A dummy search tool that simulates streaming results.",
    permissions=[ToolPermission.NETWORK],
    timeout_seconds=5
)
async def dummy_search_tool(context, query: str):
    """Yields search results one by one to simulate streaming."""
    results = [f"Result 1 for {query}", f"Result 2 for {query}", f"Result 3 for {query}"]
    for res in results:
        await asyncio.sleep(0.5)  # Simulate network delay
        yield res


class DummyPlugin(IPlugin):
    """
    A dummy plugin that listens to system.ready.
    """

    def __init__(self):
        self._context = None

    @property
    def module(self) -> IDependencyModule | None:
        return None

    def initialize(self, context: PluginContext) -> None:
        self._context = context
        context.logger.info("[DummyPlugin] Initializing...")
        
        # Register tools
        context.tool_registry.register(dummy_search_tool)
        context.logger.info("[DummyPlugin] Registered tool 'dummy.search'")
        
        # Subscribe to system.ready
        context.event_bus.subscribe("system.ready", self._on_ready)

    def dispose(self) -> None:
        if self._context:
            self._context.logger.info("[DummyPlugin] Disposing...")
            # Note: EventBus disposes subscribers on shutdown, so manual unsub not strictly required here.

    def _on_ready(self, event: Event) -> None:
        if self._context:
            self._context.logger.info(f"[DummyPlugin] Received system.ready! Version: {event.payload.get('version')}")
