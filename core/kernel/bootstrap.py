"""
Eric Bootstrap — System initialization entry point.

Responsibilities:
    1. Load environment variables from .env
    2. Load all YAML configuration files from configs/
    3. Resolve ${ENV_VAR} placeholders in config values
    4. Create Kernel instance with loaded config
    5. Boot the Kernel

Separated from Kernel so that:
    - Kernel stays testable (inject mock config directly).
    - Bootstrap can be swapped for different environments (test, prod).
    - Single Responsibility: Bootstrap = load data, Kernel = orchestrate.
"""

import os
from pathlib import Path

from dotenv import load_dotenv
import yaml

from core.kernel.kernel import Kernel
from core.config import ConfigLoader, SystemConfig


# Project root — two levels up from this file (core/kernel/bootstrap.py)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def load_env(project_root: Path | None = None) -> None:
    """
    Load environment variables from .env file if it exists.

    Args:
        project_root: Path to project root. Defaults to auto-detected.
    """
    root = project_root or PROJECT_ROOT
    env_path = root / ".env"

    if env_path.exists():
        load_dotenv(env_path)
        print(f"[Bootstrap] Loaded .env from {env_path}")
    else:
        print("[Bootstrap] No .env file found, using system environment.")


def bootstrap(
    project_root: Path | None = None,
    config_dir: Path | None = None,
) -> Kernel:
    """
    Full system bootstrap sequence.

    Args:
        project_root: Optional override for project root path.
        config_dir:   Optional override for config directory path.

    Returns:
        A fully booted Kernel instance.
    """
    print("=" * 50)
    print("  Eric — Personal AI Agent OS")
    print("  Starting up...")
    print("=" * 50)

    # 1. Load environment variables
    load_env(project_root)

    # 2. Load YAML configs via ConfigService pipeline
    cfg_dir = config_dir or (project_root or PROJECT_ROOT) / "configs"
    loader = ConfigLoader()
    configs = loader.load_from_dir(cfg_dir)

    # 3. Create Kernel
    kernel = Kernel(config=configs)

    # 4. Boot
    kernel.boot()

    return kernel
