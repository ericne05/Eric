"""
Unit tests for core.logger (ILogger, LoggerManager, factory, and Kernel integration).
"""

import logging
from pathlib import Path

from core.kernel.kernel import Kernel
from core.logger import ILogger, LoggerManager, setup_logger


class TestLoggerModule:
    """Unit tests for Logger module."""

    def test_logger_setup_returns_ilogger_instance(self, tmp_path: Path) -> None:
        log_file = tmp_path / "test.log"
        config = {
            "handlers": {
                "console": {"level": "DEBUG"},
                "file": {
                    "filename": str(log_file),
                    "level": "INFO",
                    "maxBytes": 1000,
                    "backupCount": 1,
                },
            }
        }
        logger = setup_logger(config)
        assert isinstance(logger, ILogger)
        assert isinstance(logger, LoggerManager)
        logger.shutdown()

    def test_logger_file_output(self, tmp_path: Path) -> None:
        log_file = tmp_path / "test_output.log"
        config = {
            "handlers": {
                "console": {"level": "DEBUG"},
                "file": {
                    "filename": str(log_file),
                    "level": "INFO",
                    "maxBytes": 1048576,
                    "backupCount": 1,
                },
            }
        }
        logger = setup_logger(config)

        test_message = "Test log message for file verification"
        logger.info(test_message)

        # Allow loguru enqueue flush
        logger.shutdown()

        assert log_file.exists()
        content = log_file.read_text(encoding="utf8")
        assert test_message in content

    def test_structured_logging_bind(self, tmp_path: Path) -> None:
        log_file = tmp_path / "test_bind.log"
        config = {
            "handlers": {
                "file": {
                    "filename": str(log_file),
                    "level": "DEBUG",
                }
            }
        }
        logger = setup_logger(config)
        bound_logger = logger.bind(
            module="test_mod", correlation_id="12345", agent="browser-agent"
        )

        assert isinstance(bound_logger, ILogger)
        bound_logger.info("Action dispatched")

        logger.shutdown()
        assert log_file.exists()
        content = log_file.read_text(encoding="utf8")
        assert "Action dispatched" in content

    def test_intercept_standard_logging(self, tmp_path: Path) -> None:
        log_file = tmp_path / "test_intercept.log"
        config = {
            "handlers": {
                "file": {
                    "filename": str(log_file),
                    "level": "INFO",
                }
            }
        }
        logger = setup_logger(config)

        # Emit standard python logging message
        std_logger = logging.getLogger("third_party_lib")
        std_logger.info("Message from standard python logging")

        logger.shutdown()
        assert log_file.exists()
        content = log_file.read_text(encoding="utf8")
        assert "Message from standard python logging" in content


class TestKernelLoggerIntegration:
    """Verify Kernel integrates cleanly with LoggerManager / ILogger."""

    def test_kernel_initializes_logger_on_boot(self, tmp_path: Path) -> None:
        log_file = tmp_path / "kernel_boot.log"
        config = {
            "logging": {
                "handlers": {
                    "file": {
                        "filename": str(log_file),
                        "level": "DEBUG",
                    }
                }
            }
        }

        kernel = Kernel(config=config)
        assert kernel.logger is None

        kernel.boot()
        assert kernel.logger is not None
        assert isinstance(kernel.logger, ILogger)

        kernel.shutdown()
        assert kernel.logger is None
