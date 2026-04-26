"""Configuration Loader Utilities

Handles loading and saving configurations with environment variable substitution
and default paths.

Author: Agent Cascade
Date: April 24, 2026
"""

import json
import os
from pathlib import Path
from typing import Any

import yaml

from .schemas import ExperimentConfig, ModelConfig


def load_config(
    path: str | Path,
    config_type: str = 'model',
) -> ModelConfig | ExperimentConfig:
    """Load configuration from YAML or JSON file.
    
    Automatically detects format from file extension.
    
    Args:
        path: Path to config file
        config_type: Type of config ('model' or 'experiment')
        
    Returns:
        Loaded configuration object
        
    Raises:
        ValueError: If file format not recognized
        FileNotFoundError: If file doesn't exist
        
    Example:
        config = load_config("configs/my_model.yaml", config_type="model")
        exp = load_config("experiments/compare.yaml", config_type="experiment")
    """
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f'Config file not found: {path}')

    # Detect format from extension
    suffix = path.suffix.lower()

    if suffix in ['.yaml', '.yml']:
        return load_from_yaml(path, config_type)
    if suffix == '.json':
        return load_from_json(path, config_type)
    raise ValueError(f'Unsupported config format: {suffix}. Use .yaml or .json')


def load_from_yaml(
    path: str | Path,
    config_type: str = 'model',
) -> ModelConfig | ExperimentConfig:
    """Load configuration from YAML file."""
    with open(path) as f:
        data = yaml.safe_load(f)

    # Substitute environment variables
    data = substitute_env_vars(data)

    if config_type == 'model':
        return ModelConfig(**data)
    if config_type == 'experiment':
        # Reconstruct nested ModelConfigs
        if 'models' in data:
            data['models'] = [ModelConfig(**m) for m in data['models']]
        return ExperimentConfig(**data)
    raise ValueError(f'Unknown config_type: {config_type}')


def load_from_json(
    path: str | Path,
    config_type: str = 'model',
) -> ModelConfig | ExperimentConfig:
    """Load configuration from JSON file."""
    with open(path) as f:
        data = json.load(f)

    # Substitute environment variables
    data = substitute_env_vars(data)

    if config_type == 'model':
        return ModelConfig(**data)
    if config_type == 'experiment':
        if 'models' in data:
            data['models'] = [ModelConfig(**m) for m in data['models']]
        return ExperimentConfig(**data)
    raise ValueError(f'Unknown config_type: {config_type}')


