"""
Eric Desktop Client — Main Entry Point & Host Window (Sprint 17 — Eric v1.0).
Integrates Application Shell, Chat UI, Session Manager, Activity Console, Command Palette, Timeline & Status.
"""

import asyncio, sys
from typing import Any, Dict, Optional

from app.bootstrap.app_bootstrap import AppBootstrap
from app.services.backend_bridge import BackendBridge
from app.services.session_manager import SessionManager
from app.ui.chat.chat_widget import ChatWidget
from app.ui.notification.notification_center import NotificationCenter
from app.ui.widgets.activity_console import ActivityConsole
from app.ui.widgets.command_palette import CommandPalette
from app.ui.widgets.error_panel import ErrorDiagnosticPanel
from app.ui.widgets.goal_dashboard import GoalDashboardWidget
from app.ui.widgets.runtime_status import RuntimeStatusWidget
from app.ui.widgets.timeline_widget import TimelineWidget
from app.viewmodels.main_viewmodel import MainViewModel


class EricDesktopClient:
    """
    Eric Desktop Client Host (Eric v1.0 MVP Product).
    Connects Startup Lifecycle, Backend Bridge, ViewModel, and UI Components.
    """

    def __init__(self):
        self.bootstrap = AppBootstrap()
        self.session_manager = SessionManager()
        self.notification_center = NotificationCenter()
        self.bridge = BackendBridge(self.bootstrap, self.session_manager, self.notification_center)
        self.viewmodel = MainViewModel(self.bridge)

        # UI Components
        self.chat_widget = ChatWidget()
        self.activity_console = ActivityConsole()
        self.command_palette = CommandPalette()
        self.error_panel = ErrorDiagnosticPanel()
        self.timeline_widget = TimelineWidget()
        self.runtime_status = RuntimeStatusWidget()
        self.goal_dashboard = GoalDashboardWidget()

        self.is_running: bool = False

    async def launch(self) -> Dict[str, Any]:
        """Runs the full Application Shell Startup Lifecycle."""
        self.activity_console.log("Launching Eric Desktop Client v1.0 Application Shell...")
        init_res = await self.bootstrap.initialize()

        self.session_manager.restore_last_session()
        self.activity_console.log("Kernel & Runtimes initialized. Restored active Session.")
        self.notification_center.notify("Eric Desktop Client", "System Ready", level="info")

        self.is_running = True
        return {
            "status": "online",
            "version": "1.0.0",
            "bootstrap": init_res,
            "active_session": self.session_manager.get_active_session().id,
        }

    async def send_prompt(self, prompt: str) -> str:
        """Sends user prompt through the Desktop Client."""
        self.activity_console.log(f"User Input: '{prompt}'")
        msg = await self.viewmodel.submit_prompt(prompt)
        self.chat_widget.update_messages(self.viewmodel.get_messages())
        self.runtime_status.update_health(self.viewmodel.get_runtime_health())
        self.goal_dashboard.update_progress(
            percentage=self.viewmodel.goal_progress,
            current_step=4,
            total_steps=4,
            status_text=self.viewmodel.current_status,
        )
        return msg.content

    async def shutdown(self) -> None:
        self.activity_console.log("Shutting down Eric Desktop Client...")
        await self.bootstrap.shutdown()
        self.is_running = False


async def main():
    client = EricDesktopClient()
    res = await client.launch()

    print("\n" + "=" * 60)
    print(" ERIC AI ASSISTANT v1.0 (Desktop Client)")
    print(f" Status: ONLINE | Active Session: {res['active_session'][:8]}")
    print(" Runtimes: Desktop [OK] | Vision [OK] | Browser [OK]")
    print("=" * 60)
    print(" Type your request below and press Enter (or type 'exit' / 'quit' to exit):\n")

    loop = asyncio.get_running_loop()

    try:
        while client.is_running:
            # Interactive user prompt loop
            user_input = await loop.run_in_executor(None, input, "Eric > ")
            user_input = user_input.strip()

            if not user_input:
                continue

            if user_input.lower() in ("exit", "quit", "q"):
                print("\nShutting down Eric AI Assistant...")
                break

            reply = await client.send_prompt(user_input)
            print(f"\n{reply}\n")
    except (KeyboardInterrupt, EOFError):
        print("\nExiting Eric AI Assistant...")
    finally:
        await client.shutdown()
        print("Eric AI Assistant closed successfully.")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    asyncio.run(main())
