"""
Model Registry Implementation.
"""

from core.llm.interfaces import IModelRegistry
from core.llm.models import ModelConfig


class InMemoryModelRegistry(IModelRegistry):
    def __init__(self):
        self._models: dict[str, ModelConfig] = {}
        self._default: str | None = None

    def register(self, config: ModelConfig, is_default: bool = False) -> None:
        self._models[config.name] = config
        if is_default or self._default is None:
            self._default = config.name

    def get_model(self, name: str) -> ModelConfig | None:
        return self._models.get(name)

    def get_default_model(self) -> ModelConfig:
        if not self._default:
            raise RuntimeError("No default model registered in ModelRegistry.")
        return self._models[self._default]
