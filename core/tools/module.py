"""
Tool System Module.
"""

from typing import TYPE_CHECKING

from core.di.interfaces import IDependencyModule

if TYPE_CHECKING:
    from core.di.container import Container


class ToolSystemModule(IDependencyModule):
    """
    Registers ToolRegistry and ToolExecutor.
    """

    def register(self, container: "Container") -> None:
        from core.telemetry.interfaces import ITelemetryManager
        from core.telemetry.manager import InMemoryTelemetryManager
        from core.security.interfaces import IPolicyEngine
        from core.security.policy import AllowAllPolicy
        from core.tools.interfaces import IToolRegistry, IToolExecutor
        from core.tools.executor import ToolExecutor
        from core.tools.registry import ToolRegistry

        container.add_singleton(ITelemetryManager, InMemoryTelemetryManager)
        container.add_singleton(IPolicyEngine, AllowAllPolicy)
        container.add_singleton(IToolRegistry, ToolRegistry)
        
        def _executor_factory(c):
            return ToolExecutor(
                registry=c.resolve(IToolRegistry),
                policy_engine=c.resolve(IPolicyEngine),
                telemetry=c.resolve(ITelemetryManager)
            )
        container.add_singleton(IToolExecutor, _executor_factory)
