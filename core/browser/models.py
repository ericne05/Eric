"""
Browser Runtime Models.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import uuid

from core.browser.enums import BrowserState, SelectorType, WorkflowState


@dataclass
class BrowserSelector:
    """Represents a UI element selector."""
    type: SelectorType
    value: str
    options: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BrowserTab:
    """Represents a single browser tab/page."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    url: str = "about:blank"
    title: str = ""
    history: List[str] = field(default_factory=list)


@dataclass
class BrowserContextState:
    """Represents the context state (cookies, permissions, etc.)."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    cookies: List[Dict[str, Any]] = field(default_factory=list)
    permissions: List[str] = field(default_factory=list)
    user_agent: str = ""
    geolocation: Optional[Dict[str, float]] = None


@dataclass
class BrowserSession:
    """Represents a logical browser session containing tabs and sharing a context."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    context: BrowserContextState = field(default_factory=BrowserContextState)
    tabs: List[BrowserTab] = field(default_factory=list)
    current_tab_id: Optional[str] = None


@dataclass
class BrowserActionResult:
    """Standardized result for any browser action."""
    success: bool
    page_title: str = ""
    url: str = ""
    elapsed_ms: int = 0
    screenshot_base64: Optional[str] = None
    error: Optional[str] = None
    data: Any = None  # E.g. extracted text or element info


@dataclass
class BrowserAction:
    """Represents a single action in the queue or transaction."""
    name: str  # e.g., 'click', 'goto'
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    arguments: Dict[str, Any] = field(default_factory=dict)
    retry_count: int = 0
    max_retries: int = 3
    timeout_ms: int = 10000
    priority: int = 0  # Higher means higher priority
    dependencies: List[str] = field(default_factory=list) # List of action IDs that must complete first
    status: str = "pending" # pending, running, completed, failed, cancelled


@dataclass
class AccessibilitySnapshot:
    """Represents a simplified, semantic view of the page (Accessibility Tree)."""
    tree_data: Dict[str, Any] = field(default_factory=dict)
    interactive_elements: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class SelectorCache:
    """Caches successful selectors for quick reuse."""
    entries: Dict[str, BrowserSelector] = field(default_factory=dict) # Hash -> Selector


@dataclass
class PlannerConfidence:
    """Represents the LLM's confidence level in the current plan."""
    score: float = 1.0 # 0.0 to 1.0
    reasoning: str = ""
    needs_human_help: bool = False


@dataclass
class InteractionHistory:
    """Records the history of recent actions and their outcomes."""
    recent_actions: List[BrowserAction] = field(default_factory=list)
    recent_results: List[BrowserActionResult] = field(default_factory=list)


@dataclass
class BrowserObservation:
    """Represents the agent's observation of the current browser state."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    url: str = ""
    title: str = ""
    screenshot_base64: Optional[str] = None
    network_idle: bool = True
    # The Intelligence Layer components
    accessibility_snapshot: AccessibilitySnapshot = field(default_factory=AccessibilitySnapshot)
    interaction_history: InteractionHistory = field(default_factory=InteractionHistory)


@dataclass
class BrowserIntelligenceLayer:
    """The central intelligence state for the Browser Runtime."""
    observation: BrowserObservation = field(default_factory=BrowserObservation)
    accessibility_snapshot: AccessibilitySnapshot = field(default_factory=AccessibilitySnapshot)
    selector_cache: SelectorCache = field(default_factory=SelectorCache)
    planner_confidence: PlannerConfidence = field(default_factory=PlannerConfidence)
    interaction_history: InteractionHistory = field(default_factory=InteractionHistory)
    

@dataclass
class BrowserWorkflow:
    """Represents a state machine for a high-level browser task."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    goal: str = ""
    state: WorkflowState = WorkflowState.INIT
    actions: List[BrowserAction] = field(default_factory=list)
    intelligence: BrowserIntelligenceLayer = field(default_factory=BrowserIntelligenceLayer)
