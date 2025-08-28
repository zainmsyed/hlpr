"""TOML-based configuration profiles system."""
from __future__ import annotations

import os
import tomllib
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from hlpr.cli.base import SmartCLIError, print_error, print_info, print_success


class ProfileConfig(BaseModel):
    """Configuration for a profile."""

    # Environment settings
    environment: str | None = None
    debug: bool | None = None

    # Model settings
    model: str | None = None
    api_base: str | None = None

    # Training settings
    optimizer: str | None = None
    iters: int | None = None
    include_unverified: bool | None = None
    max_bootstrapped_demos: int | None = None
    max_labeled_demos: int | None = None

    # Database settings
    database_url: str | None = None

    # Docker settings
    docker_compose_file: str | None = None
    container_name: str | None = None

    # Custom settings for extensibility
    extra: dict[str, Any] = Field(default_factory=dict)


class ProfileManager:
    """Manages configuration profiles loaded from TOML files."""

    def __init__(self) -> None:
        self._profiles: dict[str, ProfileConfig] = {}
        self._config_paths = self._get_config_paths()
        self._load_profiles()

    def _get_config_paths(self) -> list[Path]:
        """Get paths where profile configuration files can be found."""
        paths = []

        # User-specific config directory
        user_config = Path.home() / ".hlpr"
        paths.append(user_config / "profiles.toml")

        # Project-specific config
        project_root = self._find_project_root()
        if project_root:
            paths.append(project_root / ".hlpr.toml")
            paths.append(project_root / "hlpr-profiles.toml")

        # System-wide config
        paths.append(Path("/etc/hlpr/profiles.toml"))

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

    def _load_profiles(self) -> None:
        """Load profiles from all available configuration files."""
        for config_path in self._config_paths:
            if config_path.exists():
                try:
                    with open(config_path, "rb") as f:
                        data = tomllib.load(f)

                    if data and "profiles" in data:
                        for name, profile_data in data["profiles"].items():
                            try:
                                profile = ProfileConfig(**profile_data)
                                self._profiles[name] = profile
                                print_info(f"Loaded profile '{name}' from {config_path}")
                            except Exception as e:
                                print_error(f"Invalid profile '{name}' in {config_path}: {e}")

                except Exception as e:
                    print_error(f"Failed to load profiles from {config_path}: {e}")

    def get_profile(self, name: str) -> ProfileConfig | None:
        """Get a profile by name."""
        return self._profiles.get(name)

    def list_profiles(self) -> dict[str, ProfileConfig]:
        """List all available profiles."""
        return self._profiles.copy()

    def create_default_profiles(self) -> None:
        """Create default profiles if none exist."""
        if self._profiles:
            return  # Don't overwrite existing profiles

        defaults = {
            "development": ProfileConfig(
                environment="development",
                debug=True,
                model="ollama/gemma3",
                optimizer="bootstrap",
                iters=2,
                include_unverified=True,
                max_bootstrapped_demos=4,
                max_labeled_demos=8,
                api_base="http://localhost:11434",
            ),
            "staging": ProfileConfig(
                environment="staging",
                debug=False,
                model="gpt-3.5-turbo",
                optimizer="mipro",
                iters=5,
                include_unverified=False,
                max_bootstrapped_demos=8,
                max_labeled_demos=16,
            ),
            "production": ProfileConfig(
                environment="production",
                debug=False,
                model="gpt-4",
                optimizer="mipro",
                iters=10,
                include_unverified=False,
                max_bootstrapped_demos=16,
                max_labeled_demos=32,
            ),
        }

        for name, config in defaults.items():
            self.save_profile(name, config)

    def save_profile(self, name: str, config: ProfileConfig, user_only: bool = True) -> bool:
        """Save a profile to the user configuration file.

        Args:
            name: Name of the profile
            config: Profile configuration
            user_only: If True, save to user config only

        Returns:
            True if successful, False otherwise
        """
        config_dir = Path.home() / ".hlpr"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_path = config_dir / "profiles.toml"

        # Load existing profiles
        existing_data: dict[str, dict[str, dict[str, Any]]] = {"profiles": {}}
        if config_path.exists():
            try:
                with open(config_path, "rb") as f:
                    existing_data = tomllib.load(f) or {"profiles": {}}
            except Exception:
                pass  # Start fresh if file is corrupted

        # Add/update the profile
        existing_data["profiles"][name] = config.model_dump(exclude_unset=True, exclude={"extra"})
        if config.extra:
            existing_data["profiles"][name]["extra"] = config.extra

        try:
            # Simple TOML-like output (basic implementation)
            with open(config_path, "w", encoding="utf-8") as f:
                f.write("# hlpr profiles configuration\n\n")
                f.write("[profiles]\n\n")
                for profile_name, profile_data in existing_data["profiles"].items():
                    f.write(f'[{profile_name}]\n')
                    for key, value in profile_data.items():
                        if isinstance(value, str):
                            f.write(f'{key} = "{value}"\n')
                        elif isinstance(value, bool):
                            f.write(f'{key} = {str(value).lower()}\n')
                        elif isinstance(value, int | float):
                            f.write(f'{key} = {value}\n')
                        elif isinstance(value, list):
                            f.write(f'{key} = {value}\n')
                        else:
                            f.write(f'{key} = "{value}"\n')
                    f.write('\n')

            self._profiles[name] = config
            print_success(f"Saved profile '{name}' to {config_path}")
            return True

        except Exception as e:
            print_error(f"Failed to save profile '{name}': {e}")
            return False

    def apply_profile(self, name: str) -> dict[str, Any]:
        """Apply a profile's configuration to environment variables.

        Args:
            name: Name of the profile to apply

        Returns:
            Dictionary of configuration values
        """
        profile = self.get_profile(name)
        if not profile:
            available = list(self.list_profiles().keys()) if hasattr(self, 'list_profiles') else []
            suggestions = [
                f"Use 'hlpr profile apply {available[0]}' to apply available profiles" if available else "Create a profile first",
                "Run 'hlpr profile list' to see all available profiles",
                "Use 'hlpr configure profiles' to create profiles interactively",
                "Create profiles manually by editing ~/.hlpr/profiles.toml"
            ]
            SmartCLIError(
                f"Profile '{name}' not found",
                suggestions=suggestions,
                error_code="PROFILE_NOT_FOUND",
                help_url="https://docs.hlpr.dev/profiles"
            ).display()
            return {}

        print_info(f"Applying profile '{name}'")

        config_dict = {}
        profile_dict = profile.model_dump(exclude_unset=True, exclude={"extra"})

        for key, value in profile_dict.items():
            config_dict[key] = value
            print_info(f"  {key}: {value}")

        # Apply extra settings
        for key, value in profile.extra.items():
            config_dict[key] = value
            print_info(f"  {key}: {value}")

        return config_dict

    def get_current_profile(self) -> str | None:
        """Get the name of the currently active profile."""
        # Check environment variable first
        profile_name = os.environ.get("HLPR_PROFILE")
        if profile_name:
            return profile_name

        # Try to infer from environment
        env = os.environ.get("ENVIRONMENT", "").lower()
        if env in ["dev", "development"]:
            return "development"
        elif env in ["staging", "stage"]:
            return "staging"
        elif env in ["prod", "production"]:
            return "production"

        return None


# Global profile manager instance
_profile_manager: ProfileManager | None = None


def get_profile_manager() -> ProfileManager:
    """Get the global profile manager instance."""
    global _profile_manager
    if _profile_manager is None:
        _profile_manager = ProfileManager()
    return _profile_manager


def apply_profile_to_args(profile_name: str, base_args: dict[str, Any]) -> dict[str, Any]:
    """Apply a profile's configuration to command arguments.

    Args:
        profile_name: Name of the profile to apply
        base_args: Base arguments dictionary (will be modified)

    Returns:
        Updated arguments dictionary with profile values applied
    """
    manager = get_profile_manager()
    profile_config = manager.apply_profile(profile_name)

    if not profile_config:
        return base_args

    # Apply profile values, but don't overwrite explicitly provided values
    updated_args = base_args.copy()

    for key, value in profile_config.items():
        if key not in updated_args or updated_args[key] is None:
            updated_args[key] = value

    return updated_args