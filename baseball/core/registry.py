"""Source/model registry for the baseball platform.

Author: Agent cbwinslow/retrosheet
Date: 2026-04-26
"""

from typing import Any


class Registry:
    """Registry for tracking sources, features, and models."""

    def __init__(self) -> None:
        """Initialize empty registry."""
        self._sources: dict[str, Any] = {}
        self._features: dict[str, Any] = {}
        self._models: dict[str, Any] = {}

    def register_source(self, name: str, source: Any) -> None:
        """Register a data source."""
        self._sources[name] = source

    def register_feature(self, name: str, feature: Any) -> None:
        """Register a feature builder."""
        self._features[name] = feature

    def register_model(self, name: str, model: Any) -> None:
        """Register a model."""
        self._models[name] = model
