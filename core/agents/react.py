from core.agents.models import CancellationToken
"""
ReAct Agent using the new LLM Subsystem.
"""

import asyncio
from typing import Any

from core.agents.enums import TaskState
from core.agents.interfaces import ExecutionContext, IAgent
from core.llm.enums import FinishReason, MessageRole
from core.llm.interfaces import (
    IContextAssembler,
    IConversationManager,
    ILLMService,
    IPromptBuilder
)
from core.llm.models import LLMMessage
from core.tools.enums import ToolStatus
from core.tools.interfaces import IToolRegistry


class ReActAgent(IAgent):
    """
    An agent that implements the ReAct loop using the ILLMService.
    """

    def __init__(
        self,
        llm_service: ILLMService,
        prompt_builder: IPromptBuilder,
        context_assembler: IContextAssembler,
        conversation_manager: IConversationManager,
        tool_registry: IToolRegistry,
        max_reasoning_steps: int = 10,
        max_tool_calls_per_step: int = 5,
    ):
        self._llm = llm_service
        self._builder = prompt_builder
        self._assembler = context_assembler
        self._convo = conversation_manager
        self._registry = tool_registry
        
        self.max_reasoning_steps = max_reasoning_steps
        self.max_tool_calls_per_step = max_tool_calls_per_step

    @property
    def name(self) -> str:
        return "react_agent"

    def plan(self, context: ExecutionContext) -> Any:
        """
        Uses LLM to decide the next step (Thought or Tool Call).
        Since plan/act/observe in IAgent are sync currently, we use asyncio.run
        to bridge the async LLM Service. In a fully async system, these would be async.
        """
        # If task state is completed, don't plan
        if context.task.state == TaskState.COMPLETED:
            return None
            
        thread_id = context.task.id
        
        # 1. Assemble context
        context_data = self._assembler.assemble(context)
        
        # 2. Get tools
        tools = self._registry.get_all_schemas()
        
        # 3. Build prompt
        history = self._convo.get_history(thread_id)
        messages = self._builder.build_prompt(context_data, history)
        
        # 4. Generate
        cancellation = CancellationToken()
        
        # Run async generation
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import nest_asyncio
                nest_asyncio.apply()
        except RuntimeError:
            pass
            
        response = asyncio.run(self._llm.generate(
            messages=messages,
            tools=tools,
            cancellation_token=cancellation,
            stream=False
        ))
        
        # 5. Handle response
        if response.finish_reason == FinishReason.TOOL_CALLS and response.tool_calls:
            # Save Assistant message with tool calls to history
            self._convo.append_message(
                thread_id,
                LLMMessage(
                    role=MessageRole.ASSISTANT,
                    content=response.content,
                    tool_calls=response.tool_calls
                )
            )
            # Return the first tool call for the act phase
            # In a full implementation, act could handle parallel tool calls
            return response.tool_calls[0]
            
        else:
            # Text response, task is complete
            self._convo.append_message(
                thread_id,
                LLMMessage(
                    role=MessageRole.ASSISTANT,
                    content=response.content
                )
            )
            # Save result and mark finished by returning None for next plan
            context.task.result = response.content
            return None

    def act(self, context: ExecutionContext, plan_result: Any) -> Any:
        """
        Executes the tool requested by the LLM.
        plan_result is an LLMToolCall.
        """
        if not hasattr(plan_result, "name"):
            return None
            
        fqn = plan_result.name
        args = plan_result.arguments
        
        # Call tool via executor
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import nest_asyncio
                nest_asyncio.apply()
        except RuntimeError:
            pass
            
        result = asyncio.run(context.tool_executor.execute_tool(
            context, 
            fqn, 
            cancellation_token=context.task.cancellation_token, 
            **args
        ))
        
        return {
            "tool_call_id": plan_result.id,
            "name": fqn,
            "result": result
        }

    def observe(self, context: ExecutionContext, action_result: Any) -> str:
        """
        Record the tool result back into the Conversation Manager.
        """
        if not action_result or not isinstance(action_result, dict):
            return "No valid action result."
            
        thread_id = context.task.id
        tool_call_id = action_result["tool_call_id"]
        tool_name = action_result["name"]
        tool_result = action_result["result"]
        
        # Convert result to string
        if tool_result.status == ToolStatus.SUCCESS:
            data = str(tool_result.data)
        else:
            data = f"Error: {tool_result.error_message}"
            
        # Append to history
        self._convo.append_message(
            thread_id,
            LLMMessage(
                role=MessageRole.TOOL,
                content=data,
                name=tool_name,
                tool_call_id=tool_call_id
            )
        )
        
        return f"Tool {tool_name} returned: {data}"
