"""
Unit/Integration tests for Sprint 17.5 Final Hardening Pass.

Covers:
- Fix #1: AppBootstrap / DI (single composition root, shared EventBus, DI-resolved services)
- Fix #2: WindowsDesktopAdapter execute() real failure propagation
- Fix #3: GoalSpecification parameters preserved through GoalManager → Planner → Runtime
- Fix #4: LLMRouter as single routing authority
"""

import sys
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from core.desktop import WindowsDesktopAdapter, MockDesktopAdapter
from core.desktop.models import DesktopActionResult
from core.events.event_bus import EventBus
from core.goals.enums import GoalState
from core.goals.models import Goal, GoalSpecification, CapabilityRequirement
from core.goals.decomposition import GoalDecomposer
from core.goals.planner import AutonomousGoalPlanner
from core.cognition.models import SharedCognitiveContext
from core.cognition.coordinator import CognitiveCoordinator
from core.runtime.capability import CapabilityNegotiator
from core.llm.router import LLMRouter
from core.llm.models import LLMResponse, LLMMessage, ModelConfig
from core.llm.enums import FinishReason


# ═══════════════════════════════════════════════════════════════════════════
# FIX #1 — AppBootstrap DI Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestAppBootstrapDI:
    """Verify AppBootstrap uses Kernel as the single composition root."""

    @pytest.mark.asyncio
    async def test_bootstrap_kernel_not_none(self):
        """Kernel must be initialized after bootstrap.initialize()."""
        from app.bootstrap.app_bootstrap import AppBootstrap
        bootstrap = AppBootstrap()
        await bootstrap.initialize()
        assert bootstrap.kernel is not None

    @pytest.mark.asyncio
    async def test_event_bus_shared_with_kernel(self):
        """AppBootstrap.event_bus must be the SAME object as kernel.event_bus."""
        from app.bootstrap.app_bootstrap import AppBootstrap
        bootstrap = AppBootstrap()
        await bootstrap.initialize()
        assert bootstrap.event_bus is bootstrap.kernel.event_bus, (
            "AppBootstrap.event_bus must be the kernel's EventBus (shared singleton), not a new instance."
        )

    @pytest.mark.asyncio
    async def test_di_container_not_none(self):
        """Kernel DI container must exist."""
        from app.bootstrap.app_bootstrap import AppBootstrap
        bootstrap = AppBootstrap()
        await bootstrap.initialize()
        assert bootstrap.kernel.container is not None

    @pytest.mark.asyncio
    async def test_desktop_runtime_from_di(self):
        """Desktop runtime must be resolvable from the Kernel's DI container."""
        from app.bootstrap.app_bootstrap import AppBootstrap
        from core.desktop.interfaces import IDesktopRuntime
        bootstrap = AppBootstrap()
        await bootstrap.initialize()
        # The runtime resolved in AppBootstrap must match what the container provides
        container_runtime = bootstrap.kernel.container.resolve(IDesktopRuntime)
        assert bootstrap.desktop_runtime is container_runtime, (
            "AppBootstrap.desktop_runtime must be the DI-resolved singleton, not a duplicate."
        )

    @pytest.mark.asyncio
    async def test_negotiator_from_di(self):
        """CapabilityNegotiator must be the DI-resolved singleton."""
        from app.bootstrap.app_bootstrap import AppBootstrap
        from core.runtime.capability import CapabilityNegotiator
        bootstrap = AppBootstrap()
        await bootstrap.initialize()
        container_negotiator = bootstrap.kernel.container.resolve(CapabilityNegotiator)
        assert bootstrap.negotiator is container_negotiator

    @pytest.mark.asyncio
    async def test_goal_manager_from_di(self):
        """GoalManager must be the DI-resolved singleton."""
        from app.bootstrap.app_bootstrap import AppBootstrap
        from core.goals import GoalManager
        bootstrap = AppBootstrap()
        await bootstrap.initialize()
        container_gm = bootstrap.kernel.container.resolve(GoalManager)
        assert bootstrap.goal_manager is container_gm

    @pytest.mark.asyncio
    async def test_coordinator_from_di(self):
        """CognitiveCoordinator must be the DI-resolved singleton."""
        from app.bootstrap.app_bootstrap import AppBootstrap
        from core.cognition import CognitiveCoordinator
        bootstrap = AppBootstrap()
        await bootstrap.initialize()
        container_coord = bootstrap.kernel.container.resolve(CognitiveCoordinator)
        assert bootstrap.coordinator is container_coord


