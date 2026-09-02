"""
Desktop Subsystem Package (Sprint 12.5 Product-Grade).
"""

from core.desktop.adapters.mock_adapter import MockDesktopAdapter
from core.desktop.adapters.windows_adapter import WindowsDesktopAdapter
from core.desktop.enums import (
    ActionPolicy,
    AdapterHealthState,
    DesktopActionType,
    DesktopPermissions,
    DesktopState,
    RecoveryLevel,
    RetryStrategyType,
    WindowSelectorType,
)
from core.desktop.interfaces import (
    IDesktopClipboard,
    IDesktopNotification,
    IDesktopRuntime,
    IDesktopScreenshot,
    IDesktopSystem,
    IDesktopUI,
    IWindowManager,
)
from core.desktop.managers.action_queue import DesktopActionQueue
from core.desktop.managers.emergency import EmergencyStopManager
from core.desktop.managers.memory_pipeline import DesktopMemoryPipeline
from core.desktop.managers.recovery import DesktopRecoveryManager
from core.desktop.managers.retry import ExponentialRetry, FixedRetry, IRetryStrategy, LinearRetry
from core.desktop.models import (
    AdapterHealth,
    DesktopAction,
    DesktopActionResult,
    DesktopIntelligenceLayer,
    DesktopObservation,
    DesktopTransaction,
    DesktopWorkflow,
    ExecutionHistory,
    ExecutionHistoryRecord,
    RuntimeCapabilityRegistry,
    UIAccessibilitySnapshot,
    WindowInfo,
)
from core.desktop.planner import HybridDesktopPlanner

__all__ = [
    "DesktopState",
    "DesktopPermissions",
    "WindowSelectorType",
    "DesktopActionType",
    "ActionPolicy",
    "RecoveryLevel",
    "RetryStrategyType",
    "AdapterHealthState",
    "WindowInfo",
    "DesktopActionResult",
    "DesktopAction",
    "DesktopTransaction",
    "AdapterHealth",
    "RuntimeCapabilityRegistry",
    "UIAccessibilitySnapshot",
    "ExecutionHistory",
    "ExecutionHistoryRecord",
    "DesktopObservation",
    "DesktopIntelligenceLayer",
    "DesktopWorkflow",
    "IDesktopUI",
    "IDesktopScreenshot",
    "IWindowManager",
    "IDesktopClipboard",
    "IDesktopNotification",
    "IDesktopSystem",
    "IDesktopRuntime",
    "MockDesktopAdapter",
    "WindowsDesktopAdapter",
    "DesktopActionQueue",
    "DesktopRecoveryManager",
    "DesktopMemoryPipeline",
    "HybridDesktopPlanner",
    "EmergencyStopManager",
    "IRetryStrategy",
    "FixedRetry",
    "LinearRetry",
    "ExponentialRetry",
]
