"""
Capability Negotiation System.

Allows Planners to query Runtimes for what they can do
before creating a plan. Supports multi-runtime environments
where the Planner must choose which Runtime to dispatch to.
"""

from typing import Dict, List, Optional

from core.runtime.interfaces import IRuntime, IRuntimeCapability


class CapabilityRegistry(IRuntimeCapability):
    """
    Concrete implementation of IRuntimeCapability.
    Holds a flat dict of capability flags that Planners can query.
    """

    def __init__(self, capabilities: Optional[Dict[str, bool]] = None):
        self._capabilities: Dict[str, bool] = capabilities or {}

    def get_capabilities(self) -> Dict[str, bool]:
        return dict(self._capabilities)

    def supports(self, capability: str) -> bool:
        return self._capabilities.get(capability, False)

    def get_capability_list(self) -> List[str]:
        return [k for k, v in self._capabilities.items() if v]

    def set_capability(self, name: str, supported: bool) -> None:
        self._capabilities[name] = supported


class CapabilityNegotiator:
    """
    Allows the Planner to discover and negotiate capabilities
    across multiple registered Runtimes.

    Usage:
        negotiator = CapabilityNegotiator()
        negotiator.register_runtime("desktop", desktop_runtime)
        negotiator.register_runtime("browser", browser_runtime)

        # Planner asks: who can screenshot?
        runtimes = negotiator.find_runtimes_supporting("screenshot")
        # -> ["desktop", "browser"]

        # Planner asks: what can desktop do?
        caps = negotiator.query_runtime("desktop")
        # -> ["mouse", "keyboard", "window", "screenshot", ...]
    """

    def __init__(self):
        self._runtimes: Dict[str, IRuntime] = {}

    def register_runtime(self, name: str, runtime: IRuntime) -> None:
        self._runtimes[name] = runtime

    def unregister_runtime(self, name: str) -> None:
        self._runtimes.pop(name, None)

    def query_runtime(self, name: str) -> List[str]:
        """Returns the list of supported capabilities for a specific runtime."""
        runtime = self._runtimes.get(name)
        if not runtime:
            return []
        return runtime.get_runtime_capabilities().get_capability_list()

    def find_runtimes_supporting(self, capability: str) -> List[str]:
        """Returns a list of runtime names that support the given capability."""
        result = []
        for name, runtime in self._runtimes.items():
            caps = runtime.get_runtime_capabilities()
            if caps.supports(capability):
                result.append(name)
        return result

    def get_all_capabilities(self) -> Dict[str, List[str]]:
        """Returns a map of runtime_name -> list of supported capabilities."""
        return {
            name: runtime.get_runtime_capabilities().get_capability_list()
            for name, runtime in self._runtimes.items()
        }

    @property
    def runtime_names(self) -> List[str]:
        return list(self._runtimes.keys())
