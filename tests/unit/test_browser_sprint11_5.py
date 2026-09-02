import pytest
from core.browser.models import BrowserAction, BrowserWorkflow, BrowserObservation, BrowserIntelligenceLayer
from core.browser.managers.action_queue import BrowserActionQueue
from core.browser.managers.memory_pipeline import BrowserMemoryPipeline
from core.browser.planner import HybridBrowserPlanner
from core.browser.enums import WorkflowState

class MockLogger:
    def info(self, msg): pass
    def debug(self, msg): pass
    def warning(self, msg): pass
    def error(self, msg): pass
    def exception(self, msg): pass

@pytest.mark.asyncio
async def test_action_queue_cancellation():
    logger = MockLogger()
    queue = BrowserActionQueue(logger)
    
    a1 = BrowserAction(name="click1", id="1")
    a2 = BrowserAction(name="type1", id="2", dependencies=["1"])
    
    async def mock_exec(**kwargs):
        pass
        
    await queue.enqueue(a1, mock_exec)
    await queue.enqueue(a2, mock_exec)
    
    queue.cancel_action("1")
    
    # 2 should be automatically cancelled
    assert queue._actions["2"].status == "cancelled"
    
def test_memory_pipeline():
    html = "<html><body><h1>Title</h1><p>Content goes here</p></body></html>"
    pipeline = BrowserMemoryPipeline()
    
    res = pipeline.process(html, metadata={"url": "test.com"})
    
    assert len(res) == 1
    assert res[0]["header"] == "# Title"
    assert "Content goes here" in res[0]["content"]
    assert res[0]["metadata"]["url"] == "test.com"

def test_planner():
    logger = MockLogger()
    planner = HybridBrowserPlanner(logger)
    
    wf = BrowserWorkflow(goal="login")
    obs = BrowserObservation(url="https://github.com/login")
    intelligence = BrowserIntelligenceLayer(observation=obs)
    
    actions = planner.plan(wf, intelligence)
    assert wf.state == WorkflowState.PLANNING
    assert len(actions) == 3
    assert actions[0].name == "type"
