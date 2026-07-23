"""
Agent Runtime Implementation.
"""

import time
from typing import Any

from core.agents.enums import StepType, TaskState
from core.agents.interfaces import ExecutionContext, IAgentRegistry, IAgentRuntime
from core.agents.models import Step, Task
from core.config.schemas import SystemConfig
from core.events.event import Event
from core.events.event_bus import EventBus
from core.logger.interface import ILogger
from core.memory.interfaces import IMemoryService
from core.tools.interfaces import IToolExecutor


class AgentRuntime(IAgentRuntime):
    """
    Executes tasks using the registered agents and the ReAct loop.
    Acts as an Orchestrator.
    """

    def __init__(
        self,
        registry: IAgentRegistry,
        logger: ILogger,
        event_bus: EventBus,
        config: SystemConfig,
        memory: IMemoryService,
        tool_executor: IToolExecutor,
    ) -> None:
        self._registry = registry
        self._logger = logger
        self._event_bus = event_bus
        self._config = config
        self._memory = memory
        self._tool_executor = tool_executor
        
        self._tasks: dict[str, Task] = {}
        self._queue: list[str] = []

    def submit_task(self, task: Task) -> None:
        """Submit a task to the runtime."""
        if task.id in self._tasks:
            raise ValueError(f"Task with ID {task.id} already exists.")
            
        self._tasks[task.id] = task
        self._queue.append(task.id)
        
        self._logger.info(f"[AgentRuntime] Task {task.id} submitted: {task.goal}")
        
        self._event_bus.publish_sync(
            Event.create(
                name="task.created",
                source="agent_runtime",
                payload={"task_id": task.id, "goal": task.goal}
            )
        )

    def cancel_task(self, task_id: str) -> None:
        """Cancel a pending or running task."""
        task = self._tasks.get(task_id)
        if not task:
            return
            
        if task.state in (TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED):
            return
            
        task.state = TaskState.CANCELLED
        self._logger.info(f"[AgentRuntime] Task {task_id} cancelled.")
        self._event_bus.publish_sync(
            Event.create(
                name="task.cancelled",
                source="agent_runtime",
                payload={"task_id": task_id}
            )
        )

    def get_task(self, task_id: str) -> Task | None:
        return self._tasks.get(task_id)

    def process_queue(self) -> None:
        """
        Process all tasks in the queue synchronously.
        (In a real asynchronous OS, this would be an event loop or worker thread).
        """
        while self._queue:
            task_id = self._queue.pop(0)
            self._execute_task(task_id)

    def _execute_task(self, task_id: str) -> None:
        """Execute a single task through the ReAct loop."""
        task = self._tasks.get(task_id)
        if not task or task.state != TaskState.PENDING:
            return

        # Assign a default agent if none is specified
        agent_name = task.agent_name or "dummy_agent"
        agent = self._registry.get_agent(agent_name)
        
        if not agent:
            self._fail_task(task, f"Agent '{agent_name}' not found.")
            return

        task.state = TaskState.RUNNING
        self._event_bus.publish_sync(
            Event.create(
                name="task.started",
                source="agent_runtime",
                payload={"task_id": task.id, "agent": agent.name}
            )
        )

        context = ExecutionContext(
            task=task,
            logger=self._logger,
            event_bus=self._event_bus,
            config=self._config,
            memory=self._memory,
            tool_executor=self._tool_executor,
        )

        self._logger.info(f"[AgentRuntime] Starting execution of Task {task.id} with Agent '{agent.name}'")

        try:
            # ReAct Loop
            while task.state == TaskState.RUNNING:
                # 1. Plan (Thought)
                thought = agent.plan(context)
                if thought is None:
                    # Agent finished
                    task.state = TaskState.COMPLETED
                    break
                
                self._record_step(task, StepType.THOUGHT, thought)
                
                # Check for cancellation
                if task.state == TaskState.CANCELLED:
                    break

                # 2. Act
                action = agent.act(context, thought)
                self._record_step(task, StepType.ACTION, str(action))
                
                if task.state == TaskState.CANCELLED:
                    break

                # 3. Observe
                observation = agent.observe(context, action)
                self._record_step(task, StepType.OBSERVATION, observation)

            if task.state == TaskState.COMPLETED:
                self._logger.info(f"[AgentRuntime] Task {task.id} completed successfully.")
                self._event_bus.publish_sync(
                    Event.create(
                        name="task.completed",
                        source="agent_runtime",
                        payload={"task_id": task.id, "result": task.result}
                    )
                )

        except Exception as e:
            self._logger.exception(f"[AgentRuntime] Error executing Task {task.id}: {e}")
            self._fail_task(task, str(e))

    def _record_step(self, task: Task, step_type: StepType, content: str) -> None:
        """Record a step in the task timeline and emit an event."""
        step = Step(type=step_type, content=content)
        task.steps.append(step)
        
        self._event_bus.publish_sync(
            Event.create(
                name="task.step_added",
                source="agent_runtime",
                payload={
                    "task_id": task.id,
                    "step_type": step_type.value,
                    "content": content
                }
            )
        )

    def _fail_task(self, task: Task, reason: str) -> None:
        task.state = TaskState.FAILED
        task.result = reason
        self._logger.error(f"[AgentRuntime] Task {task.id} failed: {reason}")
        self._event_bus.publish_sync(
            Event.create(
                name="task.failed",
                source="agent_runtime",
                payload={"task_id": task.id, "reason": reason}
            )
        )
