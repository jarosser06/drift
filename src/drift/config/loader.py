"""Configuration loading and merging logic."""

from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from drift.config.defaults import get_default_config
from drift.config.models import DriftConfig


class ConfigLoader:
    """Handles loading and merging of drift configurations."""

    GLOBAL_CONFIG_PATHS = [
        Path.home() / ".config" / "drift" / "config.yaml",
        Path.home() / "drift" / "config.yaml",
        Path.home() / ".drift" / "config.yaml",
    ]
    PROJECT_CONFIG_NAME = ".drift.yaml"

    @staticmethod
    def _load_yaml_file(path: Path) -> Optional[Dict[str, Any]]:
        """Load YAML file if it exists.

        Args:
            path: Path to YAML file

        Returns:
            Parsed YAML content or None if file doesn't exist
        """
        if not path.exists():
            return None

        try:
            with open(path, "r") as f:
                content = yaml.safe_load(f)
                return content if content is not None else {}
        except Exception as e:
            raise ValueError(f"Error loading config from {path}: {e}")

    @staticmethod
    def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two dictionaries, with override taking precedence.

        Args:
            base: Base dictionary
            override: Override dictionary

        Returns:
            Merged dictionary
        """
        result = base.copy()

        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                # Recursively merge dictionaries
                result[key] = ConfigLoader._deep_merge(result[key], value)
            else:
                # Override value
                result[key] = value

        return result

    @staticmethod
    def _save_yaml_file(path: Path, config: Dict[str, Any]) -> None:
        """Save configuration to YAML file.

        Args:
            path: Path to save to
            config: Configuration dictionary to save
        """
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w") as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)

    @staticmethod
    def _config_to_dict(config: DriftConfig) -> Dict[str, Any]:
        """Convert DriftConfig to dictionary for YAML export.

        Args:
            config: DriftConfig instance

        Returns:
            Dictionary representation suitable for YAML
        """
        # Use pydantic's model_dump to convert to dict, with json mode to serialize enums
        return config.model_dump(mode="json", exclude_none=True)

    @classmethod
    def get_global_config_path(cls) -> Path:
        """Get the path to use for global config.

        Returns:
            Path to global config (first existing or preferred default)
        """
        # Check if any global config exists
        for path in cls.GLOBAL_CONFIG_PATHS:
            if path.exists():
                return path

        # Return the preferred default (first in list)
        return cls.GLOBAL_CONFIG_PATHS[0]

    @classmethod
    def load_global_config(cls) -> Dict[str, Any]:
        """Load global configuration.

        Returns:
            Global configuration dictionary (empty if no file exists)
        """
        for path in cls.GLOBAL_CONFIG_PATHS:
            config = cls._load_yaml_file(path)
            if config is not None:
                return config

        return {}

    @classmethod
    def load_project_config(cls, project_path: Optional[Path] = None) -> Dict[str, Any]:
        """Load project-specific configuration.

        Args:
            project_path: Path to project directory (defaults to current directory)

        Returns:
            Project configuration dictionary (empty if no file exists)
        """
        if project_path is None:
            project_path = Path.cwd()

        config_path = project_path / cls.PROJECT_CONFIG_NAME
        config = cls._load_yaml_file(config_path)
        return config if config is not None else {}

    @classmethod
    def ensure_global_config_exists(cls) -> Path:
        """Ensure global config exists, creating it if necessary.

        Returns:
            Path to global config file
        """
        config_path = cls.get_global_config_path()

        if not config_path.exists():
            # Create default config
            default_config = get_default_config()
            config_dict = cls._config_to_dict(default_config)
            cls._save_yaml_file(config_path, config_dict)

        return config_path

    @classmethod
    def load_config(cls, project_path: Optional[Path] = None) -> DriftConfig:
        """Load complete configuration with proper merging.

        Priority (highest to lowest):
        1. Project config (.drift.yaml)
        2. Global config (~/.config/drift/config.yaml)
        3. Default config (hardcoded)

        Args:
            project_path: Path to project directory (defaults to current directory)

        Returns:
            Merged and validated DriftConfig
        """
        # Start with default config
        default_dict = cls._config_to_dict(get_default_config())

        # Load and merge global config
        global_dict = cls.load_global_config()
        merged = cls._deep_merge(default_dict, global_dict)

        # Load and merge project config
        project_dict = cls.load_project_config(project_path)
        if project_dict:
            merged = cls._deep_merge(merged, project_dict)

        # Validate and return
        try:
            config = DriftConfig.model_validate(merged)
        except Exception as e:
            raise ValueError(f"Invalid configuration: {e}")

        # Post-validation checks
        cls._validate_config(config)

        return config

    @staticmethod
    def _validate_config(config: DriftConfig) -> None:
        """Perform additional validation on loaded config.

        Args:
            config: Loaded configuration

        Raises:
            ValueError: If configuration is invalid
        """
        # Validate default model exists
        if config.default_model not in config.models:
            raise ValueError(
                f"Default model '{config.default_model}' not found in models. "
                f"Available models: {list(config.models.keys())}"
            )

        # Validate phase model overrides
        for type_name, learning_type in config.drift_learning_types.items():
            if learning_type.phases:
                for phase in learning_type.phases:
                    if phase.model and phase.model not in config.models:
                        available = list(config.models.keys())
                        raise ValueError(
                            f"Learning type '{type_name}' phase '{phase.name}' "
                            f"references unknown model '{phase.model}'. "
                            f"Available models: {available}"
                        )

        # Validate at least one enabled agent tool
        enabled_tools = config.get_enabled_agent_tools()
        if not enabled_tools:
            raise ValueError("At least one agent tool must be enabled")

        # Note: We don't require learning types to be defined since users might
        # only want to use drift for document analysis or have project-specific configs
