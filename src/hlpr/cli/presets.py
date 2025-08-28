"""Command presets system for simplified CLI usage."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from hlpr.cli.base import SmartCLIError, print_error, print_info, print_success


class PresetConfig(BaseModel):
    """Configuration for a command preset."""

    # Common parameters
    model: str | None = None
    optimizer: str | None = None
    iters: int | None = None
    include_unverified: bool | None = None
    max_bootstrapped_demos: int | None = None
    max_labeled_demos: int | None = None

    # Meeting-specific parameters
    output: str | None = None

    # Database parameters
    drop: bool | None = None

    # Custom parameters for extensibility
    extra_args: dict[str, Any] = Field(default_factory=dict)


class PresetManager:
    """Manages command presets loaded from YAML configuration files."""

    def __init__(self) -> None:
        self._presets: dict[str, PresetConfig] = {}
        self._config_paths = self._get_config_paths()
        self._load_presets()

    def _get_config_paths(self) -> list[Path]:
        """Get paths where preset configuration files can be found."""
        paths = []

        # User-specific config directory
        user_config = Path.home() / ".hlpr"
        paths.append(user_config / "presets.yml")
        paths.append(user_config / "presets.yaml")

        # Project-specific config
        project_root = self._find_project_root()
        if project_root:
            paths.append(project_root / ".hlpr.yml")
            paths.append(project_root / ".hlpr.yaml")
            paths.append(project_root / "hlpr-presets.yml")
            paths.append(project_root / "hlpr-presets.yaml")

        # System-wide config
        paths.append(Path("/etc/hlpr/presets.yml"))
        paths.append(Path("/etc/hlpr/presets.yaml"))

        return paths

    def _find_project_root(self) -> Path | None:
        """Find the project root by looking for common markers."""
        current = Path.cwd()

        # Look for project markers
        markers = ["pyproject.toml", ".git", "uv.lock", "requirements.txt"]

        for path in [current] + list(current.parents):
            if any((path / marker).exists() for marker in markers):
                return path

        return None

    def _load_presets(self) -> None:
        """Load presets from all available configuration files."""
        for config_path in self._config_paths:
            if config_path.exists():
                try:
                    with open(config_path, encoding="utf-8") as f:
                        data = yaml.safe_load(f)

                    if data and "presets" in data:
                        for name, preset_data in data["presets"].items():
                            try:
                                preset = PresetConfig(**preset_data)
                                self._presets[name] = preset
                                print_info(f"Loaded preset '{name}' from {config_path}")
                            except Exception as e:
                                print_error(f"Invalid preset '{name}' in {config_path}: {e}")

                except Exception as e:
                    print_error(f"Failed to load presets from {config_path}: {e}")

    def get_preset(self, name: str) -> PresetConfig | None:
        """Get a preset by name."""
        return self._presets.get(name)

    def list_presets(self) -> dict[str, PresetConfig]:
        """List all available presets."""
        return self._presets.copy()

    def save_preset(self, name: str, config: PresetConfig, user_only: bool = True) -> bool:
        """Save a preset to the user configuration file.

        Args:
            name: Name of the preset
            config: Preset configuration
            user_only: If True, save to user config only

        Returns:
            True if successful, False otherwise
        """
        config_dir = Path.home() / ".hlpr"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_path = config_dir / "presets.yml"

        # Load existing presets
        existing_data: dict[str, Any] = {"presets": {}}
        if config_path.exists():
            try:
                with open(config_path, encoding="utf-8") as f:
                    existing_data = yaml.safe_load(f) or {"presets": {}}
            except Exception:
                pass  # Start fresh if file is corrupted

        # Add/update the preset
        existing_data["presets"][name] = config.model_dump(exclude_unset=True)

        try:
            with open(config_path, "w", encoding="utf-8") as f:
                yaml.dump(existing_data, f, default_flow_style=False, sort_keys=False)

            self._presets[name] = config
            print_success(f"Saved preset '{name}' to {config_path}")
            return True

        except Exception as e:
            print_error(f"Failed to save preset '{name}': {e}")
            return False

    def create_default_presets(self) -> None:
        """Create default presets if none exist."""
        if self._presets:
            return  # Don't overwrite existing presets

        defaults = {
            "quick": PresetConfig(
                optimizer="bootstrap",
                iters=1,
                model="ollama/gemma3",
                include_unverified=False,
            ),
            "development": PresetConfig(
                optimizer="bootstrap",
                iters=2,
                model="ollama/gemma3",
                include_unverified=True,
            ),
            "production": PresetConfig(
                optimizer="mipro",
                iters=10,
                model="gpt-4",
                include_unverified=False,
                max_bootstrapped_demos=8,
                max_labeled_demos=32,
            ),
            "experimental": PresetConfig(
                optimizer="mipro",
                iters=5,
                model="gpt-3.5-turbo",
                include_unverified=True,
                max_bootstrapped_demos=4,
                max_labeled_demos=16,
            ),
        }

        for name, config in defaults.items():
            self.save_preset(name, config)


# Global preset manager instance
_preset_manager: PresetManager | None = None


def get_preset_manager() -> PresetManager:
    """Get the global preset manager instance."""
    global _preset_manager
    if _preset_manager is None:
        _preset_manager = PresetManager()
    return _preset_manager


def apply_preset_to_args(preset_name: str, base_args: dict[str, Any]) -> dict[str, Any]:
    """Apply a preset's configuration to command arguments.

    Args:
        preset_name: Name of the preset to apply
        base_args: Base arguments dictionary (will be modified)

    Returns:
        Updated arguments dictionary with preset values applied
    """
    manager = get_preset_manager()
    preset = manager.get_preset(preset_name)

    if not preset:
        available = list(manager.list_presets().keys()) if hasattr(manager, 'list_presets') else []
        suggestions = [
            f"Use 'hlpr presets show {available[0]}' to see available presets" if available else "Create a preset first",
            "Run 'hlpr presets list' to see all available presets",
            "Use 'hlpr wizard' to create presets interactively",
            "Create presets manually by editing ~/.hlpr/presets.yml"
        ]
        SmartCLIError(
            f"Preset '{preset_name}' not found",
            suggestions=suggestions,
            error_code="PRESET_NOT_FOUND",
            help_url="https://docs.hlpr.dev/presets"
        ).display()
        return base_args

    print_info(f"Applying preset '{preset_name}'")

    # Apply preset values, but don't overwrite explicitly provided values
    updated_args = base_args.copy()

    preset_dict = preset.model_dump(exclude_unset=True, exclude={"extra_args"})
    for key, value in preset_dict.items():
        if key not in updated_args or updated_args[key] is None:
            updated_args[key] = value
            print_info(f"  {key}: {value}")

    # Apply extra args
    for key, value in preset.extra_args.items():
        if key not in updated_args or updated_args[key] is None:
            updated_args[key] = value
            print_info(f"  {key}: {value}")

    return updated_args