"""Configuration management for hlpr."""
from __future__ import annotations

from pathlib import Path
from typing import Any


class Config:
    """Configuration manager with hierarchical loading."""

    def __init__(self, config_file: Path | None = None) -> None:
        self.config_file = config_file or self._find_config_file()
        self._config: dict[str, Any] = {}
        self._load_config()

    def _find_config_file(self) -> Path:
        """Find configuration file in standard locations."""
        search_paths = [
            Path.cwd() / "hlpr.toml",
            Path.cwd() / ".hlpr.toml",
            Path.home() / ".config" / "hlpr" / "config.toml",
            Path.home() / ".hlpr.toml",
        ]

        for path in search_paths:
            if path.exists():
                return path

        # Return default location
        return Path.cwd() / "hlpr.toml"

    def _load_config(self) -> None:
        """Load configuration from file (simple key=value format for now)."""
        if self.config_file.exists():
            try:
                config = {}
                with open(self.config_file, encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#"):
                            if "=" in line:
                                key, value = line.split("=", 1)
                                key = key.strip()
                                value = value.strip().strip('"').strip("'")
                                self._set_nested_value(config, key, value)
                self._config = config
            except Exception:
                # If config file is corrupted, start with empty config
                self._config = {}
        else:
            self._config = {}

    def _set_nested_value(self, config: dict[str, Any], key: str, value: str) -> None:
        """Set a nested configuration value from dot notation."""
        keys = key.split(".")
        current = config

        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]

        current[keys[-1]] = value

    def _get_nested_value(self, config: dict[str, Any], key: str) -> Any:
        """Get a nested configuration value from dot notation."""
        keys = key.split(".")
        current = config

        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return None

        return current

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        return self._get_nested_value(self._config, key) or default

    def set(self, key: str, value: Any) -> None:
        """Set configuration value."""
        self._set_nested_value(self._config, key, str(value))

    def save(self) -> None:
        """Save configuration to file."""
        # Ensure config directory exists
        self.config_file.parent.mkdir(parents=True, exist_ok=True)

        with open(self.config_file, "w", encoding="utf-8") as f:
            f.write("# hlpr configuration file\n")
            f.write("# This file uses a simple key=value format\n\n")

            def write_dict(d: dict[str, Any], prefix: str = "") -> None:
                for k, v in d.items():
                    full_key = f"{prefix}.{k}" if prefix else k
                    if isinstance(v, dict):
                        write_dict(v, full_key)
                    else:
                        f.write(f'{full_key} = "{v}"\n')

            write_dict(self._config)

    def create_default(self) -> None:
        """Create default configuration."""
        default_config = {
            "model": {
                "default": "ollama/gemma3",
                "fallback": "gpt-3.5-turbo"
            },
            "optimization": {
                "default_optimizer": "mipro",
                "default_iters": 5,
                "max_bootstrapped_demos": 4,
                "max_labeled_demos": 16
            },
            "database": {
                "default_url": "sqlite+aiosqlite:///./hlpr.db"
            },
            "output": {
                "default_format": "markdown",
                "auto_save": "true"
            }
        }

        self._config.update(default_config)
        self.save()


# Global config instance
_config: Config | None = None


def get_config() -> Config:
    """Get global configuration instance."""
    global _config
    if _config is None:
        _config = Config()
    return _config


def init_config() -> None:
    """Initialize configuration with defaults if not exists."""
    config = get_config()
    if not config.config_file.exists():
        config.create_default()