"""Unit tests for configuration loader."""

import pytest
import yaml

from drift.config.loader import ConfigLoader
from drift.config.models import AgentToolConfig, ConversationMode, DriftConfig, DriftLearningType


class TestConfigLoader:
    """Tests for ConfigLoader class."""

    def test_load_yaml_file_exists(self, temp_dir):
        """Test loading an existing YAML file."""
        config_file = temp_dir / "test.yaml"
        config_data = {"key": "value", "nested": {"item": "data"}}

        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        result = ConfigLoader._load_yaml_file(config_file)
        assert result == config_data

    def test_load_yaml_file_not_exists(self, temp_dir):
        """Test loading a non-existent YAML file returns None."""
        config_file = temp_dir / "nonexistent.yaml"
        result = ConfigLoader._load_yaml_file(config_file)
        assert result is None

    def test_load_yaml_file_empty(self, temp_dir):
        """Test loading an empty YAML file returns empty dict."""
        config_file = temp_dir / "empty.yaml"
        config_file.write_text("")

        result = ConfigLoader._load_yaml_file(config_file)
        assert result == {}

    def test_load_yaml_file_invalid(self, temp_dir):
        """Test loading an invalid YAML file raises error."""
        config_file = temp_dir / "invalid.yaml"
        config_file.write_text("invalid: yaml: content:\n  - broken")

        with pytest.raises(ValueError) as exc_info:
            ConfigLoader._load_yaml_file(config_file)
        assert "Error loading config" in str(exc_info.value)

    def test_deep_merge_simple(self):
        """Test deep merge with simple dictionaries."""
        base = {"a": 1, "b": 2}
        override = {"b": 3, "c": 4}

        result = ConfigLoader._deep_merge(base, override)
        assert result == {"a": 1, "b": 3, "c": 4}

    def test_deep_merge_nested(self):
        """Test deep merge with nested dictionaries."""
        base = {"level1": {"a": 1, "b": 2}, "other": "value"}
        override = {"level1": {"b": 3, "c": 4}}

        result = ConfigLoader._deep_merge(base, override)
        assert result == {"level1": {"a": 1, "b": 3, "c": 4}, "other": "value"}

    def test_deep_merge_deeply_nested(self):
        """Test deep merge with deeply nested dictionaries."""
        base = {"l1": {"l2": {"l3": {"a": 1, "b": 2}}}}
        override = {"l1": {"l2": {"l3": {"b": 3}, "new": "value"}}}

        result = ConfigLoader._deep_merge(base, override)
        assert result == {"l1": {"l2": {"l3": {"a": 1, "b": 3}, "new": "value"}}}

    def test_deep_merge_override_with_non_dict(self):
        """Test deep merge when override replaces dict with non-dict."""
        base = {"a": {"nested": "value"}}
        override = {"a": "simple"}

        result = ConfigLoader._deep_merge(base, override)
        assert result == {"a": "simple"}

    def test_deep_merge_preserves_original(self):
        """Test that deep merge doesn't modify original dicts."""
        base = {"a": 1}
        override = {"b": 2}

        result = ConfigLoader._deep_merge(base, override)
        assert base == {"a": 1}  # Unchanged
        assert override == {"b": 2}  # Unchanged
        assert result == {"a": 1, "b": 2}

    def test_save_yaml_file(self, temp_dir):
        """Test saving configuration to YAML file."""
        config_file = temp_dir / "subdir" / "config.yaml"
        config_data = {"key": "value", "nested": {"item": "data"}}

        ConfigLoader._save_yaml_file(config_file, config_data)

        assert config_file.exists()
        with open(config_file, "r") as f:
            loaded = yaml.safe_load(f)
        assert loaded == config_data

    def test_config_to_dict(self, sample_drift_config):
        """Test converting DriftConfig to dictionary."""
        result = ConfigLoader._config_to_dict(sample_drift_config)

        assert isinstance(result, dict)
        assert "models" in result
        assert "default_model" in result
        assert result["default_model"] == "haiku"

    def test_get_global_config_path_existing(self, temp_dir, monkeypatch):
        """Test getting global config path when file exists."""
        config_file = temp_dir / "config.yaml"
        config_file.write_text("test: config")

        # Mock the GLOBAL_CONFIG_PATHS to use our temp directory
        monkeypatch.setattr(
            ConfigLoader,
            "GLOBAL_CONFIG_PATHS",
            [config_file, temp_dir / "alt.yaml"],
        )

        result = ConfigLoader.get_global_config_path()
        assert result == config_file

    def test_get_global_config_path_none_existing(self, temp_dir, monkeypatch):
        """Test getting global config path when no file exists."""
        config_file = temp_dir / "config.yaml"

        monkeypatch.setattr(
            ConfigLoader,
            "GLOBAL_CONFIG_PATHS",
            [config_file, temp_dir / "alt.yaml"],
        )

        result = ConfigLoader.get_global_config_path()
        assert result == config_file  # Returns first in list

    def test_load_global_config_exists(self, temp_dir, monkeypatch):
        """Test loading global config when file exists."""
        config_file = temp_dir / "config.yaml"
        config_data = {"models": {"haiku": {"provider": "bedrock"}}}

        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        monkeypatch.setattr(ConfigLoader, "GLOBAL_CONFIG_PATHS", [config_file])

        result = ConfigLoader.load_global_config()
        assert result == config_data

    def test_load_global_config_not_exists(self, temp_dir, monkeypatch):
        """Test loading global config when no file exists."""
        monkeypatch.setattr(
            ConfigLoader,
            "GLOBAL_CONFIG_PATHS",
            [temp_dir / "nonexistent.yaml"],
        )

        result = ConfigLoader.load_global_config()
        assert result == {}

    def test_load_project_config_exists(self, temp_dir):
        """Test loading project config when file exists."""
        config_file = temp_dir / ".drift.yaml"
        config_data = {"conversations": {"mode": "all"}}

        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        result = ConfigLoader.load_project_config(temp_dir)
        assert result == config_data

    def test_load_project_config_not_exists(self, temp_dir):
        """Test loading project config when file doesn't exist."""
        result = ConfigLoader.load_project_config(temp_dir)
        assert result == {}

    def test_load_project_config_current_dir(self, temp_dir, monkeypatch):
        """Test loading project config from current directory."""
        config_file = temp_dir / ".drift.yaml"
        config_data = {"test": "value"}

        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        monkeypatch.chdir(temp_dir)

        result = ConfigLoader.load_project_config()
        assert result == config_data

    def test_ensure_global_config_exists_creates_file(self, temp_dir, monkeypatch):
        """Test that ensure_global_config_exists creates file if missing."""
        config_file = temp_dir / "config.yaml"

        monkeypatch.setattr(ConfigLoader, "GLOBAL_CONFIG_PATHS", [config_file])

        result = ConfigLoader.ensure_global_config_exists()

        assert result == config_file
        assert config_file.exists()

        # Verify it's valid YAML with expected structure
        with open(config_file, "r") as f:
            config = yaml.safe_load(f)
        assert "models" in config
        assert "default_model" in config

    def test_ensure_global_config_exists_preserves_existing(self, temp_dir, monkeypatch):
        """Test that ensure_global_config_exists preserves existing file."""
        config_file = temp_dir / "config.yaml"
        original_data = {"custom": "configuration"}

        with open(config_file, "w") as f:
            yaml.dump(original_data, f)

        monkeypatch.setattr(ConfigLoader, "GLOBAL_CONFIG_PATHS", [config_file])

        result = ConfigLoader.ensure_global_config_exists()

        assert result == config_file

        # Original content should be preserved
        with open(config_file, "r") as f:
            config = yaml.safe_load(f)
        assert config == original_data

    def test_load_config_default_only(self, temp_dir, monkeypatch):
        """Test loading config with only defaults (no files)."""
        monkeypatch.setattr(
            ConfigLoader,
            "GLOBAL_CONFIG_PATHS",
            [temp_dir / "nonexistent.yaml"],
        )

        config = ConfigLoader.load_config(temp_dir)

        assert isinstance(config, DriftConfig)
        assert config.default_model == "haiku"
        assert "haiku" in config.models
        assert "claude-code" in config.agent_tools

    def test_load_config_with_global(self, temp_dir, monkeypatch):
        """Test loading config with global config override."""
        global_config = temp_dir / "global.yaml"
        global_data = {
            "default_model": "sonnet",
            "providers": {
                "bedrock": {
                    "provider": "bedrock",
                    "params": {"region": "us-west-2"},
                }
            },
            "models": {
                "sonnet": {
                    "provider": "bedrock",
                    "model_id": "claude-sonnet",
                    "params": {},
                }
            },
        }

        with open(global_config, "w") as f:
            yaml.dump(global_data, f)

        monkeypatch.setattr(ConfigLoader, "GLOBAL_CONFIG_PATHS", [global_config])

        config = ConfigLoader.load_config(temp_dir)

        # Should have both default and override
        assert "haiku" in config.models  # From defaults
        assert "sonnet" in config.models  # From global

    def test_load_config_with_project(self, temp_dir, monkeypatch):
        """Test loading config with project config override."""
        monkeypatch.setattr(
            ConfigLoader,
            "GLOBAL_CONFIG_PATHS",
            [temp_dir / "nonexistent.yaml"],
        )

        project_config = temp_dir / ".drift.yaml"
        project_data = {
            "conversations": {"mode": "all", "days": 30},
        }

        with open(project_config, "w") as f:
            yaml.dump(project_data, f)

        config = ConfigLoader.load_config(temp_dir)

        assert config.conversations.mode == ConversationMode.ALL
        assert config.conversations.days == 30

    def test_load_config_priority(self, temp_dir, monkeypatch):
        """Test config loading priority: project > global > default."""
        # Set up global config
        global_config = temp_dir / "global.yaml"
        global_data = {
            "conversations": {"mode": "last_n_days", "days": 14},
            "temp_dir": "/tmp/global",
        }
        with open(global_config, "w") as f:
            yaml.dump(global_data, f)

        monkeypatch.setattr(ConfigLoader, "GLOBAL_CONFIG_PATHS", [global_config])

        # Set up project config
        project_config = temp_dir / ".drift.yaml"
        project_data = {
            "conversations": {"days": 30},  # Override only days
        }
        with open(project_config, "w") as f:
            yaml.dump(project_data, f)

        config = ConfigLoader.load_config(temp_dir)

        # Mode from global (not overridden by project)
        assert config.conversations.mode == ConversationMode.LAST_N_DAYS
        # Days from project (highest priority)
        assert config.conversations.days == 30
        # Temp dir from global
        assert config.temp_dir == "/tmp/global"

    def test_validate_config_default_model_not_found(self):
        """Test validation fails when default model doesn't exist."""
        config = DriftConfig(
            models={},  # No models defined
            default_model="nonexistent",
            drift_learning_types={
                "test": DriftLearningType(
                    description="test",
                    detection_prompt="test",
                    analysis_method="ai_analyzed",
                    scope="turn_level",
                    context="test",
                    requires_project_context=False,
                )
            },
            agent_tools={"claude-code": AgentToolConfig(conversation_path="/tmp")},
        )

        with pytest.raises(ValueError) as exc_info:
            ConfigLoader._validate_config(config)
        assert "Default model 'nonexistent' not found" in str(exc_info.value)

    def test_validate_config_learning_type_model_not_found(
        self, sample_provider_config, sample_model_config
    ):
        """Test validation fails when learning type references unknown model."""
        config = DriftConfig(
            providers={"bedrock": sample_provider_config},
            models={"haiku": sample_model_config},
            default_model="haiku",
            drift_learning_types={
                "test": DriftLearningType(
                    description="test",
                    detection_prompt="test",
                    analysis_method="ai_analyzed",
                    scope="turn_level",
                    context="test",
                    requires_project_context=False,
                    model="nonexistent",
                )
            },
            agent_tools={"claude-code": AgentToolConfig(conversation_path="/tmp")},
        )

        with pytest.raises(ValueError) as exc_info:
            ConfigLoader._validate_config(config)
        assert "references unknown model 'nonexistent'" in str(exc_info.value)

    def test_validate_config_no_enabled_agent_tools(
        self, sample_provider_config, sample_model_config
    ):
        """Test validation fails when no agent tools are enabled."""
        config = DriftConfig(
            providers={"bedrock": sample_provider_config},
            models={"haiku": sample_model_config},
            default_model="haiku",
            drift_learning_types={
                "test": DriftLearningType(
                    description="test",
                    detection_prompt="test",
                    analysis_method="ai_analyzed",
                    scope="turn_level",
                    context="test",
                    requires_project_context=False,
                )
            },
            agent_tools={"claude-code": AgentToolConfig(conversation_path="/tmp", enabled=False)},
        )

        with pytest.raises(ValueError) as exc_info:
            ConfigLoader._validate_config(config)
        assert "At least one agent tool must be enabled" in str(exc_info.value)

    def test_validate_config_no_learning_types(self, sample_provider_config, sample_model_config):
        """Test validation fails when no learning types are defined."""
        config = DriftConfig(
            providers={"bedrock": sample_provider_config},
            models={"haiku": sample_model_config},
            default_model="haiku",
            drift_learning_types={},  # Empty
            agent_tools={"claude-code": AgentToolConfig(conversation_path="/tmp")},
        )

        with pytest.raises(ValueError) as exc_info:
            ConfigLoader._validate_config(config)
        assert "At least one drift learning type must be defined" in str(exc_info.value)

    def test_validate_config_success(self, sample_drift_config):
        """Test validation passes with valid config."""
        # Should not raise any exception
        ConfigLoader._validate_config(sample_drift_config)

    def test_load_config_invalid_raises_error(self, temp_dir, monkeypatch):
        """Test that loading invalid config raises ValueError."""
        monkeypatch.setattr(
            ConfigLoader,
            "GLOBAL_CONFIG_PATHS",
            [temp_dir / "nonexistent.yaml"],
        )

        project_config = temp_dir / ".drift.yaml"
        # Invalid: missing required field
        project_data = {
            "models": {
                "test": {
                    # Missing provider field
                    "model_id": "test",
                    "params": {"temperature": 0.5},
                }
            }
        }
        with open(project_config, "w") as f:
            yaml.dump(project_data, f)

        with pytest.raises(ValueError) as exc_info:
            ConfigLoader.load_config(temp_dir)
        assert "Invalid configuration" in str(exc_info.value)
