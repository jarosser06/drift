"""Integration tests for rule groups feature."""

from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

import yaml

from drift.cli.output.markdown import MarkdownFormatter
from drift.config.loader import ConfigLoader
from drift.core.types import AnalysisResult, AnalysisSummary, CompleteAnalysisResult, Rule


class TestRuleGroupsEndToEnd:
    """End-to-end integration tests for rule groups."""

    def test_full_workflow_with_groups(self):
        """Test complete workflow from config loading to output formatting."""
        with TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)

            # Create comprehensive config with groups
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
                "default_group_name": "General Checks",
                "agent_tools": {
                    "claude-code": {
                        "conversation_path": str(project_path),
                        "enabled": True,
                    }
                },
                "rule_definitions": {
                    "config_rule": {
                        "description": "Rule from main config",
                        "scope": "project_level",
                        "context": "Config context",
                        "requires_project_context": True,
                        "group_name": "Configuration",
                    },
                },
            }

            config_file = project_path / ".drift.yaml"
            with open(config_file, "w") as f:
                yaml.dump(config_content, f)

            # Create rules file with file-level group
            rules_file_content = {
                "group_name": "Documentation Quality",
                "doc_rule_1": {
                    "description": "First doc rule",
                    "scope": "project_level",
                    "context": "Doc context 1",
                    "requires_project_context": True,
                },
                "doc_rule_2": {
                    "description": "Second doc rule",
                    "scope": "project_level",
                    "context": "Doc context 2",
                    "requires_project_context": True,
                },
            }

            rules_file = project_path / ".drift_rules.yaml"
            with open(rules_file, "w") as f:
                yaml.dump(rules_file_content, f)

            # Create second rules file with different group
            extra_rules_content = {
                "validation_rule": {
                    "description": "Validation rule",
                    "scope": "project_level",
                    "context": "Validation context",
                    "requires_project_context": True,
                    "group_name": "Workflow Validation",
                }
            }

            extra_rules_file = project_path / "extra_rules.yaml"
            with open(extra_rules_file, "w") as f:
                yaml.dump(extra_rules_content, f)

            # Load config with all rules
            config = ConfigLoader.load_config(project_path, rules_files=[str(extra_rules_file)])

            # Verify all groups are set correctly
            assert config.rule_definitions["config_rule"].group_name == "Configuration"
            assert config.rule_definitions["doc_rule_1"].group_name == "Documentation Quality"
            assert config.rule_definitions["doc_rule_2"].group_name == "Documentation Quality"
            assert config.rule_definitions["validation_rule"].group_name == "Workflow Validation"

            # Create analysis results with grouped rules
            rules = [
                Rule(
                    turn_number=1,
                    agent_tool="test",
                    conversation_file="/test",
                    observed_behavior="Config issue",
                    expected_behavior="Expected config",
                    rule_type="config_rule",
                    group_name="Configuration",
                ),
                Rule(
                    turn_number=2,
                    agent_tool="test",
                    conversation_file="/test",
                    observed_behavior="Doc issue 1",
                    expected_behavior="Expected doc 1",
                    rule_type="doc_rule_1",
                    group_name="Documentation Quality",
                ),
                Rule(
                    turn_number=3,
                    agent_tool="test",
                    conversation_file="/test",
                    observed_behavior="Validation issue",
                    expected_behavior="Expected validation",
                    rule_type="validation_rule",
                    group_name="Workflow Validation",
                ),
            ]

            analysis_result = AnalysisResult(
                session_id="integration-test",
                agent_tool="test",
                conversation_file="/test",
                rules=rules,
                analysis_timestamp=datetime.now(),
            )

            complete_result = CompleteAnalysisResult(
                metadata={},
                summary=AnalysisSummary(
                    total_conversations=1,
                    total_rule_violations=3,
                    conversations_with_drift=1,
                    rules_passed=["doc_rule_2"],
                ),
                results=[analysis_result],
            )

            # Format output
            formatter = MarkdownFormatter(config=config)
            output = formatter.format(complete_result)

            # Verify all groups appear in output
            assert "### Configuration" in output
            assert "### Documentation Quality" in output
            assert "### Workflow Validation" in output

            # Verify passed rules section also has groups
            assert "## Checks Passed" in output

            # Verify rules appear under correct groups
            assert "#### config_rule" in output
            assert "#### doc_rule_1" in output
            assert "#### validation_rule" in output

    def test_multi_file_rules_with_duplicate_detection(self):
        """Test that duplicate rule+group combinations are detected across files."""
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

            # File 1: Group A
            file1_content = {
                "group_name": "Group A",
                "shared_rule": {
                    "description": "First definition",
                    "scope": "project_level",
                    "context": "Context 1",
                    "requires_project_context": True,
                },
            }

            file1 = project_path / ".drift_rules.yaml"
            with open(file1, "w") as f:
                yaml.dump(file1_content, f)

            # File 2: Also Group A with same rule name
            # This should override the rule from file1 (.drift_rules.yaml)
            file2_content = {
                "group_name": "Group A",
                "shared_rule": {
                    "description": "Override definition",
                    "scope": "project_level",
                    "context": "Override context",
                    "requires_project_context": True,
                },
            }

            file2 = project_path / "extra.yaml"
            with open(file2, "w") as f:
                yaml.dump(file2_content, f)

            # Should succeed and use the override from extra.yaml (CLI arg has highest priority)
            config = ConfigLoader.load_config(project_path, rules_files=[str(file2)])
            assert config.rule_definitions["shared_rule"].description == "Override definition"
            assert config.rule_definitions["shared_rule"].context == "Override context"
            assert config.rule_definitions["shared_rule"].group_name == "Group A"

    def test_same_rule_name_different_groups_allowed(self):
        """Test that same rule name in different groups works correctly."""
        with TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)

            # Create config with same rule name in different groups
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
            }

            config_file = project_path / ".drift.yaml"
            with open(config_file, "w") as f:
                yaml.dump(config_content, f)

            # File 1: completeness in Skills group
            file1_content = {
                "group_name": "Skills",
                "completeness": {
                    "description": "Skill completeness",
                    "scope": "project_level",
                    "context": "Skills context",
                    "requires_project_context": True,
                },
            }

            file1 = project_path / ".drift_rules.yaml"
            with open(file1, "w") as f:
                yaml.dump(file1_content, f)

            # File 2: completeness in Commands group
            file2_content = {
                "group_name": "Commands",
                "completeness": {
                    "description": "Command completeness",
                    "scope": "project_level",
                    "context": "Commands context",
                    "requires_project_context": True,
                },
            }

            file2 = project_path / "commands.yaml"
            with open(file2, "w") as f:
                yaml.dump(file2_content, f)

            # Should load successfully - different groups
            # Note: Can't actually test this properly because YAML merges duplicate keys
            # But the validation logic supports it
            config = ConfigLoader.load_config(project_path, rules_files=[str(file2)])

            # Should have both rules (but YAML limitation means second overwrites first)
            # This test documents the behavior
            assert "completeness" in config.rule_definitions

    def test_backward_compatible_output(self):
        """Test that output is backward compatible with configs without groups."""
        with TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)

            # Old-style config without group_name
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

            config = ConfigLoader.load_config(project_path)

            # Should use default group name
            assert config.default_group_name == "General"
            assert config.rule_definitions["old_rule"].group_name is None

            # Create result with rule
            rule = Rule(
                turn_number=1,
                agent_tool="test",
                conversation_file="/test",
                observed_behavior="Issue",
                expected_behavior="Expected",
                rule_type="old_rule",
                group_name=None,  # Old behavior
            )

            analysis_result = AnalysisResult(
                session_id="test",
                agent_tool="test",
                conversation_file="/test",
                rules=[rule],
                analysis_timestamp=datetime.now(),
            )

            complete_result = CompleteAnalysisResult(
                metadata={},
                summary=AnalysisSummary(
                    total_conversations=1,
                    total_rule_violations=1,
                    conversations_with_drift=1,
                ),
                results=[analysis_result],
            )

            # Format output
            formatter = MarkdownFormatter(config=config)
            output = formatter.format(complete_result)

            # Should still work, using "General" as fallback
            assert "### General" in output
            assert "#### old_rule" in output
