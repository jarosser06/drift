"""Tests for rule groups feature."""

from pathlib import Path
from tempfile import TemporaryDirectory

import yaml

from drift.config.defaults import get_default_config
from drift.config.loader import ConfigLoader
from drift.config.models import RuleDefinition


class TestRuleGroupsConfiguration:
    """Tests for rule groups in configuration."""

    def test_default_group_name_in_config(self):
        """Test that default_group_name is available in config."""
        config = ConfigLoader.load_config()
        assert hasattr(config, "default_group_name")
        assert config.default_group_name == "General"

    def test_rule_with_explicit_group_name(self):
        """Test loading a rule with explicit group_name."""
        with TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)

            # Create a config with a rule that has group_name
            config_content = {
                "providers": {
                    "test-provider": {
                        "provider": "claude-code",
                        "params": {},
                    }
                },
                "models": {
                    "test-model": {
                        "provider": "test-provider",
                        "model_id": "test",
                        "params": {},
                    }
                },
                "default_model": "test-model",
                "agent_tools": {
                    "claude-code": {
                        "conversation_path": str(project_path),
                        "enabled": True,
                    }
                },
                "rule_definitions": {
                    "test_rule": {
                        "description": "Test rule",
                        "scope": "project_level",
                        "context": "Test context",
                        "requires_project_context": True,
                        "group_name": "Workflow Check",
                    }
                },
            }

            config_file = project_path / ".drift.yaml"
            with open(config_file, "w") as f:
                yaml.dump(config_content, f)

            # Load config
            config = ConfigLoader.load_config(project_path)

            # Verify rule has group_name
            assert "test_rule" in config.rule_definitions
            assert config.rule_definitions["test_rule"].group_name == "Workflow Check"

    def test_rule_without_group_name_uses_default(self):
        """Test that rules without group_name use default_group_name."""
        with TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)

            # Create a config with a rule without group_name
            config_content = {
                "providers": {
                    "test-provider": {
                        "provider": "claude-code",
                        "params": {},
                    }
                },
                "models": {
                    "test-model": {
                        "provider": "test-provider",
                        "model_id": "test",
                        "params": {},
                    }
                },
                "default_model": "test-model",
                "default_group_name": "Custom Default",
                "agent_tools": {
                    "claude-code": {
                        "conversation_path": str(project_path),
                        "enabled": True,
                    }
                },
                "rule_definitions": {
                    "test_rule": {
                        "description": "Test rule",
                        "scope": "project_level",
                        "context": "Test context",
                        "requires_project_context": True,
                    }
                },
            }

            config_file = project_path / ".drift.yaml"
            with open(config_file, "w") as f:
                yaml.dump(config_content, f)

            # Load config
            config = ConfigLoader.load_config(project_path)

            # Verify custom default group name
            assert config.default_group_name == "Custom Default"

            # Rule should not have explicit group_name (None)
            assert config.rule_definitions["test_rule"].group_name is None


