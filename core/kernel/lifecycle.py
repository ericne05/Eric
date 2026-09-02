"""
System lifecycle states for Eric.

Defines the ordered states that the Kernel transitions through
during boot and shutdown. States are sequential — no skipping.
"""

from enum import Enum, auto


class SystemState(Enum):
    """Represents the current state of the Eric system."""

    CREATED = auto()        # Kernel instantiated, nothing initialized
    BOOTING = auto()        # Boot sequence in progress
    READY = auto()          # All subsystems initialized, awaiting run
    RUNNING = auto()        # Main event loop active
    SHUTTING_DOWN = auto()  # Graceful shutdown in progress
    STOPPED = auto()        # All resources released, process can exit
    FAILED = auto()         # System encountered an unrecoverable error


class StateTransitionError(RuntimeError):
    """Raised when an invalid system state transition is attempted."""
    pass
