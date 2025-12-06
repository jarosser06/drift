"""Configuration loading and merging logic."""

from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import requests
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
    DEFAULT_RULES_FILE = ".drift_rules.yaml"
    RULES_FETCH_TIMEOUT = 10  # seconds

    @staticmethod
    def _load_yaml_file(path: Path) -> Optional[Dict[str, Any]]:
        """Load YAML file if it exists.

        -- path: Path to YAML file

        Returns parsed YAML content or None if file doesn't exist.
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
    def _is_remote_url(source: str) -> bool:
        """Check if source is a remote URL (HTTP or HTTPS).

        -- source: File path or URL to check

        Returns True if source is an HTTP(S) URL, False otherwise.
        """
        parsed = urlparse(source)
        return parsed.scheme in ("http", "https")

    @classmethod
    def _load_remote_rules(cls, url: str) -> Dict[str, Any]:
        """Load rules from remote HTTP(S) URL.

        -- url: Remote URL to fetch rules from

        Returns parsed YAML content from remote file.

        Raises ValueError if request fails or YAML is invalid.
        """
        try:
            response = requests.get(url, timeout=cls.RULES_FETCH_TIMEOUT)
            response.raise_for_status()
        except requests.exceptions.Timeout:
            raise ValueError(
                f"Timeout fetching rules from {url} (timeout: {cls.RULES_FETCH_TIMEOUT}s)"
            )
        except requests.exceptions.RequestException as e:
            raise ValueError(f"Error fetching rules from {url}: {e}")

        try:
            content = yaml.safe_load(response.text)
            return content if content is not None else {}
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in remote rules file {url}: {e}")

    @classmethod
    def _process_rules_file_content(cls, content: Dict[str, Any]) -> Dict[str, Any]:
        """Process rules file content, handling top-level group_name.

        If the file has a top-level 'group_name' field, apply it to all rules
        in the file that don't have their own explicit group_name.

        -- content: Raw YAML content from rules file

        Returns processed rules dictionary with group_name removed from top-level.
        """
        if not content:
            return {}

        # Extract top-level group_name if present
        file_group_name = content.pop("group_name", None)

        # If there's a file-level group_name, apply it to rules without one
        if file_group_name is not None:
            for rule_name, rule_def in content.items():
                if isinstance(rule_def, dict) and "group_name" not in rule_def:
                    rule_def["group_name"] = file_group_name

        return content

    @classmethod
    def _load_rules_file(cls, source: str) -> Dict[str, Any]:
        """Load rules from file or URL.

        -- source: Local file path or HTTP(S) URL

        Returns parsed rules dictionary.

        Raises ValueError if source doesn't exist or has invalid YAML.
        """
        if cls._is_remote_url(source):
            content = cls._load_remote_rules(source)
            return cls._process_rules_file_content(content)

        # Local file
        path = Path(source).expanduser().resolve()
        if not path.exists():
            raise ValueError(f"Rules file not found: {source}")

        try:
            with open(path, "r") as f:
                content = yaml.safe_load(f)
                content = content if content is not None else {}
                return cls._process_rules_file_content(content)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in rules file {source}: {e}")
        except Exception as e:
            raise ValueError(f"Error loading rules from {source}: {e}")

    @classmethod
    def _merge_rules(
        cls,
        base_rules: Dict[str, Any],
        new_rules: Dict[str, Any],
        default_group_name: str = "General",
    ) -> Dict[str, Any]:
        """Merge two rule definition dictionaries.

        Rules with the same name but different groups are allowed.
        Later rules override earlier rules with the same name AND group.

        -- base_rules: Base rule definitions
        -- new_rules: New rule definitions to merge in
        -- default_group_name: Default group name to use for rules without explicit group

        Returns merged rule definitions.
        """
        # Simply merge - later rules override earlier ones
        # This allows intentional overrides in the loading priority chain:
        # CLI rules > .drift_rules.yaml > .drift.yaml rules
        merged = base_rules.copy()
        merged.update(new_rules)
        return merged

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
    def load_config(
        cls, project_path: Optional[Path] = None, rules_files: Optional[List[str]] = None
    ) -> DriftConfig:
        """Load complete configuration with proper merging.

        Priority (highest to lowest):
        1. Project config (.drift.yaml)
        2. Global config (~/.config/drift/config.yaml)
        3. Default config (hardcoded)

        Rules loading priority (highest to lowest):
        1. --rules-file CLI arguments (if provided, can be multiple)
        2. .drift_rules.yaml in project root (if exists)
        3. rule_definitions section in .drift.yaml (current behavior)
        4. Empty rules dict (use built-in defaults only)

        -- project_path: Path to project directory (defaults to current directory)
        -- rules_files: Optional list of rules file paths/URLs from CLI

        Returns merged and validated DriftConfig.
        """
        if project_path is None:
            project_path = Path.cwd()

        # Start with default config
        default_dict = cls._config_to_dict(get_default_config())

        # Load and merge global config
        global_dict = cls.load_global_config()
        merged = cls._deep_merge(default_dict, global_dict)

        # Load and merge project config
        project_dict = cls.load_project_config(project_path)
        if project_dict:
            merged = cls._deep_merge(merged, project_dict)

        # Get default group name from merged config (for duplicate checking)
        default_group_name = merged.get("default_group_name", "General")

        # Load rules with priority order
        rules_dict: Dict[str, Any] = {}

        # Start with rules from .drift.yaml (lowest priority)
        if "rule_definitions" in merged:
            rules_dict = merged.get("rule_definitions", {})

        # Check for .drift_rules.yaml in project root
        default_rules_file = project_path / cls.DEFAULT_RULES_FILE
        if default_rules_file.exists():
            try:
                default_rules = cls._load_rules_file(str(default_rules_file))
                rules_dict = cls._merge_rules(rules_dict, default_rules, default_group_name)
            except ValueError as e:
                raise ValueError(f"Error loading {cls.DEFAULT_RULES_FILE}: {e}")

        # Apply CLI-specified rules files (highest priority)
        if rules_files:
            for rules_file in rules_files:
                try:
                    file_rules = cls._load_rules_file(rules_file)
                    rules_dict = cls._merge_rules(rules_dict, file_rules, default_group_name)
                except ValueError as e:
                    raise ValueError(f"Error loading rules file '{rules_file}': {e}")

        # Update merged config with final rules
        merged["rule_definitions"] = rules_dict

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
        for rule_name, rule_def in config.rule_definitions.items():
            if rule_def.phases:
                for phase in rule_def.phases:
                    if phase.model and phase.model not in config.models:
                        available = list(config.models.keys())
                        raise ValueError(
                            f"Rule '{rule_name}' phase '{phase.name}' "
                            f"references unknown model '{phase.model}'. "
                            f"Available models: {available}"
                        )

        # Validate at least one enabled agent tool
        enabled_tools = config.get_enabled_agent_tools()
        if not enabled_tools:
            raise ValueError("At least one agent tool must be enabled")

        # Validate rule name + group name uniqueness
        ConfigLoader._validate_rule_group_uniqueness(config)

        # Note: We don't require rules to be defined since users might
        # only want to use drift for document analysis or have project-specific configs

    @staticmethod
    def _validate_rule_group_uniqueness(config: DriftConfig) -> None:
        """Validate that rule name + group name combinations are unique.

        Args:
            config: Loaded configuration

        Raises:
            ValueError: If duplicate rule name + group name combinations are found
        """
        seen_combinations = {}

        for rule_name, rule_def in config.rule_definitions.items():
            # Get effective group name (use default if not specified)
            group_name = rule_def.group_name or config.default_group_name

            # Create unique key from group + rule name
            combination_key = (group_name, rule_name)

            if combination_key in seen_combinations:
                raise ValueError(
                    f"Duplicate rule name '{rule_name}' in group '{group_name}'. "
                    f"Rule names must be unique within their group."
                )

            seen_combinations[combination_key] = True