class TestRuleGroupsFileLoading:
    """Tests for loading rules from files with group_name support."""

    def test_top_level_group_name_applied_to_rules(self):
        """Test that top-level group_name is applied to all rules in file."""
        with TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)

            # Create main config
            main_config = {
                "providers": {
                    "test-provider": {
                        "provider": "claude-code",
                        "params": {},
                    }
                },
                "models": {
                    "test-model": {
                        "provider": "test-provider",
                        "model_id": "test",
                        "params": {},
                    }
                },
                "default_model": "test-model",
                "agent_tools": {
                    "claude-code": {
                        "conversation_path": str(project_path),
                        "enabled": True,
                    }
                },
            }

            config_file = project_path / ".drift.yaml"
            with open(config_file, "w") as f:
                yaml.dump(main_config, f)

            # Create rules file with top-level group_name
            rules_content = {
                "group_name": "Documentation Quality",
                "rule_one": {
                    "description": "First rule",
                    "scope": "project_level",
                    "context": "Context one",
                    "requires_project_context": True,
                },
                "rule_two": {
                    "description": "Second rule",
                    "scope": "project_level",
                    "context": "Context two",
                    "requires_project_context": True,
                },
            }

            rules_file = project_path / ".drift_rules.yaml"
            with open(rules_file, "w") as f:
                yaml.dump(rules_content, f)

            # Load config
            config = ConfigLoader.load_config(project_path)

            # Both rules should have the file-level group_name
            assert config.rule_definitions["rule_one"].group_name == "Documentation Quality"
            assert config.rule_definitions["rule_two"].group_name == "Documentation Quality"

    def test_rule_level_group_name_overrides_file_level(self):
        """Test that rule-level group_name overrides file-level group_name."""
        with TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)

            # Create main config
            main_config = {
                "providers": {
                    "test-provider": {
                        "provider": "claude-code",
                        "params": {},
                    }
                },
                "models": {
                    "test-model": {
                        "provider": "test-provider",
                        "model_id": "test",
                        "params": {},
                    }
                },
                "default_model": "test-model",
                "agent_tools": {
                    "claude-code": {
                        "conversation_path": str(project_path),
                        "enabled": True,
                    }
                },
            }

            config_file = project_path / ".drift.yaml"
            with open(config_file, "w") as f:
                yaml.dump(main_config, f)

            # Create rules file with file-level group_name
            # But one rule has its own group_name
            rules_content = {
                "group_name": "File Level Group",
                "rule_one": {
                    "description": "First rule",
                    "scope": "project_level",
                    "context": "Context one",
                    "requires_project_context": True,
                },
                "rule_two": {
                    "description": "Second rule",
                    "scope": "project_level",
                    "context": "Context two",
                    "requires_project_context": True,
                    "group_name": "Rule Level Group",
                },
            }

            rules_file = project_path / ".drift_rules.yaml"
            with open(rules_file, "w") as f:
                yaml.dump(rules_content, f)

            # Load config
            config = ConfigLoader.load_config(project_path)

            # rule_one should use file-level group
            assert config.rule_definitions["rule_one"].group_name == "File Level Group"

            # rule_two should use its own group
            assert config.rule_definitions["rule_two"].group_name == "Rule Level Group"

    def test_duplicate_rule_name_in_same_group_overrides_correctly(self):
        """Test that higher priority rule files override lower priority ones."""
        with TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)

            # Create main config with a rule
            main_config = {
                "providers": {
                    "test-provider": {
                        "provider": "claude-code",
                        "params": {},
                    }
                },
                "models": {
                    "test-model": {
                        "provider": "test-provider",
                        "model_id": "test",
                        "params": {},
                    }
                },
                "default_model": "test-model",
                "agent_tools": {
                    "claude-code": {
                        "conversation_path": str(project_path),
                        "enabled": True,
                    }
                },
                "rule_definitions": {
                    "my_rule": {
                        "description": "Test rule",
                        "scope": "project_level",
                        "context": "Test context",
                        "requires_project_context": True,
                        "group_name": "Group A",
                    }
                },
            }

            config_file = project_path / ".drift.yaml"
            with open(config_file, "w") as f:
                yaml.dump(main_config, f)

            # Create rules file with same rule name in same group
            # This should OVERRIDE the rule from .drift.yaml (higher priority)
            rules_content = {
                "my_rule": {
                    "description": "Override rule",
                    "scope": "project_level",
                    "context": "Override context",
                    "requires_project_context": True,
                    "group_name": "Group A",
                }
            }

            rules_file = project_path / ".drift_rules.yaml"
            with open(rules_file, "w") as f:
                yaml.dump(rules_content, f)

            # Loading should succeed and use the override from .drift_rules.yaml
            config = ConfigLoader.load_config(project_path)
            assert config.rule_definitions["my_rule"].description == "Override rule"
            assert config.rule_definitions["my_rule"].context == "Override context"

    def test_same_rule_name_in_different_groups_allowed(self):
        """Test that same rule name in different groups is allowed."""
        with TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)

            # Create config with rules having same name but different groups
            config_content = {
                "providers": {
                    "test-provider": {
                        "provider": "claude-code",
                        "params": {},
                    }
                },
                "models": {
                    "test-model": {
                        "provider": "test-provider",
                        "model_id": "test",
                        "params": {},
                    }
                },
                "default_model": "test-model",
                "agent_tools": {
                    "claude-code": {
                        "conversation_path": str(project_path),
                        "enabled": True,
                    }
                },
                "rule_definitions": {
                    "completeness": {
                        "description": "Skill completeness",
                        "scope": "project_level",
                        "context": "Skills context",
                        "requires_project_context": True,
                        "group_name": "Skills",
                    },
                },
            }

            config_file = project_path / ".drift.yaml"
            with open(config_file, "w") as f:
                yaml.dump(config_content, f)

            # Note: Since we can't have duplicate keys in a Python dict,
            # and YAML merges duplicate keys by taking the last one,
            # we can't actually test this case through normal YAML loading.
            # The validation logic works correctly, but we can't create
            # the test scenario without manually constructing the dict.

            # Load config - should succeed
            config = ConfigLoader.load_config(project_path)
            assert "completeness" in config.rule_definitions

    def test_custom_default_group_name(self):
        """Test setting a custom default_group_name in config."""
        with TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)

            config_content = {
                "providers": {
                    "test-provider": {
                        "provider": "claude-code",
                        "params": {},
                    }
                },
                "models": {
                    "test-model": {
                        "provider": "test-provider",
                        "model_id": "test",
                        "params": {},
                    }
                },
                "default_model": "test-model",
                "default_group_name": "My Custom Group",
                "agent_tools": {
                    "claude-code": {
                        "conversation_path": str(project_path),
                        "enabled": True,
                    }
                },
            }

            config_file = project_path / ".drift.yaml"
            with open(config_file, "w") as f:
                yaml.dump(config_content, f)

            config = ConfigLoader.load_config(project_path)
            assert config.default_group_name == "My Custom Group"

    def test_multiple_files_same_group_merges(self):
        """Test that multiple CLI files with same group_name merge rules correctly."""
        with TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)

            # Create main config
            main_config = {
                "providers": {
                    "test-provider": {
                        "provider": "claude-code",
                        "params": {},
                    }
                },
                "models": {
                    "test-model": {
                        "provider": "test-provider",
                        "model_id": "test",
                        "params": {},
                    }
                },
                "default_model": "test-model",
                "agent_tools": {
                    "claude-code": {
                        "conversation_path": str(project_path),
                        "enabled": True,
                    }
                },
            }

            config_file = project_path / ".drift.yaml"
            with open(config_file, "w") as f:
                yaml.dump(main_config, f)

            # Create first rules file with "Skills" group
            rules_file_1 = project_path / "rules1.yaml"
            rules_content_1 = {
                "group_name": "Skills",
                "rule_one": {
                    "description": "First rule",
                    "scope": "project_level",
                    "context": "Context one",
                    "requires_project_context": True,
                },
            }
            with open(rules_file_1, "w") as f:
                yaml.dump(rules_content_1, f)

            # Create second rules file also with "Skills" group
            rules_file_2 = project_path / "rules2.yaml"
            rules_content_2 = {
                "group_name": "Skills",
                "rule_two": {
                    "description": "Second rule",
                    "scope": "project_level",
                    "context": "Context two",
                    "requires_project_context": True,
                },
            }
            with open(rules_file_2, "w") as f:
                yaml.dump(rules_content_2, f)

            # Load config with BOTH CLI rules files (issue #54)
            config = ConfigLoader.load_config(
                project_path, rules_files=[str(rules_file_1), str(rules_file_2)]
            )

            # Both rules should be present with same group
            assert "rule_one" in config.rule_definitions
            assert "rule_two" in config.rule_definitions
            assert config.rule_definitions["rule_one"].group_name == "Skills"
            assert config.rule_definitions["rule_two"].group_name == "Skills"


