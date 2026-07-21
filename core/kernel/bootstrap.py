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


def load_configs(config_dir: Path | None = None) -> dict:
    """
    Load all YAML configuration files from a directory.

    Args:
        config_dir: Path to config directory.
                    Defaults to PROJECT_ROOT / "configs".

    Returns:
        Dictionary keyed by config name (filename without .yaml),
        values are parsed YAML content.
    """
    if config_dir is None:
        config_dir = PROJECT_ROOT / "configs"

    configs: dict = {}

    if not config_dir.exists():
        print(f"[Bootstrap] Warning: Config directory not found: {config_dir}")
        return configs

    for yaml_file in sorted(config_dir.glob("*.yaml")):
        name = yaml_file.stem
        try:
            with open(yaml_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                configs[name] = data if data else {}
        except yaml.YAMLError as e:
            print(f"[Bootstrap] Error parsing {yaml_file.name}: {e}")
        except OSError as e:
            print(f"[Bootstrap] Error reading {yaml_file.name}: {e}")

    loaded = ", ".join(configs.keys())
    print(f"[Bootstrap] Loaded configs: {loaded}")

    return configs


def resolve_env_vars(obj):
    """
    Recursively resolve ${ENV_VAR} placeholders in config values
    from the current environment.

    Unresolved placeholders are left as-is.
    """
    if isinstance(obj, dict):
        return {k: resolve_env_vars(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [resolve_env_vars(item) for item in obj]
    if isinstance(obj, str) and obj.startswith("${") and obj.endswith("}"):
        env_key = obj[2:-1]
        return os.environ.get(env_key, obj)
    return obj


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

    # 2. Load YAML configs
    configs = load_configs(config_dir)

    # 3. Resolve ${ENV_VAR} placeholders
    configs = resolve_env_vars(configs)

    # 4. Create Kernel
    kernel = Kernel(config=configs)

    # 5. Boot
    kernel.boot()

    return kernel
