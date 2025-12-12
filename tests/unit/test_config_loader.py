"""Unit tests for configuration loader."""

import pytest
import yaml

from drift.config.loader import ConfigLoader
from drift.config.models import AgentToolConfig, ConversationMode, DriftConfig, RuleDefinition


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
        from drift.config.models import PhaseDefinition

        config = DriftConfig(
            models={},  # No models defined
            default_model="nonexistent",
            rule_definitions={
                "test": RuleDefinition(
                    description="test",
                    scope="conversation_level",
                    context="test",
                    requires_project_context=False,
                    phases=[
                        PhaseDefinition(
                            name="detection",
                            type="prompt",
                            prompt="test",
                        )
                    ],
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
        from drift.config.models import PhaseDefinition

        config = DriftConfig(
            providers={"bedrock": sample_provider_config},
            models={"haiku": sample_model_config},
            default_model="haiku",
            rule_definitions={
                "test": RuleDefinition(
                    description="test",
                    scope="conversation_level",
                    context="test",
                    requires_project_context=False,
                    phases=[
                        PhaseDefinition(
                            name="detection",
                            type="prompt",
                            prompt="test",
                            model="nonexistent",
                        )
                    ],
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
        from drift.config.models import PhaseDefinition

        config = DriftConfig(
            providers={"bedrock": sample_provider_config},
            models={"haiku": sample_model_config},
            default_model="haiku",
            rule_definitions={
                "test": RuleDefinition(
                    description="test",
                    scope="conversation_level",
                    context="test",
                    requires_project_context=False,
                    phases=[
                        PhaseDefinition(
                            name="detection",
                            type="prompt",
                            prompt="test",
                        )
                    ],
                )
            },
            agent_tools={"claude-code": AgentToolConfig(conversation_path="/tmp", enabled=False)},
        )

        with pytest.raises(ValueError) as exc_info:
            ConfigLoader._validate_config(config)
        assert "At least one agent tool must be enabled" in str(exc_info.value)

    def test_validate_config_no_learning_types(self, sample_provider_config, sample_model_config):
        """Test validation with no learning types (allows project-specific configs)."""
        config = DriftConfig(
            providers={"bedrock": sample_provider_config},
            models={"haiku": sample_model_config},
            default_model="haiku",
            rule_definitions={},  # Empty - this is now allowed
            agent_tools={"claude-code": AgentToolConfig(conversation_path="/tmp")},
        )

        # Should not raise - empty learning types are allowed
        ConfigLoader._validate_config(config)

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


class TestRulesFileLoading:
    """Tests for rules file loading functionality (issue #31)."""

    def test_is_remote_url_http(self):
        """Test detection of HTTP URLs."""
        assert ConfigLoader._is_remote_url("http://example.com/rules.yaml")

    def test_is_remote_url_https(self):
        """Test detection of HTTPS URLs."""
        assert ConfigLoader._is_remote_url("https://example.com/rules.yaml")

    def test_is_remote_url_local_path(self):
        """Test detection of local paths."""
        assert not ConfigLoader._is_remote_url("/path/to/file.yaml")
        assert not ConfigLoader._is_remote_url("relative/path/file.yaml")
        assert not ConfigLoader._is_remote_url("~/path/file.yaml")

    def test_is_remote_url_file_scheme(self):
        """Test that file:// URLs are not considered remote."""
        assert not ConfigLoader._is_remote_url("file:///path/to/file.yaml")

    def test_merge_rules_non_overlapping(self):
        """Test merging rules with no overlap."""
        base = {
            "rule1": {"description": "First rule"},
            "rule2": {"description": "Second rule"},
        }
        new = {
            "rule3": {"description": "Third rule"},
            "rule4": {"description": "Fourth rule"},
        }

        result = ConfigLoader._merge_rules(base, new)

        assert len(result) == 4
        assert "rule1" in result
        assert "rule2" in result
        assert "rule3" in result
        assert "rule4" in result

    def test_merge_rules_overlapping(self):
        """Test merging rules with overlap (later overrides earlier)."""
        base = {
            "rule1": {"description": "Original description", "group_name": "GroupA"},
            "rule2": {"description": "Second rule", "group_name": "GroupB"},
        }
        new = {
            "rule1": {"description": "Updated description", "group_name": "GroupA"},
            "rule3": {"description": "Third rule", "group_name": "GroupC"},
        }

        result = ConfigLoader._merge_rules(base, new)

        assert len(result) == 3
        assert result["rule1"]["description"] == "Updated description"
        assert result["rule2"]["description"] == "Second rule"
        assert result["rule3"]["description"] == "Third rule"

    def test_merge_rules_preserves_original(self):
        """Test that merge doesn't modify original dictionaries."""
        base = {"rule1": {"description": "Original"}}
        new = {"rule2": {"description": "New"}}

        result = ConfigLoader._merge_rules(base, new)

        assert base == {"rule1": {"description": "Original"}}
        assert new == {"rule2": {"description": "New"}}
        assert len(result) == 2

    def test_load_rules_file_local_exists(self, temp_dir):
        """Test loading rules from existing local file."""
        rules_file = temp_dir / "rules.yaml"
        rules_data = {
            "test_rule": {
                "description": "Test rule",
                "scope": "conversation_level",
            }
        }

        with open(rules_file, "w") as f:
            yaml.dump(rules_data, f)

        result = ConfigLoader._load_rules_file(str(rules_file))
        assert result == rules_data

    def test_load_rules_file_local_absolute_path(self, temp_dir):
        """Test loading rules from absolute path."""
        rules_file = temp_dir / "rules.yaml"
        rules_data = {"rule1": {"description": "Test"}}

        with open(rules_file, "w") as f:
            yaml.dump(rules_data, f)

        result = ConfigLoader._load_rules_file(str(rules_file.absolute()))
        assert result == rules_data

    def test_load_rules_file_local_relative_path(self, temp_dir, monkeypatch):
        """Test loading rules from relative path."""
        monkeypatch.chdir(temp_dir)

        rules_file = temp_dir / "rules.yaml"
        rules_data = {"rule1": {"description": "Test"}}

        with open(rules_file, "w") as f:
            yaml.dump(rules_data, f)

        result = ConfigLoader._load_rules_file("rules.yaml")
        assert result == rules_data

    def test_load_rules_file_local_home_expansion(self, temp_dir, monkeypatch):
        """Test loading rules with home directory expansion."""
        import os

        # Create a file in a temp directory
        rules_dir = temp_dir / "rules"
        rules_dir.mkdir()
        rules_file = rules_dir / "rules.yaml"
        rules_data = {"rule1": {"description": "Test"}}

        with open(rules_file, "w") as f:
            yaml.dump(rules_data, f)

        # Mock expanduser to expand ~ to our temp directory
        original_expanduser = os.path.expanduser

        def mock_expanduser(path):
            if path.startswith("~"):
                return str(temp_dir) + path[1:]
            return original_expanduser(path)

        monkeypatch.setattr("os.path.expanduser", mock_expanduser)

        # Test with tilde path
        result = ConfigLoader._load_rules_file("~/rules/rules.yaml")
        assert result == rules_data

    def test_load_rules_file_local_not_found(self, temp_dir):
        """Test loading rules from non-existent local file."""
        with pytest.raises(ValueError) as exc_info:
            ConfigLoader._load_rules_file(str(temp_dir / "missing.yaml"))
        assert "Rules file not found" in str(exc_info.value)

    def test_load_rules_file_local_invalid_yaml(self, temp_dir):
        """Test loading rules from file with invalid YAML."""
        rules_file = temp_dir / "invalid.yaml"
        rules_file.write_text("invalid: yaml: content:\n  - broken")

        with pytest.raises(ValueError) as exc_info:
            ConfigLoader._load_rules_file(str(rules_file))
        assert "Invalid YAML in rules file" in str(exc_info.value)

    def test_load_rules_file_local_empty(self, temp_dir):
        """Test loading rules from empty file."""
        rules_file = temp_dir / "empty.yaml"
        rules_file.write_text("")

        result = ConfigLoader._load_rules_file(str(rules_file))
        assert result == {}

    def test_load_remote_rules_success(self, monkeypatch):
        """Test loading rules from remote URL successfully."""
        import requests

        rules_data = {"remote_rule": {"description": "Remote rule"}}
        yaml_content = yaml.dump(rules_data)

        class MockResponse:
            text = yaml_content
            status_code = 200

            def raise_for_status(self):
                pass

        def mock_get(url, timeout):
            assert url == "https://example.com/rules.yaml"
            assert timeout == ConfigLoader.RULES_FETCH_TIMEOUT
            return MockResponse()

        monkeypatch.setattr(requests, "get", mock_get)

        result = ConfigLoader._load_remote_rules("https://example.com/rules.yaml")
        assert result == rules_data

    def test_load_remote_rules_timeout(self, monkeypatch):
        """Test timeout when fetching remote rules."""
        import requests

        def mock_get(url, timeout):
            raise requests.exceptions.Timeout()

        monkeypatch.setattr(requests, "get", mock_get)

        with pytest.raises(ValueError) as exc_info:
            ConfigLoader._load_remote_rules("https://example.com/rules.yaml")
        assert "Timeout fetching rules" in str(exc_info.value)
        assert "10s" in str(exc_info.value)

    def test_load_remote_rules_http_error(self, monkeypatch):
        """Test HTTP error when fetching remote rules."""
        import requests

        class MockResponse:
            status_code = 404

            def raise_for_status(self):
                raise requests.exceptions.HTTPError("404 Not Found")

        def mock_get(url, timeout):
            return MockResponse()

        monkeypatch.setattr(requests, "get", mock_get)

        with pytest.raises(ValueError) as exc_info:
            ConfigLoader._load_remote_rules("https://example.com/rules.yaml")
        assert "Error fetching rules" in str(exc_info.value)

    def test_load_remote_rules_connection_error(self, monkeypatch):
        """Test connection error when fetching remote rules."""
        import requests

        def mock_get(url, timeout):
            raise requests.exceptions.ConnectionError("Network unreachable")

        monkeypatch.setattr(requests, "get", mock_get)

        with pytest.raises(ValueError) as exc_info:
            ConfigLoader._load_remote_rules("https://example.com/rules.yaml")
        assert "Error fetching rules" in str(exc_info.value)

    def test_load_remote_rules_invalid_yaml(self, monkeypatch):
        """Test invalid YAML in remote rules file."""
        import requests

        class MockResponse:
            text = "invalid: yaml: content:\n  - broken"
            status_code = 200

            def raise_for_status(self):
                pass

        def mock_get(url, timeout):
            return MockResponse()

        monkeypatch.setattr(requests, "get", mock_get)

        with pytest.raises(ValueError) as exc_info:
            ConfigLoader._load_remote_rules("https://example.com/rules.yaml")
        assert "Invalid YAML in remote rules file" in str(exc_info.value)

    def test_load_remote_rules_empty(self, monkeypatch):
        """Test loading empty remote rules file."""
        import requests

        class MockResponse:
            text = ""
            status_code = 200

            def raise_for_status(self):
                pass

        def mock_get(url, timeout):
            return MockResponse()

        monkeypatch.setattr(requests, "get", mock_get)

        result = ConfigLoader._load_remote_rules("https://example.com/rules.yaml")
        assert result == {}

    def test_load_config_with_single_rules_file(self, temp_dir, monkeypatch):
        """Test loading config with single rules file."""
        monkeypatch.setattr(
            ConfigLoader,
            "GLOBAL_CONFIG_PATHS",
            [temp_dir / "nonexistent.yaml"],
        )

        # Create rules file
        rules_file = temp_dir / "rules.yaml"
        rules_data = {
            "custom_rule": {
                "description": "Custom rule from file",
                "scope": "conversation_level",
                "context": "Test context",
                "requires_project_context": False,
            }
        }
        with open(rules_file, "w") as f:
            yaml.dump(rules_data, f)

        config = ConfigLoader.load_config(temp_dir, rules_files=[str(rules_file)])

        assert "custom_rule" in config.rule_definitions
        assert config.rule_definitions["custom_rule"].description == "Custom rule from file"

    def test_load_config_with_multiple_rules_files(self, temp_dir, monkeypatch):
        """Test loading config with multiple rules files."""
        monkeypatch.setattr(
            ConfigLoader,
            "GLOBAL_CONFIG_PATHS",
            [temp_dir / "nonexistent.yaml"],
        )

        # Create first rules file
        rules_file1 = temp_dir / "rules1.yaml"
        rules_data1 = {
            "rule1": {
                "description": "First rule",
                "scope": "conversation_level",
                "context": "Test",
                "requires_project_context": False,
            }
        }
        with open(rules_file1, "w") as f:
            yaml.dump(rules_data1, f)

        # Create second rules file
        rules_file2 = temp_dir / "rules2.yaml"
        rules_data2 = {
            "rule2": {
                "description": "Second rule",
                "scope": "conversation_level",
                "context": "Test",
                "requires_project_context": False,
            }
        }
        with open(rules_file2, "w") as f:
            yaml.dump(rules_data2, f)

        config = ConfigLoader.load_config(
            temp_dir, rules_files=[str(rules_file1), str(rules_file2)]
        )

        assert "rule1" in config.rule_definitions
        assert "rule2" in config.rule_definitions

    def test_load_config_rules_file_override_priority(self, temp_dir, monkeypatch):
        """Test that later rules files override earlier ones."""
        monkeypatch.setattr(
            ConfigLoader,
            "GLOBAL_CONFIG_PATHS",
            [temp_dir / "nonexistent.yaml"],
        )

        # Create first rules file with rule1
        rules_file1 = temp_dir / "rules1.yaml"
        rules_data1 = {
            "shared_rule": {
                "description": "Original description",
                "scope": "conversation_level",
                "context": "Original",
                "requires_project_context": False,
                "group_name": "TestGroup",
            }
        }
        with open(rules_file1, "w") as f:
            yaml.dump(rules_data1, f)

        # Create second rules file that overrides rule1
        rules_file2 = temp_dir / "rules2.yaml"
        rules_data2 = {
            "shared_rule": {
                "description": "Updated description",
                "scope": "conversation_level",
                "context": "Updated",
                "requires_project_context": True,
                "group_name": "TestGroup",
            }
        }
        with open(rules_file2, "w") as f:
            yaml.dump(rules_data2, f)

        config = ConfigLoader.load_config(
            temp_dir, rules_files=[str(rules_file1), str(rules_file2)]
        )

        assert config.rule_definitions["shared_rule"].description == "Updated description"
        assert config.rule_definitions["shared_rule"].scope == "conversation_level"

    def test_load_config_with_default_rules_file(self, temp_dir, monkeypatch):
        """Test loading config with .drift_rules.yaml in project root."""
        monkeypatch.setattr(
            ConfigLoader,
            "GLOBAL_CONFIG_PATHS",
            [temp_dir / "nonexistent.yaml"],
        )

        # Create .drift_rules.yaml
        default_rules_file = temp_dir / ".drift_rules.yaml"
        rules_data = {
            "default_rule": {
                "description": "Rule from .drift_rules.yaml",
                "scope": "conversation_level",
                "context": "Test",
                "requires_project_context": False,
            }
        }
        with open(default_rules_file, "w") as f:
            yaml.dump(rules_data, f)

        config = ConfigLoader.load_config(temp_dir)

        assert "default_rule" in config.rule_definitions
        assert config.rule_definitions["default_rule"].description == "Rule from .drift_rules.yaml"

    def test_load_config_cli_rules_exclude_drift_rules_yaml(self, temp_dir, monkeypatch):
        """Test that CLI rules file excludes .drift_rules.yaml (issue #54)."""
        monkeypatch.setattr(
            ConfigLoader,
            "GLOBAL_CONFIG_PATHS",
            [temp_dir / "nonexistent.yaml"],
        )

        # Create .drift_rules.yaml (should be ignored when CLI rules provided)
        default_rules_file = temp_dir / ".drift_rules.yaml"
        default_rules = {
            "default_rule": {
                "description": "From .drift_rules.yaml",
                "scope": "conversation_level",
                "context": "Default",
                "requires_project_context": False,
            }
        }
        with open(default_rules_file, "w") as f:
            yaml.dump(default_rules, f)

        # Create CLI rules file
        cli_rules_file = temp_dir / "cli_rules.yaml"
        cli_rules = {
            "cli_rule": {
                "description": "From CLI",
                "scope": "conversation_level",
                "context": "CLI",
                "requires_project_context": True,
            }
        }
        with open(cli_rules_file, "w") as f:
            yaml.dump(cli_rules, f)

        config = ConfigLoader.load_config(temp_dir, rules_files=[str(cli_rules_file)])

        # Only CLI rule should be present
        assert "cli_rule" in config.rule_definitions
        assert "default_rule" not in config.rule_definitions
        assert config.rule_definitions["cli_rule"].description == "From CLI"

    def test_load_config_priority_default_rules_over_drift_yaml(self, temp_dir, monkeypatch):
        """Test that .drift_rules.yaml overrides rule_definitions in .drift.yaml."""
        monkeypatch.setattr(
            ConfigLoader,
            "GLOBAL_CONFIG_PATHS",
            [temp_dir / "nonexistent.yaml"],
        )

        # Create .drift.yaml with rule_definitions
        drift_yaml = temp_dir / ".drift.yaml"
        drift_config = {
            "rule_definitions": {
                "shared_rule": {
                    "description": "From .drift.yaml",
                    "scope": "conversation_level",
                    "context": "Config",
                    "requires_project_context": False,
                    "group_name": "TestGroup",
                }
            }
        }
        with open(drift_yaml, "w") as f:
            yaml.dump(drift_config, f)

        # Create .drift_rules.yaml
        default_rules_file = temp_dir / ".drift_rules.yaml"
        default_rules = {
            "shared_rule": {
                "description": "From .drift_rules.yaml",
                "scope": "conversation_level",
                "context": "Rules file",
                "requires_project_context": True,
                "group_name": "TestGroup",
            }
        }
        with open(default_rules_file, "w") as f:
            yaml.dump(default_rules, f)

        config = ConfigLoader.load_config(temp_dir)

        assert config.rule_definitions["shared_rule"].description == "From .drift_rules.yaml"
        assert config.rule_definitions["shared_rule"].scope == "conversation_level"

    def test_load_config_combines_rules_from_default_sources(self, temp_dir, monkeypatch):
        """Test that rules from default sources are combined when no CLI rules provided."""
        monkeypatch.setattr(
            ConfigLoader,
            "GLOBAL_CONFIG_PATHS",
            [temp_dir / "nonexistent.yaml"],
        )

        # Create .drift.yaml with rule_definitions
        drift_yaml = temp_dir / ".drift.yaml"
        drift_config = {
            "rule_definitions": {
                "rule_from_config": {
                    "description": "From .drift.yaml",
                    "scope": "conversation_level",
                    "context": "Config",
                    "requires_project_context": False,
                }
            }
        }
        with open(drift_yaml, "w") as f:
            yaml.dump(drift_config, f)

        # Create .drift_rules.yaml
        default_rules_file = temp_dir / ".drift_rules.yaml"
        default_rules = {
            "rule_from_default": {
                "description": "From .drift_rules.yaml",
                "scope": "conversation_level",
                "context": "Default rules",
                "requires_project_context": False,
            }
        }
        with open(default_rules_file, "w") as f:
            yaml.dump(default_rules, f)

        # Load config WITHOUT CLI rules files (uses defaults)
        config = ConfigLoader.load_config(temp_dir)

        # Both default rules should be present (from .drift.yaml and .drift_rules.yaml)
        assert "rule_from_config" in config.rule_definitions
        assert "rule_from_default" in config.rule_definitions

    def test_load_config_rules_file_not_found_error(self, temp_dir, monkeypatch):
        """Test error when specified rules file doesn't exist."""
        monkeypatch.setattr(
            ConfigLoader,
            "GLOBAL_CONFIG_PATHS",
            [temp_dir / "nonexistent.yaml"],
        )

        with pytest.raises(ValueError) as exc_info:
            ConfigLoader.load_config(temp_dir, rules_files=["missing_rules.yaml"])

        assert "Error loading rules file 'missing_rules.yaml'" in str(exc_info.value)
        assert "Rules file not found" in str(exc_info.value)

    def test_load_config_rules_file_invalid_yaml_error(self, temp_dir, monkeypatch):
        """Test error when rules file contains invalid YAML."""
        monkeypatch.setattr(
            ConfigLoader,
            "GLOBAL_CONFIG_PATHS",
            [temp_dir / "nonexistent.yaml"],
        )

        invalid_file = temp_dir / "invalid.yaml"
        invalid_file.write_text("invalid: yaml: content:\n  - broken")

        with pytest.raises(ValueError) as exc_info:
            ConfigLoader.load_config(temp_dir, rules_files=[str(invalid_file)])

        assert "Error loading rules file" in str(exc_info.value)
        assert "Invalid YAML" in str(exc_info.value)

    def test_load_config_default_rules_file_error(self, temp_dir, monkeypatch):
        """Test error when .drift_rules.yaml is invalid."""
        monkeypatch.setattr(
            ConfigLoader,
            "GLOBAL_CONFIG_PATHS",
            [temp_dir / "nonexistent.yaml"],
        )

        # Create invalid .drift_rules.yaml
        default_rules_file = temp_dir / ".drift_rules.yaml"
        default_rules_file.write_text("invalid: yaml: content:\n  - broken")

        with pytest.raises(ValueError) as exc_info:
            ConfigLoader.load_config(temp_dir)

        assert "Error loading .drift_rules.yaml" in str(exc_info.value)

    def test_load_config_cli_rules_exclude_defaults(self, temp_dir, monkeypatch):
        """Test that CLI rules files exclude default rule locations (issue #54)."""
        monkeypatch.setattr(
            ConfigLoader,
            "GLOBAL_CONFIG_PATHS",
            [temp_dir / "nonexistent.yaml"],
        )

        # Create .drift.yaml with rule_definitions
        drift_yaml = temp_dir / ".drift.yaml"
        drift_config = {
            "rule_definitions": {
                "rule_from_config": {
                    "description": "From .drift.yaml",
                    "scope": "conversation_level",
                    "context": "Config",
                    "requires_project_context": False,
                }
            }
        }
        with open(drift_yaml, "w") as f:
            yaml.dump(drift_config, f)

        # Create .drift_rules.yaml
        default_rules_file = temp_dir / ".drift_rules.yaml"
        default_rules = {
            "rule_from_default": {
                "description": "From .drift_rules.yaml",
                "scope": "conversation_level",
                "context": "Default rules",
                "requires_project_context": False,
            }
        }
        with open(default_rules_file, "w") as f:
            yaml.dump(default_rules, f)

        # Create CLI rules file
        cli_rules_file = temp_dir / "cli_rules.yaml"
        cli_rules = {
            "rule_from_cli": {
                "description": "From CLI",
                "scope": "conversation_level",
                "context": "CLI",
                "requires_project_context": False,
            }
        }
        with open(cli_rules_file, "w") as f:
            yaml.dump(cli_rules, f)

        # Load config with CLI rules file
        config = ConfigLoader.load_config(temp_dir, rules_files=[str(cli_rules_file)])

        # ONLY CLI rule should be present (default locations excluded)
        assert "rule_from_cli" in config.rule_definitions
        assert "rule_from_config" not in config.rule_definitions
        assert "rule_from_default" not in config.rule_definitions

    def test_load_config_cli_rules_empty_list_uses_defaults(self, temp_dir, monkeypatch):
        """Test that empty rules_files list is treated as None (uses defaults)."""
        monkeypatch.setattr(
            ConfigLoader,
            "GLOBAL_CONFIG_PATHS",
            [temp_dir / "nonexistent.yaml"],
        )

        # Create .drift.yaml with rule_definitions
        drift_yaml = temp_dir / ".drift.yaml"
        drift_config = {
            "rule_definitions": {
                "rule_from_config": {
                    "description": "From .drift.yaml",
                    "scope": "conversation_level",
                    "context": "Config",
                    "requires_project_context": False,
                }
            }
        }
        with open(drift_yaml, "w") as f:
            yaml.dump(drift_config, f)

        # Load config with empty rules_files list
        config = ConfigLoader.load_config(temp_dir, rules_files=[])

        # Should use default locations since rules_files is empty
        assert "rule_from_config" in config.rule_definitions

    def test_load_config_multiple_cli_rules_exclude_defaults(self, temp_dir, monkeypatch):
        """Test that multiple CLI rules files exclude default locations."""
        monkeypatch.setattr(
            ConfigLoader,
            "GLOBAL_CONFIG_PATHS",
            [temp_dir / "nonexistent.yaml"],
        )

        # Create default rules that should be ignored
        drift_yaml = temp_dir / ".drift.yaml"
        drift_config = {
            "rule_definitions": {
                "default_rule": {
                    "description": "Should be ignored",
                    "scope": "conversation_level",
                    "context": "Default",
                    "requires_project_context": False,
                }
            }
        }
        with open(drift_yaml, "w") as f:
            yaml.dump(drift_config, f)

        # Create first CLI rules file
        rules_file1 = temp_dir / "rules1.yaml"
        rules_data1 = {
            "cli_rule1": {
                "description": "First CLI rule",
                "scope": "conversation_level",
                "context": "CLI1",
                "requires_project_context": False,
            }
        }
        with open(rules_file1, "w") as f:
            yaml.dump(rules_data1, f)

        # Create second CLI rules file
        rules_file2 = temp_dir / "rules2.yaml"
        rules_data2 = {
            "cli_rule2": {
                "description": "Second CLI rule",
                "scope": "conversation_level",
                "context": "CLI2",
                "requires_project_context": False,
            }
        }
        with open(rules_file2, "w") as f:
            yaml.dump(rules_data2, f)

        # Load config with multiple CLI rules files
        config = ConfigLoader.load_config(
            temp_dir, rules_files=[str(rules_file1), str(rules_file2)]
        )

        # Only CLI rules should be present
        assert "cli_rule1" in config.rule_definitions
        assert "cli_rule2" in config.rule_definitions
        assert "default_rule" not in config.rule_definitions
