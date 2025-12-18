"""Tests for loading additional rules files from configuration."""

import yaml

from drift.config.loader import ConfigLoader


class TestConfigLoaderAdditionalFiles:
    """Tests for loading additional rules files from config."""

    def test_load_config_with_additional_rules_files_in_config(self, temp_dir, monkeypatch):
        """Test loading config with additional rules files defined in .drift.yaml."""
        monkeypatch.setattr(
            ConfigLoader,
            "GLOBAL_CONFIG_PATHS",
            [temp_dir / "nonexistent.yaml"],
        )

        # Create additional rules file 1
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

        # Create additional rules file 2
        rules_file2 = temp_dir / "rules2.yaml"
        rules_data2 = {
            "rule2": {
                "description": "Second rule",
                "scope": "project_level",
                "context": "Test",
                "requires_project_context": False,
            }
        }
        with open(rules_file2, "w") as f:
            yaml.dump(rules_data2, f)

        # Create project config referencing these files
        project_config = temp_dir / ".drift.yaml"
        project_data = {"additional_rules_files": ["rules1.yaml", "rules2.yaml"]}
        with open(project_config, "w") as f:
            yaml.dump(project_data, f)

        # Perform the load
        config = ConfigLoader.load_config(temp_dir)

        # Verify both rules are loaded
        assert "rule1" in config.rule_definitions
        assert "rule2" in config.rule_definitions
        assert config.rule_definitions["rule1"].description == "First rule"

    def test_additional_rules_override_default_rules(self, temp_dir, monkeypatch):
        """Test that additional rules override default rules (from .drift_rules.yaml)."""
        monkeypatch.setattr(
            ConfigLoader,
            "GLOBAL_CONFIG_PATHS",
            [temp_dir / "nonexistent.yaml"],
        )

        # Create default rules file
        default_rules = temp_dir / ".drift_rules.yaml"
        default_data = {
            "rule1": {
                "description": "Default description",
                "scope": "conversation_level",
                "context": "Test",
                "requires_project_context": False,
            }
        }
        with open(default_rules, "w") as f:
            yaml.dump(default_data, f)

        # Create overriding rules file
        override_file = temp_dir / "override.yaml"
        override_data = {
            "rule1": {
                "description": "Overridden description",
                "scope": "conversation_level",
                "context": "Test",
                "requires_project_context": False,
            }
        }
        with open(override_file, "w") as f:
            yaml.dump(override_data, f)

        # Create project config
        project_config = temp_dir / ".drift.yaml"
        project_data = {"additional_rules_files": ["override.yaml"]}
        with open(project_config, "w") as f:
            yaml.dump(project_data, f)

        # Perform the load
        config = ConfigLoader.load_config(temp_dir)

        # Verify override happened
        assert "rule1" in config.rule_definitions
        assert config.rule_definitions["rule1"].description == "Overridden description"