# ═══════════════════════════════════════════════════════════════════════════
# FIX #2 — Desktop Execute Failure Propagation
# ═══════════════════════════════════════════════════════════════════════════

class TestDesktopExecuteFailurePropagation:
    """Verify WindowsDesktopAdapter.execute() correctly aggregates action results."""

    @pytest.mark.asyncio
    async def test_all_actions_success(self):
        """All supported actions succeed → overall success=True."""
        bus = EventBus()
        adapter = WindowsDesktopAdapter(event_bus=bus, sandbox=True)

        plan = [
            {"action": "click", "x": 100, "y": 200},
            {"action": "type_text", "text": "hello"},
            {"action": "hotkey", "keys": ["ctrl", "c"]},
            {"action": "launch", "target": "notepad"},
        ]
        result = await adapter.execute(plan)

        assert result["success"] is True
        assert result["actions_executed"] == 4
        assert len(result["results"]) == 4
        for r in result["results"]:
            assert isinstance(r, DesktopActionResult)
            assert r.success is True

    @pytest.mark.asyncio
    async def test_one_action_fails_overall_fails(self):
        """If one delegated action fails, overall success must be False."""
        bus = EventBus()
        adapter = WindowsDesktopAdapter(event_bus=bus, sandbox=True)

        # Patch click to return a failure result
        failing_result = DesktopActionResult(success=False, error="Simulated click failure")
        adapter._ui.click = AsyncMock(return_value=failing_result)

        plan = [
            {"action": "click", "x": 100, "y": 200},
            {"action": "type_text", "text": "hello"},
        ]
        result = await adapter.execute(plan)

        assert result["success"] is False
        assert result["actions_executed"] == 2
        assert result["results"][0].success is False

    @pytest.mark.asyncio
    async def test_unsupported_action_fails(self):
        """Unknown action must return explicit DesktopActionResult(success=False)."""
        bus = EventBus()
        adapter = WindowsDesktopAdapter(event_bus=bus, sandbox=True)

        plan = [{"action": "unknown_action_xyz"}]
        result = await adapter.execute(plan)

        assert result["success"] is False
        assert result["actions_executed"] == 1
        failed_res = result["results"][0]
        assert isinstance(failed_res, DesktopActionResult)
        assert failed_res.success is False
        assert "unsupported" in failed_res.error.lower() or "unknown" in failed_res.error.lower()

    @pytest.mark.asyncio
    async def test_failed_launch_propagates(self):
        """Failed launch_application must propagate failure to overall result."""
        bus = EventBus()
        adapter = WindowsDesktopAdapter(event_bus=bus, sandbox=True)

        failing_result = DesktopActionResult(success=False, error="Launch failed: not found")
        adapter._system.launch_application = AsyncMock(return_value=failing_result)

        plan = [{"action": "launch", "target": "nonexistent_app"}]
        result = await adapter.execute(plan)

        assert result["success"] is False
        assert result["results"][0].success is False

    @pytest.mark.asyncio
    async def test_empty_plan_succeeds(self):
        """Empty plan must succeed with zero actions executed."""
        bus = EventBus()
        adapter = WindowsDesktopAdapter(event_bus=bus, sandbox=True)

        result = await adapter.execute([])

        assert result["success"] is True
        assert result["actions_executed"] == 0
        assert result["results"] == []


# ═══════════════════════════════════════════════════════════════════════════
# FIX #3 — GoalSpecification Parameter Preservation
# ═══════════════════════════════════════════════════════════════════════════

