"""
Unit tests for the Core Configuration System (Architecture 2.0).
"""

import os
import json
from pathlib import Path
from dataclasses import dataclass, FrozenInstanceError
import pytest

from core.config.exceptions import (
    ConfigError,
    SchemaValidationError,
    UnknownSchemaError,
)
from core.config.registry import ConfigRegistry
from core.config.schemas import (
    AppConfig,
    SystemConfig,
    BrowserConfig,
    BaseSchema,
)
from core.config.resolvers import EnvResolver
from core.config.parsers import YAMLParser, JSONParser
from core.config.service import ConfigService


@pytest.fixture(autouse=True)
def clean_env():
    """Ensure environment is clean before each test."""
    original_env = os.environ.copy()
    yield
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def temp_config_dir(tmp_path):
    config_dir = tmp_path / "configs"
    config_dir.mkdir()
    return config_dir


# ── Registry Tests ────────────────────────────────────────────────────────
def test_config_registry_register_and_get():
    ConfigRegistry.clear()
    ConfigRegistry.register("test_app", AppConfig)
    assert ConfigRegistry.has("test_app")
    assert ConfigRegistry.get("test_app") is AppConfig

def test_unknown_schema_handling():
    ConfigRegistry.clear()
    with pytest.raises(UnknownSchemaError):
        ConfigRegistry.get("non_existent")


# ── Resolver Tests ────────────────────────────────────────────────────────
def test_env_resolution_with_value():
    os.environ["TEST_VAR"] = "hello_world"
    assert EnvResolver.resolve("${TEST_VAR}") == "hello_world"

def test_env_resolution_with_default_fallback():
    # TEST_VAR_2 is NOT set
    assert EnvResolver.resolve("${TEST_VAR_2:fallback_value}") == "fallback_value"

def test_env_resolution_missing_no_default():
    # If no default and no env var, returns placeholder string
    assert EnvResolver.resolve("${MISSING_VAR}") == "${MISSING_VAR}"

def test_env_resolution_recursive_dict_list():
    os.environ["NESTED_ENV"] = "resolved"
    data = {
        "key1": ["${NESTED_ENV}", "static"],
        "key2": {"sub": "${NESTED_ENV:default}"}
    }
    resolved = EnvResolver.resolve(data)
    assert resolved["key1"][0] == "resolved"
    assert resolved["key1"][1] == "static"
    assert resolved["key2"]["sub"] == "resolved"


# ── Schema Validation & Immutability Tests ────────────────────────────────
def test_default_schema_instantiation():
    sys_cfg = SystemConfig()
    assert sys_cfg.app.name == "Eric"
    assert sys_cfg.browser.provider == "playwright"
    assert sys_cfg.llm.default_provider == "gemini"

def test_schema_validation_success():
    app = AppConfig(environment="staging")
    app.validate()  # Should not raise

def test_schema_validation_failure_raises_schema_validation_error():
    app = AppConfig(environment="invalid_env")
    with pytest.raises(SchemaValidationError):
        app.validate()

    browser = BrowserConfig(viewport={"width": 0, "height": 800})
    with pytest.raises(SchemaValidationError):
        browser.validate()

def test_immutable_frozen_dataclass_raises_error_on_mutation():
    app = AppConfig()
    with pytest.raises(FrozenInstanceError):
        app.name = "New Name"

def test_to_dict_and_from_dict_roundtrip():
    original = AppConfig(name="CustomApp", environment="production")
    data_dict = original.to_dict()
    assert data_dict["name"] == "CustomApp"
    assert data_dict["environment"] == "production"
    
    restored = AppConfig.from_dict(data_dict)
    assert restored.name == "CustomApp"
    assert restored.environment == "production"

def test_system_config_attribute_access():
    sys_cfg = SystemConfig()
    assert sys_cfg.app.name == "Eric"
    assert sys_cfg.agents.agents == {}
    assert sys_cfg.browser.is_mobile is False


# ── Parser Tests ──────────────────────────────────────────────────────────
def test_empty_yaml_file_handling(temp_config_dir):
    yaml_file = temp_config_dir / "empty.yaml"
    yaml_file.write_text("")
    parser = YAMLParser()
    data = parser.parse(yaml_file)
    assert data == {}

def test_malformed_yaml_raises_config_error(temp_config_dir):
    yaml_file = temp_config_dir / "bad.yaml"
    yaml_file.write_text("invalid:\n  - yaml: [")
    parser = YAMLParser()
    with pytest.raises(ConfigError):
        parser.parse(yaml_file)

def test_json_parser_support(temp_config_dir):
    json_file = temp_config_dir / "app.json"
    json_file.write_text(json.dumps({"name": "JSONApp"}))
    parser = JSONParser()
    data = parser.parse(json_file)
    assert data["name"] == "JSONApp"


# ── ConfigService Tests ───────────────────────────────────────────────────
def test_config_service_caching(temp_config_dir):
    app_yaml = temp_config_dir / "app.yaml"
    app_yaml.write_text("app:\n  name: TestApp\n")
    
    service = ConfigService()
    cfg1 = service.load_from_dir(temp_config_dir)
    assert cfg1.app.name == "TestApp"
    
    # Modify file, but shouldn't reload due to cache
    app_yaml.write_text("app:\n  name: NewApp\n")
    cfg2 = service.load_from_dir(temp_config_dir)
    assert cfg2.app.name == "TestApp"
    assert cfg1 is cfg2

def test_config_service_reload_invalidates_cache(temp_config_dir):
    app_yaml = temp_config_dir / "app.yaml"
    app_yaml.write_text("app:\n  name: TestApp\n")
    
    service = ConfigService()
    cfg1 = service.load_from_dir(temp_config_dir)
    
    app_yaml.write_text("app:\n  name: NewApp\n")
    cfg2 = service.load_from_dir(temp_config_dir, reload=True)
    assert cfg2.app.name == "NewApp"
    assert cfg1 is not cfg2

def test_missing_config_directory_returns_empty(tmp_path):
    service = ConfigService()
    cfg = service.load_from_dir(tmp_path / "non_existent_dir")
    assert isinstance(cfg, SystemConfig)
    assert cfg.app.name == "Eric"

def test_load_all_yaml_configs(temp_config_dir):
    (temp_config_dir / "app.yaml").write_text("app:\n  name: App1\n")
    (temp_config_dir / "browser.yaml").write_text("browser:\n  provider: selenium\n")
    
    service = ConfigService()
    sys_cfg = service.load_from_dir(temp_config_dir)
    
    assert sys_cfg.app.name == "App1"
    assert sys_cfg.browser.provider == "selenium"
    # Fallback to default for missing configs
    assert sys_cfg.llm.default_provider == "gemini"


# ── Plugin Custom Schema Test ─────────────────────────────────────────────
@dataclass(frozen=True)
class CustomPluginConfig(BaseSchema):
    custom_field: str = "default_value"

def test_plugin_custom_schema_registration():
    ConfigRegistry.register("my_plugin", CustomPluginConfig)
    assert ConfigRegistry.has("my_plugin")
    cls = ConfigRegistry.get("my_plugin")
    instance = cls(custom_field="changed")
    assert instance.custom_field == "changed"