def substitute_env_vars(obj: Any) -> Any:
    """Recursively substitute environment variables in strings.
    
    Format: ${VAR_NAME} or ${VAR_NAME:default_value}
    """
    if isinstance(obj, dict):
        return {k: substitute_env_vars(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [substitute_env_vars(item) for item in obj]
    if isinstance(obj, str):
        # Handle ${VAR} or ${VAR:default}
        import re
        pattern = r'\$\{([^}:]+)(?::([^}]*))?\}'

        def replace(match):
            var_name = match.group(1)
            default_value = match.group(2)
            value = os.getenv(var_name, default_value)
            if value is None:
                raise ValueError(f'Environment variable {var_name} not set')
            return value

        return re.sub(pattern, replace, obj)
    return obj


def save_config(
    config: ModelConfig | ExperimentConfig,
    path: str | Path,
    format: str = 'yaml',
) -> None:
    """Save configuration to file.
    
    Args:
        config: Configuration object to save
        path: Destination path
        format: 'yaml' or 'json'
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    data = config.model_dump()

    if format in ['yaml', 'yml']:
        with open(path, 'w') as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)
    elif format == 'json':
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
    else:
        raise ValueError(f'Unknown format: {format}')


def find_configs(
    directory: str | Path,
    pattern: str = '*.yaml',
) -> list[Path]:
    """Find all config files in directory.
    
    Args:
        directory: Directory to search
        pattern: Glob pattern (default: *.yaml)
        
    Returns:
        List of config file paths
    """
    directory = Path(directory)
    return list(directory.glob(pattern))


def load_configs_batch(
    directory: str | Path,
    config_type: str = 'model',
) -> list[ModelConfig | ExperimentConfig]:
    """Load all configs from directory.
    
    Args:
        directory: Directory containing config files
        config_type: Type of configs
        
    Returns:
        List of loaded configurations
    """
    configs = []
    for path in find_configs(directory):
        try:
            config = load_config(path, config_type)
            configs.append(config)
        except Exception as e:
            print(f'Warning: Failed to load {path}: {e}')
    return configs


class ConfigManager:
    """Manages configuration storage and retrieval.
    
    Provides a centralized place to store and retrieve configurations
    with versioning and metadata.
    """

    def __init__(self, base_path: str | Path = 'configs'):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

        # Subdirectories
        self.models_path = self.base_path / 'models'
        self.experiments_path = self.base_path / 'experiments'
        self.defaults_path = self.base_path / 'defaults'

        for path in [self.models_path, self.experiments_path, self.defaults_path]:
            path.mkdir(exist_ok=True)

    def save_model_config(
        self,
        config: ModelConfig,
        name: str | None = None,
    ) -> Path:
        """Save model configuration."""
        if name is None:
            name = config.get_model_id_string()

        path = self.models_path / f'{name}.yaml'
        save_config(config, path, 'yaml')
        return path

    def save_experiment_config(
        self,
        config: ExperimentConfig,
        name: str | None = None,
    ) -> Path:
        """Save experiment configuration."""
        if name is None:
            name = config.experiment_name.replace(' ', '_').lower()

        path = self.experiments_path / f'{name}.yaml'
        save_config(config, path, 'yaml')
        return path

    def load_model_config(self, name: str) -> ModelConfig:
        """Load model configuration by name."""
        path = self.models_path / f'{name}.yaml'
        if not path.exists():
            path = self.models_path / f'{name}.json'
        return load_config(path, 'model')

    def load_experiment_config(self, name: str) -> ExperimentConfig:
        """Load experiment configuration by name."""
        path = self.experiments_path / f'{name}.yaml'
        if not path.exists():
            path = self.experiments_path / f'{name}.json'
        return load_config(path, 'experiment')

    def list_model_configs(self) -> list[str]:
        """List available model configurations."""
        configs = []
        for path in self.models_path.glob('*.yaml'):
            configs.append(path.stem)
        for path in self.models_path.glob('*.json'):
            if path.stem not in configs:
                configs.append(path.stem)
        return sorted(configs)

    def list_experiment_configs(self) -> list[str]:
        """List available experiment configurations."""
        configs = []
        for path in self.experiments_path.glob('*.yaml'):
            configs.append(path.stem)
        for path in self.experiments_path.glob('*.json'):
            if path.stem not in configs:
                configs.append(path.stem)
        return sorted(configs)

    def get_default_config(self, name: str) -> ModelConfig | None:
        """Load default configuration template."""
        from .schemas import (
            get_default_lightgbm_config,
            get_default_xgboost_config,
            get_quick_test_config,
        )

        defaults = {
            'xgboost': get_default_xgboost_config,
            'lightgbm': get_default_lightgbm_config,
            'quick_test': get_quick_test_config,
        }

        if name in defaults:
            return defaults[name]()
        return None


# Convenience functions

def load_model_config(path: str | Path) -> ModelConfig:
    """Load a model configuration from file."""
    return load_config(path, config_type='model')


def load_experiment_config(path: str | Path) -> ExperimentConfig:
    """Load an experiment configuration from file."""
    return load_config(path, config_type='experiment')


def save_model_config(
    config: ModelConfig,
    path: str | Path,
    format: str = 'yaml',
) -> None:
    """Save a model configuration to file."""
    save_config(config, path, format)


def save_experiment_config(
    config: ExperimentConfig,
    path: str | Path,
    format: str = 'yaml',
) -> None:
    """Save an experiment configuration to file."""
    save_config(config, path, format)


__all__ = [
    'ConfigManager',
    'find_configs',
    'load_config',
    'load_configs_batch',
    'load_experiment_config',
    'load_from_json',
    'load_from_yaml',
    'load_model_config',
    'save_config',
    'save_experiment_config',
    'save_model_config',
    'substitute_env_vars',
]
