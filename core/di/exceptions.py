"""
Dependency Injection Exceptions.

Provides a structured exception hierarchy for DI resolution failures.
"""


class DIError(Exception):
    """Base exception for all Dependency Injection errors."""


class DependencyResolutionError(DIError):
    """
    Raised when a dependency cannot be resolved.

    Common causes:
    - Service not registered in the container.
    - Constructor parameter missing type hints.
    - Unresolvable dependency chain.
    """


class CircularDependencyError(DependencyResolutionError):
    """
    Raised when a circular dependency is detected during resolution.

    Stores the full resolution stack so the developer can trace the cycle:
        A → B → C → A

    Attributes:
        chain: The list of types forming the circular dependency.
    """

    def __init__(self, chain: list[type]) -> None:
        self.chain = chain
        chain_str = " → ".join(t.__name__ for t in chain)
        super().__init__(f"Circular dependency detected: {chain_str}")
