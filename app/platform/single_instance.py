"""
Single Instance Ownership Implementations (app/platform/single_instance.py).

Provides:
- WindowsSingleInstanceLock: Production Windows implementation using Win32 Named Mutex.
- FileSingleInstanceLock: Cross-platform fallback using file lock.
- MockSingleInstanceLock: Deterministic in-memory lock for fast unit testing.
"""

import ctypes
from ctypes import wintypes
import logging
import os
import sys
from typing import Optional

from app.platform.interfaces import ISingleInstanceLock
from core.utils.paths import get_app_data_dir

logger = logging.getLogger(__name__)

ERROR_ALREADY_EXISTS = 183


class WindowsSingleInstanceLock(ISingleInstanceLock):
    """
    Windows-native single instance enforcement using a Win32 Named Mutex.

    Safe, fast, and does not leave stale lockfiles if the application terminates unexpectedly.
    """

    DEFAULT_MUTEX_NAME = "Local\\EricDesktopAssistant_SingleInstance_Mutex"

    def __init__(self, mutex_name: Optional[str] = None):
        self._mutex_name = mutex_name or self.DEFAULT_MUTEX_NAME
        self._handle: Optional[wintypes.HANDLE] = None
        self._acquired: bool = False

    def acquire(self) -> bool:
        """
        Attempt to create/acquire the named mutex.

        Returns True if this is the first instance (mutex created cleanly).
        Returns False if another instance already owns the mutex (ERROR_ALREADY_EXISTS).
        """
        if self._acquired:
            return True

        if sys.platform != "win32":
            logger.debug("[WindowsSingleInstanceLock] Non-Windows OS detected; bypassing Win32 mutex.")
            self._acquired = True
            return True

        try:
            kernel32 = ctypes.windll.kernel32
            kernel32.CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
            kernel32.CreateMutexW.restype = wintypes.HANDLE

            handle = kernel32.CreateMutexW(None, True, self._mutex_name)
            last_error = kernel32.GetLastError()

            if not handle:
                logger.warning(f"[WindowsSingleInstanceLock] Failed to create mutex '{self._mutex_name}', error: {last_error}")
                return False

            if last_error == ERROR_ALREADY_EXISTS:
                logger.info(f"[WindowsSingleInstanceLock] Another instance is already running (mutex '{self._mutex_name}' exists).")
                kernel32.CloseHandle(handle)
                return False

            self._handle = handle
            self._acquired = True
            logger.info(f"[WindowsSingleInstanceLock] Acquired single-instance mutex '{self._mutex_name}'.")
            return True
        except Exception as e:
            logger.error(f"[WindowsSingleInstanceLock] Error acquiring mutex: {e}", exc_info=True)
            return False

    def release(self) -> None:
        """
        Release ownership of the named mutex and close the Win32 handle.
        Safe for duplicate calls (idempotent).
        """
        if not self._acquired:
            return

        if self._handle and sys.platform == "win32":
            try:
                ctypes.windll.kernel32.CloseHandle(self._handle)
                logger.info(f"[WindowsSingleInstanceLock] Released single-instance mutex '{self._mutex_name}'.")
            except Exception as e:
                logger.warning(f"[WindowsSingleInstanceLock] Error closing mutex handle: {e}")
            finally:
                self._handle = None

        self._acquired = False

    @property
    def is_locked(self) -> bool:
        return self._acquired


class FileSingleInstanceLock(ISingleInstanceLock):
    """
    Cross-platform fallback single-instance lock using a lockfile in the application data directory.
    """

    def __init__(self, lock_file_path: Optional[str] = None):
        self._lock_file = lock_file_path or os.path.join(get_app_data_dir(), "eric.lock")
        self._file_handle = None
        self._acquired = False

    def acquire(self) -> bool:
        if self._acquired:
            return True

        try:
            os.makedirs(os.path.dirname(self._lock_file), exist_ok=True)
            # Try atomic exclusive open
            flags = os.O_CREAT | os.O_EXCL | os.O_RDWR
            self._file_handle = os.open(self._lock_file, flags)
            # Write current PID
            os.write(self._file_handle, str(os.getpid()).encode())
            self._acquired = True
            return True
        except FileExistsError:
            # Check if stale PID
            return False
        except Exception as e:
            logger.warning(f"[FileSingleInstanceLock] Error creating lockfile: {e}")
            return False

    def release(self) -> None:
        if not self._acquired:
            return

        try:
            if self._file_handle is not None:
                os.close(self._file_handle)
                self._file_handle = None
            if os.path.exists(self._lock_file):
                os.remove(self._lock_file)
        except Exception as e:
            logger.warning(f"[FileSingleInstanceLock] Error releasing lockfile: {e}")
        finally:
            self._acquired = False

    @property
    def is_locked(self) -> bool:
        return self._acquired


class MockSingleInstanceLock(ISingleInstanceLock):
    """
    In-memory mock for deterministic unit testing.
    """

    def __init__(self, initially_locked: bool = False, fail_on_acquire: bool = False):
        self._acquired: bool = initially_locked
        self._fail_on_acquire: bool = fail_on_acquire
        self.acquire_call_count: int = 0
        self.release_call_count: int = 0

    def acquire(self) -> bool:
        self.acquire_call_count += 1
        if self._fail_on_acquire or self._acquired:
            return False
        self._acquired = True
        return True

    def release(self) -> None:
        self.release_call_count += 1
        self._acquired = False

    @property
    def is_locked(self) -> bool:
        return self._acquired
