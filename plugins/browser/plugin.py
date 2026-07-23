"""
Stateless Browser Plugin.
"""
from typing import Any, Dict, Type

from core.browser.enums import SelectorType
from core.browser.interfaces import IBrowserRuntime
from core.browser.models import BrowserSelector
from core.logger.interface import ILogger
from core.plugins.interfaces import IPlugin
from core.tools.interfaces import ITool, ToolContext, ToolResult
from core.tools.schema import ToolSchema, ToolParameter


class BrowserOpenTool(ITool):
    def __init__(self, runtime: IBrowserRuntime):
        self._runtime = runtime

    @property
    def schema(self) -> ToolSchema:
        return ToolSchema(
            name="browser_open",
            description="Opens a URL in a new browser tab.",
            parameters=[
                ToolParameter(name="url", type="string", description="The URL to open", required=True)
            ]
        )

    async def execute_async(self, context: ToolContext, **kwargs) -> ToolResult:
        url = kwargs.get("url")
        tab = await self._runtime.session_manager.create_tab(url)
        return ToolResult(success=True, data={"tab_id": tab.id, "url": tab.url})


class BrowserClickTool(ITool):
    def __init__(self, runtime: IBrowserRuntime):
        self._runtime = runtime

    @property
    def schema(self) -> ToolSchema:
        return ToolSchema(
            name="browser_click",
            description="Clicks on an element in the current tab.",
            parameters=[
                ToolParameter(name="selector", type="string", description="CSS or XPath selector", required=True),
                ToolParameter(name="type", type="string", description="Selector type (css, xpath)", required=False)
            ]
        )

    async def execute_async(self, context: ToolContext, **kwargs) -> ToolResult:
        selector_str = kwargs.get("selector")
        sel_type = kwargs.get("type", "css")
        
        stype = SelectorType.CSS if sel_type == "css" else SelectorType.XPATH
        selector = BrowserSelector(type=stype, value=selector_str)
        
        res = await self._runtime.dom.click(selector)
        return ToolResult(success=res.success, error=res.error)


class BrowserExtractTextTool(ITool):
    def __init__(self, runtime: IBrowserRuntime):
        self._runtime = runtime

    @property
    def schema(self) -> ToolSchema:
        return ToolSchema(
            name="browser_extract_text",
            description="Extracts all visible text from the current page.",
            parameters=[]
        )

    async def execute_async(self, context: ToolContext, **kwargs) -> ToolResult:
        res = await self._runtime.dom.extract_text()
        if res.success:
            return ToolResult(success=True, data={"text": res.data})
        return ToolResult(success=False, error=res.error)


class BrowserPlugin(IPlugin):
    """
    Plugin that registers all browser-related stateless tools.
    """
    def __init__(self, runtime: IBrowserRuntime, logger: ILogger):
        self._runtime = runtime
        self._logger = logger
        self._tools = [
            BrowserOpenTool(runtime),
            BrowserClickTool(runtime),
            BrowserExtractTextTool(runtime)
        ]

    @property
    def name(self) -> str:
        return "browser"

    @property
    def version(self) -> str:
        return "1.0.0"

    def initialize(self) -> None:
        self._logger.info("[BrowserPlugin] Initializing stateless browser tools.")
        # Runtime is typically started asynchronously elsewhere, e.g. at system boot.

    def shutdown(self) -> None:
        pass

    def get_tools(self) -> list[ITool]:
        return self._tools
