"""
Manual test for Agent Runtime.
"""

from core.agents.models import Task
from core.agents.interfaces import IAgentRuntime
from core.kernel.bootstrap import bootstrap


def run():
    print("Booting Eric Kernel for Agent Runtime Test...")
    kernel = bootstrap()
    
    runtime = kernel._container.resolve(IAgentRuntime)
    
    print("\n--- Submitting Task ---")
    task = Task(id="test_task_123", goal="Open Son Tung song on YouTube", agent_name="react_agent")
    runtime.submit_task(task)
    
    print("\n--- Processing Queue ---")
    runtime.process_queue()
    
    print("\n--- Task Timeline ---")
    retrieved_task = runtime.get_task("test_task_123")
    print(f"Goal: {retrieved_task.goal}")
    print(f"State: {retrieved_task.state.value}")
    print(f"Result: {retrieved_task.result}")
    print("Steps:")
    for step in retrieved_task.steps:
        print(f"  [{step.timestamp.strftime('%H:%M:%S')}] {step.type.value.upper()}: {step.content}")


if __name__ == "__main__":
    run()
