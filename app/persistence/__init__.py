"""
app/persistence — Durable Session Persistence Package.

Public API:
    ISessionRepository  — abstract repository contract
    SQLiteSessionStore  — SQLite-backed implementation
"""

from app.persistence.interfaces import ISessionRepository
from app.persistence.session_store import SQLiteSessionStore

__all__ = [
    "ISessionRepository",
    "SQLiteSessionStore",
]