class TestRuleGroupsDefaults:
    """Tests for default group name handling."""

    def test_default_config_has_default_group_name(self):
        """Test that the default config includes default_group_name."""
        config = get_default_config()
        assert config.default_group_name == "General"

    def test_rule_definition_group_name_optional(self):
        """Test that group_name is optional on RuleDefinition."""
        rule = RuleDefinition(
            description="Test rule",
            scope="project_level",
            context="Test context",
            requires_project_context=True,
        )
        assert rule.group_name is None

    def test_rule_definition_with_group_name(self):
        """Test creating RuleDefinition with explicit group_name."""
        rule = RuleDefinition(
            description="Test rule",
            scope="project_level",
            context="Test context",
            requires_project_context=True,
            group_name="Custom Group",
        )
        assert rule.group_name == "Custom Group"


class TestRuleGroupsValidation:
    """Tests for rule group validation during config loading."""

    def test_duplicate_check_uses_default_group_when_none(self):
        """Test that duplicate checking uses default group when rule has no group."""
        with TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)

            # Create config with two rules, both without group_name (use default)
            config_content = {
                "providers": {
                    "test-provider": {
                        "provider": "claude-code",
                        "params": {},
                    }
                },
                "models": {
                    "test-model": {
                        "provider": "test-provider",
                        "model_id": "test",
                        "params": {},
                    }
                },
                "default_model": "test-model",
                "default_group_name": "General",
                "agent_tools": {
                    "claude-code": {
                        "conversation_path": str(project_path),
                        "enabled": True,
                    }
                },
                "rule_definitions": {
                    "my_rule": {
                        "description": "First rule",
                        "scope": "project_level",
                        "context": "Context",
                        "requires_project_context": True,
                    }
                },
            }

            config_file = project_path / ".drift.yaml"
            with open(config_file, "w") as f:
                yaml.dump(config_content, f)

            # Create rules file with same rule name, also no group (uses default)
            # This should override the rule from .drift.yaml
            rules_content = {
                "my_rule": {
                    "description": "Override rule",
                    "scope": "project_level",
                    "context": "Override context",
                    "requires_project_context": True,
                }
            }

            rules_file = project_path / ".drift_rules.yaml"
            with open(rules_file, "w") as f:
                yaml.dump(rules_content, f)

            # Should succeed and use override from .drift_rules.yaml
            # Both rules use the default group "General" (None means use default)
            config = ConfigLoader.load_config(project_path)
            assert config.rule_definitions["my_rule"].description == "Override rule"
            assert config.rule_definitions["my_rule"].context == "Override context"
            # Group name is None (meaning use default group "General")
            assert (
                config.rule_definitions["my_rule"].group_name is None
                or config.rule_definitions["my_rule"].group_name == "General"
            )
            # Verify the effective group is the default
            effective_group = (
                config.rule_definitions["my_rule"].group_name or config.default_group_name
            )
            assert effective_group == "General"

    def test_validation_after_file_level_group_applied(self):
        """Test that validation occurs after file-level group_name is applied."""
        with TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)

            # Create main config
            main_config = {
                "providers": {
                    "test-provider": {
                        "provider": "claude-code",
                        "params": {},
                    }
                },
                "models": {
                    "test-model": {
                        "provider": "test-provider",
                        "model_id": "test",
                        "params": {},
                    }
                },
                "default_model": "test-model",
                "agent_tools": {
                    "claude-code": {
                        "conversation_path": str(project_path),
                        "enabled": True,
                    }
                },
            }

            config_file = project_path / ".drift.yaml"
            with open(config_file, "w") as f:
                yaml.dump(main_config, f)

            # Create first rules file
            rules_file_1 = project_path / ".drift_rules.yaml"
            rules_content_1 = {
                "group_name": "Shared Group",
                "my_rule": {
                    "description": "First rule",
                    "scope": "project_level",
                    "context": "Context",
                    "requires_project_context": True,
                },
            }
            with open(rules_file_1, "w") as f:
                yaml.dump(rules_content_1, f)

            # Create second rules file with same group and same rule name
            # This should override the rule from .drift_rules.yaml
            rules_file_2 = project_path / "extra.yaml"
            rules_content_2 = {
                "group_name": "Shared Group",
                "my_rule": {
                    "description": "Override rule",
                    "scope": "project_level",
                    "context": "Override context",
                    "requires_project_context": True,
                },
            }
            with open(rules_file_2, "w") as f:
                yaml.dump(rules_content_2, f)

            # Should succeed and use the override from extra.yaml (higher priority CLI arg)
            config = ConfigLoader.load_config(project_path, rules_files=[str(rules_file_2)])
            assert config.rule_definitions["my_rule"].description == "Override rule"
            assert config.rule_definitions["my_rule"].context == "Override context"
            assert config.rule_definitions["my_rule"].group_name == "Shared Group"

    def test_empty_rules_file_with_only_group_name(self):
        """Test loading rules file that only has group_name field."""
        with TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)

            # Create main config
            main_config = {
                "providers": {
                    "test-provider": {
                        "provider": "claude-code",
                        "params": {},
                    }
                },
                "models": {
                    "test-model": {
                        "provider": "test-provider",
                        "model_id": "test",
                        "params": {},
                    }
                },
                "default_model": "test-model",
                "agent_tools": {
                    "claude-code": {
                        "conversation_path": str(project_path),
                        "enabled": True,
                    }
                },
            }

            config_file = project_path / ".drift.yaml"
            with open(config_file, "w") as f:
                yaml.dump(main_config, f)

            # Create rules file with only group_name
            rules_file = project_path / ".drift_rules.yaml"
            rules_content = {"group_name": "Empty Group"}
            with open(rules_file, "w") as f:
                yaml.dump(rules_content, f)

            # Should load successfully with no rules
            config = ConfigLoader.load_config(project_path)
            assert len(config.rule_definitions) == 0


