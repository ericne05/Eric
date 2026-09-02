"""
Builders for Context and Prompts.
"""

from typing import Any, Dict, List, TYPE_CHECKING

from core.agents.interfaces import ExecutionContext
from core.llm.enums import MessageRole
from core.llm.interfaces import IContextAssembler, IPromptBuilder
from core.llm.models import LLMMessage, ContextData

if TYPE_CHECKING:
    from core.memory.interface import IMemoryService


class ContextAssembler(IContextAssembler):
    """
    Assembles system state, current task, and relevant memories into a data object.
    """
    def __init__(self, memory_service: "IMemoryService" = None):
        self._memory = memory_service

    def assemble(self, context: ExecutionContext) -> ContextData:
        memories = []
        if self._memory:
            # Fake retrieval logic for demonstration
            memories = self._memory.get_recent_fragments()

        return ContextData(
            task_id=context.task.id,
            goal=context.task.goal,
            state=context.task.state.value,
            memories=memories
        )


class ReActPromptBuilder(IPromptBuilder):
    """
    Builds the ReAct LLMMessages array.
    """
    def build_prompt(self, context_data: ContextData, history: List[LLMMessage]) -> List[LLMMessage]:
        messages = []
        
        # System Message (Instruction)
        system_instruction = (
            "You are Eric, an autonomous AI assistant.\n"
            f"Your current task is: {context_data.goal}\n"
            "Use the provided tools to solve the task. If you have enough information, "
            "respond directly with the final answer."
        )
        
        # Inject Memory Fragments
        if context_data.memories:
            system_instruction += "\n\nRelevant Memories:\n" + "\n".join(context_data.memories)
        
        messages.append(LLMMessage(role=MessageRole.SYSTEM, content=system_instruction))
        
        # Append all previous conversation history
        messages.extend(history)
        
        return messages
