"""
Desktop Runtime Data Models (Sprint 12.5 Product-Grade).
"""

from dataclasses import dataclass, field
import datetime
from typing import Any, Dict, List, Optional, Tuple
import uuid

from core.browser.enums import WorkflowState
from core.desktop.enums import (
    ActionPolicy,
    AdapterHealthState,
    DesktopActionType,
    RecoveryLevel,
    RetryStrategyType,
    WindowSelectorType,
)


@dataclass
class WindowInfo:
    """Represents metadata of a desktop window."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    process_name: str = ""
    process_id: int = 0
    bounds: Tuple[int, int, int, int] = (0, 0, 800, 600)  # x, y, width, height
    is_focused: bool = False
    is_minimized: bool = False


@dataclass
class DesktopActionResult:
    """Standardized result for any desktop action with Telemetry details."""
    success: bool
    elapsed_ms: int = 0
    screenshot_base64: Optional[str] = None
    error: Optional[str] = None
    data: Any = None
    # Telemetry metrics
    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    confidence_score: float = 1.0


@dataclass
class DesktopAction:
    """Represents a single desktop action in the queue or workflow."""
    name: str  # Action name e.g., 'click', 'type_text'
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    arguments: Dict[str, Any] = field(default_factory=dict)
    retry_count: int = 0
    max_retries: int = 3
    timeout_ms: int = 10000
    priority: int = 0  # Higher means higher priority
    dependencies: List[str] = field(default_factory=list)  # Action IDs that must complete first
    status: str = "pending"  # pending, running, completed, failed, cancelled
    policy: ActionPolicy = ActionPolicy.RECOVER
    inverse_action: Optional["DesktopAction"] = None  # Action used for Rollback
    transaction_id: Optional[str] = None


@dataclass
class DesktopTransaction:
    """Represents a sequence of actions that must complete as a single transaction."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    actions: List[DesktopAction] = field(default_factory=list)
    status: str = "pending"  # pending, committed, rolled_back, failed


@dataclass
class AdapterHealth:
    """Self-check status of the active desktop adapter."""
    state: AdapterHealthState = AdapterHealthState.HEALTHY
    mouse_ok: bool = True
    keyboard_ok: bool = True
    screenshot_ok: bool = True
    window_ok: bool = True
    error_details: Optional[str] = None


@dataclass
class RuntimeCapabilityRegistry:
    """Registry declaring current capability flags for the active Desktop Runtime."""
    can_mouse: bool = True
    can_keyboard: bool = True
    can_window: bool = True
    can_screenshot: bool = True
    can_clipboard: bool = True
    can_notification: bool = True
    can_system_power: bool = True
    can_ocr: bool = False  # OCR belongs to Vision Runtime
    can_voice: bool = False  # Voice belongs to Voice Runtime


@dataclass
class UIAccessibilitySnapshot:
    """Represents a simplified, semantic view of the desktop UI (UIAutomation Tree)."""
    tree_data: Dict[str, Any] = field(default_factory=dict)
    interactive_elements: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class DesktopSelectorCache:
    """Caches successful selectors or coordinates for quick reuse."""
    entries: Dict[str, Dict[str, Any]] = field(default_factory=dict)


@dataclass
class DesktopPlannerConfidence:
    """Represents the LLM's confidence level in the current desktop plan."""
    score: float = 1.0  # 0.0 to 1.0
    reasoning: str = ""
    needs_human_help: bool = False


@dataclass
class ExecutionHistoryRecord:
    """A record of an executed desktop action and its outcome."""
    action: DesktopAction
    result: DesktopActionResult
    timestamp: datetime.datetime = field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))


@dataclass
class ExecutionHistory:
    """Records the history of recent desktop actions and their outcomes."""
    records: List[ExecutionHistoryRecord] = field(default_factory=list)


@dataclass
class DesktopObservation:
    """Represents the agent's observation of the current desktop environment."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    focused_window: Optional[WindowInfo] = None
    active_windows: List[WindowInfo] = field(default_factory=list)
    screenshot_base64: Optional[str] = None
    screen_resolution: Tuple[int, int] = (1920, 1080)
    ui_accessibility_snapshot: UIAccessibilitySnapshot = field(default_factory=UIAccessibilitySnapshot)


@dataclass
class DesktopIntelligenceLayer:
    """The central intelligence state for the Desktop Runtime."""
    observation: DesktopObservation = field(default_factory=DesktopObservation)
    ui_accessibility_snapshot: UIAccessibilitySnapshot = field(default_factory=UIAccessibilitySnapshot)
    selector_cache: DesktopSelectorCache = field(default_factory=DesktopSelectorCache)
    planner_confidence: DesktopPlannerConfidence = field(default_factory=DesktopPlannerConfidence)
    execution_history: ExecutionHistory = field(default_factory=ExecutionHistory)
    capability_registry: RuntimeCapabilityRegistry = field(default_factory=RuntimeCapabilityRegistry)
    adapter_health: AdapterHealth = field(default_factory=AdapterHealth)


@dataclass
class DesktopWorkflow:
    """Represents a state machine for a high-level desktop automation task."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    goal: str = ""
    state: WorkflowState = WorkflowState.INIT
    actions: List[DesktopAction] = field(default_factory=list)
    intelligence: DesktopIntelligenceLayer = field(default_factory=DesktopIntelligenceLayer)
