"""Configuration loading and merging."""

from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

from .defaults import MASTERING_PRESETS
from ..core.errors import ConfigurationError


def get_config_paths() -> list[Path]:
    """
    Get configuration file search paths in priority order.

    Returns:
        List of paths to check for config files
    """
    paths = []

    # User config
    user_config = Path.home() / '.config' / 'mediforge' / 'config.yaml'
    if user_config.exists():
        paths.append(user_config)

    # Project config
    project_config = Path.cwd() / '.mediforge.yaml'
    if project_config.exists():
        paths.append(project_config)

    return paths


def load_config() -> dict[str, Any]:
    """
    Load and merge configuration from all sources.

    Priority (highest to lowest):
    1. Project config (.mediforge.yaml in cwd)
    2. User config (~/.config/mediforge/config.yaml)
    3. Built-in defaults
    """
    config: dict[str, Any] = {}
    yaml = YAML()

    for path in get_config_paths():
        try:
            with open(path) as f:
                file_config = yaml.load(f)
                if file_config:
                    _deep_merge(config, file_config)
        except Exception:
            pass  # Ignore invalid config files

    return config


def _deep_merge(base: dict, override: dict) -> None:
    """Deep merge override into base dict."""
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value


def get_mastering_preset(name: str) -> dict[str, Any]:
    """
    Get mastering preset by name.

    Args:
        name: Preset name

    Returns:
        Preset configuration dict

    Raises:
        ConfigurationError: If preset not found
    """
    config = load_config()
    presets = {**MASTERING_PRESETS, **config.get('mastering_presets', {})}

    if name not in presets:
        available = ', '.join(sorted(presets.keys()))
        raise ConfigurationError(
            f"Unknown preset: {name}. Available: {available}"
        )

    return presets[name]
