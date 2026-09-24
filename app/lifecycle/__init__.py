"""
Application Lifecycle Package (app/lifecycle).

Exports:
- CompanionApplication: The Windows companion coordinator.
- CompanionStartupResult: Structured result of starting the companion.
"""

from app.lifecycle.companion_app import (
    CompanionApplication,
    CompanionStartupResult,
)

__all__ = [
    "CompanionApplication",
    "CompanionStartupResult",
]