class TestGoalSpecParameterPreservation:
    """Verify structured GoalSpecification parameters flow through the pipeline."""

    def test_decomposer_preserves_intent_as_subgoal_title(self):
        """GoalDecomposer must use spec.intent as the execution subgoal title."""
        spec = GoalSpecification(
            intent="launch_application",
            parameters={"application": "notepad"},
        )
        decomposer = GoalDecomposer()
        goal = decomposer.decompose(spec)

        # The execution subgoal should have intent as title
        interact_sg = goal.graph.subgoals.get("sg_interact")
        assert interact_sg is not None, "sg_interact subgoal must exist"
        assert interact_sg.title == "launch_application", (
            f"Subgoal title must be spec.intent='launch_application', got '{interact_sg.title}'"
        )

    def test_decomposer_preserves_parameters_in_result_data(self):
        """GoalDecomposer must store spec.parameters in the subgoal's result_data."""
        spec = GoalSpecification(
            intent="launch_application",
            parameters={"application": "notepad"},
        )
        decomposer = GoalDecomposer()
        goal = decomposer.decompose(spec)

        interact_sg = goal.graph.subgoals.get("sg_interact")
        assert interact_sg is not None
        assert interact_sg.result_data is not None
        assert interact_sg.result_data.get("application") == "notepad", (
            "spec.parameters must be in subgoal.result_data so they flow to ExecutionStep.arguments"
        )

    def test_planner_merges_parameters_into_step_arguments(self):
        """AutonomousGoalPlanner must include spec.parameters in ExecutionStep.arguments."""
        spec = GoalSpecification(
            intent="launch_application",
            parameters={"application": "notepad"},
        )
        decomposer = GoalDecomposer()
        planner = AutonomousGoalPlanner(decomposer)
        goal = decomposer.decompose(spec)
        plan = planner.build_plan(goal)

        # Find the step corresponding to sg_interact
        interact_step = next(
            (s for s in plan.steps if s.subgoal_id == "sg_interact"), None
        )
        assert interact_step is not None, "ExecutionStep for sg_interact must exist"
        assert interact_step.arguments.get("application") == "notepad", (
            f"ExecutionStep.arguments must contain application='notepad', got {interact_step.arguments}"
        )
        # action_name must be intent-derived, not a generic placeholder
        assert interact_step.action_name == "launch_application", (
            f"action_name must be 'launch_application', got '{interact_step.action_name}'"
        )

    def test_type_text_parameter_preserved(self):
        """Verify type_text parameter flows through the pipeline."""
        spec = GoalSpecification(
            intent="type_text",
            parameters={"text": "hello world"},
        )
        decomposer = GoalDecomposer()
        planner = AutonomousGoalPlanner(decomposer)
        goal = decomposer.decompose(spec)
        plan = planner.build_plan(goal)

        interact_step = next(
            (s for s in plan.steps if s.subgoal_id == "sg_interact"), None
        )
        assert interact_step is not None
        assert interact_step.arguments.get("text") == "hello world", (
            f"ExecutionStep.arguments must contain text='hello world', got {interact_step.arguments}"
        )

    @pytest.mark.asyncio
    async def test_e2e_parameter_reaches_runtime(self):
        """End-to-end: GoalSpec parameters reach the Runtime action payload."""
        from core.goals import GoalManager
        from core.cognition.models import SharedCognitiveContext

        spec = GoalSpecification(
            intent="launch_application",
            parameters={"application": "notepad"},
        )

        # Build a mock runtime that records what execute() receives
        received_plans = []

        class RecordingRuntime:
            async def start(self): pass
            async def stop(self): pass
            async def shutdown(self): pass
            async def observe(self): return {}
            async def plan(self, goal, obs): return []
            async def execute(self, plan):
                received_plans.append(plan)
                return {"success": True, "actions_executed": len(plan), "results": []}
            async def recover(self, err, ctx): return {}
            def get_runtime_capabilities(self):
                from core.runtime.capability import CapabilityRegistry
                return CapabilityRegistry({"mouse": True, "screenshot": True})
            def get_health(self): return {"state": "healthy"}

        runtime = RecordingRuntime()
        negotiator = CapabilityNegotiator()
        negotiator.register_runtime("desktop", runtime)

        decomposer = GoalDecomposer()
        planner = AutonomousGoalPlanner(decomposer)
        goal = decomposer.decompose(spec)
        goal.plan = planner.build_plan(goal)

        coordinator = CognitiveCoordinator(negotiator=negotiator)

        ctx = SharedCognitiveContext(goal=goal)
        result = await coordinator.run_cognition_loop(ctx)

        # The runtime must have been called with a plan containing the parameters
        assert len(received_plans) > 0, "Runtime execute() was never called"
        all_actions = [action for plan in received_plans for action in plan]
        # Look for our application parameter in the dispatched actions
        found = any(
            action.get("args", {}).get("application") == "notepad"
            or action.get("application") == "notepad"
            for action in all_actions
            if isinstance(action, dict)
        )
        assert found, (
            f"Parameter 'application=notepad' not found in any dispatched action. "
            f"Received plans: {received_plans}"
        )


