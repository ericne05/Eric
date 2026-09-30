"""
core/approval/module.py — Approval System DI Module.

Registers IApprovalPolicy and IApprovalManager into the Kernel DI Container.
"""

from typing import TYPE_CHECKING

from core.di.interfaces import IDependencyModule

if TYPE_CHECKING:
    from core.di.container import Container


class ApprovalModule(IDependencyModule):
    """
    Registers the Approval Subsystem in the DI Container.
    """

    def register(self, container: "Container") -> None:
        from core.approval.interfaces import IApprovalManager, IApprovalPolicy
        from core.approval.manager import ApprovalManager
        from core.approval.policy import DefaultApprovalPolicy
        from core.events.event_bus import EventBus

        container.add_singleton(IApprovalPolicy, DefaultApprovalPolicy)

        def _manager_factory(c):
            bus = c.resolve(EventBus) if c.has(EventBus) else None
            policy = c.resolve(IApprovalPolicy) if c.has(IApprovalPolicy) else None
            return ApprovalManager(policy=policy, event_bus=bus)

        container.add_singleton(IApprovalManager, _manager_factory)
        container.add_singleton(ApprovalManager, _manager_factory)