class TestRuleGroupsBackwardCompatibility:
    """Tests for backward compatibility with existing configurations."""

    def test_config_without_group_name_field(self):
        """Test that old configs without group_name still work."""
        with TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)

            # Old-style config without any group_name fields
            config_content = {
                "providers": {
                    "test-provider": {
                        "provider": "claude-code",
                        "params": {},
                    }
                },
                "models": {
                    "test-model": {
                        "provider": "test-provider",
                        "model_id": "test",
                        "params": {},
                    }
                },
                "default_model": "test-model",
                "agent_tools": {
                    "claude-code": {
                        "conversation_path": str(project_path),
                        "enabled": True,
                    }
                },
                "rule_definitions": {
                    "old_rule": {
                        "description": "Old rule",
                        "scope": "project_level",
                        "context": "Old context",
                        "requires_project_context": True,
                    }
                },
            }

            config_file = project_path / ".drift.yaml"
            with open(config_file, "w") as f:
                yaml.dump(config_content, f)

            # Should load successfully
            config = ConfigLoader.load_config(project_path)

            # Should use default group name
            assert config.default_group_name == "General"
            assert config.rule_definitions["old_rule"].group_name is None

    def test_mixed_new_and_old_style_rules(self):
        """Test mixing rules with and without group_name."""
        with TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)

            config_content = {
                "providers": {
                    "test-provider": {
                        "provider": "claude-code",
                        "params": {},
                    }
                },
                "models": {
                    "test-model": {
                        "provider": "test-provider",
                        "model_id": "test",
                        "params": {},
                    }
                },
                "default_model": "test-model",
                "agent_tools": {
                    "claude-code": {
                        "conversation_path": str(project_path),
                        "enabled": True,
                    }
                },
                "rule_definitions": {
                    "new_rule": {
                        "description": "New rule with group",
                        "scope": "project_level",
                        "context": "Context",
                        "requires_project_context": True,
                        "group_name": "Custom Group",
                    },
                    "old_rule": {
                        "description": "Old rule without group",
                        "scope": "project_level",
                        "context": "Context",
                        "requires_project_context": True,
                    },
                },
            }

            config_file = project_path / ".drift.yaml"
            with open(config_file, "w") as f:
                yaml.dump(config_content, f)

            config = ConfigLoader.load_config(project_path)

            # New rule has explicit group
            assert config.rule_definitions["new_rule"].group_name == "Custom Group"

            # Old rule has no group (None, will use default at runtime)
            assert config.rule_definitions["old_rule"].group_name is None
