"""
app/persistence/module.py — DI Module for Session Persistence.

Registers ISessionRepository (SQLiteSessionStore) with the DI Container.
Called from core/kernel/kernel.py during _init_container().

The database path is resolved at registration time from core.utils.paths,
so it respects %LOCALAPPDATA%\\Eric on Windows and ~/.config/Eric elsewhere.
Tests override the path by injecting a pre-built SQLiteSessionStore instance
directly (container.register_instance) before calling this module.
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)


class SessionPersistenceModule:
    """
    DI Module: registers ISessionRepository -> SQLiteSessionStore.

    The store is registered as a pre-built instance so that the db_path
    (a runtime value) can be resolved before DI auto-construction.
    The container's lifecycle management will call initialize()/dispose()
    via ILifecycleAware.
    """

    def register(self, container) -> None:
        from core.utils.paths import get_app_data_dir
        from app.persistence.interfaces import ISessionRepository
        from app.persistence.session_store import SQLiteSessionStore

        # Resolve database path under %LOCALAPPDATA%\Eric\sessions\
        sessions_dir = os.path.join(get_app_data_dir(), "sessions")
        db_path = os.path.join(sessions_dir, "sessions.db")

        store = SQLiteSessionStore(db_path)
        # initialize() is called here so the schema exists before any
        # service that depends on ISessionRepository is resolved.
        try:
            store.initialize()
        except Exception as exc:
            logger.error(
                "[SessionPersistenceModule] Failed to initialize SQLiteSessionStore: %s",
                exc,
            )
            raise

        container.register_instance(ISessionRepository, store)
        logger.info(
            "[SessionPersistenceModule] ISessionRepository registered at %s", db_path
        )