# ═══════════════════════════════════════════════════════════════════════════
# FIX #4 — LLMRouter as Sole Routing Authority
# ═══════════════════════════════════════════════════════════════════════════

class TestLLMRoutingAuthority:
    """Verify LLMRouter is the exclusive routing/failover authority."""

    @pytest.mark.asyncio
    async def test_llm_service_uses_router(self):
        """LLMService.generate() must route through LLMRouter, not a direct provider."""
        from core.llm.service import LLMService

        router = MagicMock(spec=LLMRouter)
        expected_response = LLMResponse(content="test response", finish_reason=FinishReason.STOP)
        router.chat = AsyncMock(return_value=expected_response)

        model_registry = MagicMock()
        model_registry.get_default_model.return_value = ModelConfig(name="test", provider="test")
        budget_manager = MagicMock()
        budget_manager.check_budget.return_value = True
        telemetry = MagicMock()
        logger = MagicMock()

        service = LLMService(
            router=router,
            model_registry=model_registry,
            budget_manager=budget_manager,
            telemetry=telemetry,
            logger=logger,
        )

        messages = [LLMMessage(role="user", content="hello")]
        response = await service.generate(messages)

        # LLMRouter.chat() must have been called, not a direct provider
        router.chat.assert_called_once()
        assert response.content == "test response"

    @pytest.mark.asyncio
    async def test_failover_owned_by_router(self):
        """Failover must be handled by LLMRouter, not LLMService."""
        from core.llm.service import LLMService
        from core.llm.providers.dummy import DummyProvider, DummyToolMapper

        # Router with two providers: first fails, second succeeds
        router = LLMRouter()
        failing_provider = MagicMock(spec=DummyProvider)
        failing_provider.generate = AsyncMock(side_effect=Exception("provider error"))
        router.register("failing", failing_provider, priority=10)

        succeeding_response = LLMResponse(content="fallback response", finish_reason=FinishReason.STOP)
        succeeding_provider = MagicMock(spec=DummyProvider)
        succeeding_provider.generate = AsyncMock(return_value=succeeding_response)
        router.register("succeeding", succeeding_provider, priority=20)

        model_registry = MagicMock()
        model_registry.get_default_model.return_value = ModelConfig(name="test", provider="test")
        budget_manager = MagicMock()
        budget_manager.check_budget.return_value = True
        telemetry = MagicMock()
        logger = MagicMock()

        service = LLMService(
            router=router,
            model_registry=model_registry,
            budget_manager=budget_manager,
            telemetry=telemetry,
            logger=logger,
        )

        messages = [LLMMessage(role="user", content="hello")]
        response = await service.generate(messages)

        # Router should have failed over to the second provider
        assert response.content == "fallback response"
        assert failing_provider.generate.call_count == 1
        assert succeeding_provider.generate.call_count == 1

    @pytest.mark.asyncio
    async def test_provider_selection_in_one_place(self):
        """Provider selection must happen inside LLMRouter, not LLMService."""
        from core.llm.service import LLMService

        # LLMService should not have its own provider selection logic
        # Verify by checking it has a 'router' attribute, not a 'provider' attribute
        router = MagicMock(spec=LLMRouter)
        router.chat = AsyncMock(return_value=LLMResponse(content="ok", finish_reason=FinishReason.STOP))

        service = LLMService(
            router=router,
            model_registry=MagicMock(get_default_model=lambda: ModelConfig(name="t", provider="t")),
            budget_manager=MagicMock(check_budget=lambda _: True),
            telemetry=MagicMock(),
            logger=MagicMock(),
        )

        assert hasattr(service, "_router"), "LLMService must store router"
        assert not hasattr(service, "_provider"), "LLMService must NOT own a provider (use router)"

    @pytest.mark.asyncio
    async def test_dummy_provider_not_production_when_gemini_configured(self):
        """DummyProvider must not become primary when Gemini env key is configured."""
        from core.llm.module import LLMSystemModule
        from core.di.container import Container
        from core.llm.router import LLMRouter

        # Simulate environment with a Gemini API key
        with patch.dict("os.environ", {"GEMINI_API_KEY": "fake-key-for-test"}):
            # Patch GeminiProvider so it doesn't actually call APIs
            with patch("core.llm.providers.gemini.GeminiProvider") as MockGemini:
                MockGemini.return_value = MagicMock()
                # Create a minimal container for this test
                container = Container()
                from core.di.enums import Lifetime
                # Register minimal stubs needed by LLMSystemModule
                from core.llm.interfaces import IToolSchemaMapper
                from core.llm.providers.dummy import DummyToolMapper
                container.register_instance(IToolSchemaMapper, DummyToolMapper())

                from core.telemetry.interfaces import ITelemetryManager
                container.register_instance(ITelemetryManager, MagicMock())

                from core.logger.interface import ILogger
                container.register_instance(ILogger, MagicMock())

                LLMSystemModule().register(container)
                router = container.resolve(LLMRouter)

                # The first (highest priority) provider must NOT be DummyProvider
                available = router.get_available_providers()
                assert len(available) > 0
                assert available[0].name != "dummy", (
                    f"When Gemini key is configured, 'dummy' must NOT be the primary provider. "
                    f"Got: {[p.name for p in available]}"
                )

    @pytest.mark.asyncio
    async def test_di_registers_llm_router(self):
        """LLMRouter must be registered in the DI container via LLMSystemModule."""
        from core.llm.module import LLMSystemModule
        from core.di.container import Container
        from core.llm.router import LLMRouter
        from core.llm.interfaces import IToolSchemaMapper
        from core.llm.providers.dummy import DummyToolMapper
        from core.telemetry.interfaces import ITelemetryManager
        from core.logger.interface import ILogger

        container = Container()
        container.register_instance(IToolSchemaMapper, DummyToolMapper())
        container.register_instance(ITelemetryManager, MagicMock())
        container.register_instance(ILogger, MagicMock())

        LLMSystemModule().register(container)

        router = container.resolve(LLMRouter)
        assert router is not None
        assert isinstance(router, LLMRouter)
        # DummyProvider must be registered as a fallback (last)
        providers = router.get_available_providers()
        assert any(p.name == "dummy" for p in providers), "DummyProvider must be registered as fallback"

    @pytest.mark.asyncio
    async def test_default_model_registry_prefers_real_provider_over_dummy(self):
        """ModelRegistry default model must prefer real providers (Gemini) and not dummy-v1."""
        from core.llm.module import LLMSystemModule
        from core.di.container import Container
        from core.llm.interfaces import IModelRegistry, IToolSchemaMapper
        from core.llm.providers.dummy import DummyToolMapper
        from core.telemetry.interfaces import ITelemetryManager
        from core.logger.interface import ILogger
        from core.llm.providers.gemini import GeminiProvider

        container = Container()
        container.register_instance(IToolSchemaMapper, DummyToolMapper())
        container.register_instance(ITelemetryManager, MagicMock())
        container.register_instance(ILogger, MagicMock())

        LLMSystemModule().register(container)

        registry = container.resolve(IModelRegistry)
        default_model = registry.get_default_model()

        # Default production model must NOT be dummy
        assert default_model.provider != "dummy", f"Default model provider should not be 'dummy', got '{default_model.provider}'"
        assert default_model.provider == "gemini"
        assert default_model.name == GeminiProvider.DEFAULT_MODEL

        # Dummy model is still registered for explicit test/dev fallback
        dummy_model = registry.get_model("dummy-v1")
        assert dummy_model is not None
        assert dummy_model.provider == "dummy"
