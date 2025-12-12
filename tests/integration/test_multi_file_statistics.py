"""Integration tests for statistics aggregation across multiple rules files."""

import tempfile
from pathlib import Path

import pytest

from drift.config.loader import ConfigLoader
from drift.core.analyzer import DriftAnalyzer


class TestMultiFileStatistics:
    """Test that statistics are correctly aggregated when using multiple rules files."""

    @pytest.fixture
    def temp_project(self):
        """Create a temporary project directory with test files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)

            # Create test files for validation
            (project_path / "README.md").write_text("# Test Project\n")
            (project_path / "CHANGELOG.md").write_text("# Changelog\n")
            (project_path / "LICENSE").write_text("MIT License\n")
            (project_path / "CONTRIBUTING.md").write_text("# Contributing\n")

            yield project_path

    def test_total_checks_with_two_files_same_group(self, temp_project, monkeypatch):
        """Test total_checks when two default rules files contribute to the SAME group.

        Scenario: .drift.yaml has 1 rule in "Documentation" group
                  .drift_rules.yaml has 1 more rule in "Documentation" group
        Expected: total_checks = 2 (both rules counted)
        """
        monkeypatch.setattr(
            ConfigLoader,
            "GLOBAL_CONFIG_PATHS",
            [temp_project / "nonexistent.yaml"],
        )

        # Base config - just write YAML directly
        drift_yaml_content = """
rule_definitions:
  check_readme:
    description: "README must exist"
    scope: project_level
    context: "Test"
    group_name: "Documentation"
    requires_project_context: false
    validation_rules:
      document_bundle:
        bundle_type: mixed
        file_patterns:
          - README.md
        bundle_strategy: individual
      rules:
        - rule_type: "core:file_exists"
          description: "README must exist"
          file_path: "README.md"
"""
        drift_yaml = temp_project / ".drift.yaml"
        drift_yaml.write_text(drift_yaml_content)

        # Additional rules file - using .drift_rules.yaml (default location)
        extra_rules_content = """
check_changelog:
  description: "CHANGELOG must exist"
  scope: project_level
  context: "Test"
  group_name: "Documentation"
  requires_project_context: false
  validation_rules:
    document_bundle:
      bundle_type: mixed
      file_patterns:
        - CHANGELOG.md
      bundle_strategy: individual
    rules:
      - rule_type: "core:file_exists"
        description: "CHANGELOG must exist"
        file_path: "CHANGELOG.md"
"""
        rules_file = temp_project / ".drift_rules.yaml"
        rules_file.write_text(extra_rules_content)

        # Load without CLI rules_files (uses defaults)
        loaded_config = ConfigLoader.load_config(temp_project)

        # Run analysis
        analyzer = DriftAnalyzer(loaded_config, temp_project)
        result = analyzer.analyze_documents()

        # Assert counts
        assert result.summary.total_checks == 2, (
            f"total_checks is {result.summary.total_checks}, expected 2 "
            f"(1 from .drift.yaml + 1 from .drift_rules.yaml)"
        )
        assert result.summary.checks_passed == 2
        assert result.summary.by_group.get("Documentation", 0) == 2

    def test_total_checks_with_two_files_different_groups(self, temp_project, monkeypatch):
        """Test total_checks when two default rules files contribute to DIFFERENT groups.

        Scenario: .drift.yaml has 1 rule in "Documentation" group
                  .drift_rules.yaml has 1 rule in "Legal" group
        Expected: total_checks = 2, by_group has both Documentation and Legal
        """
        monkeypatch.setattr(
            ConfigLoader,
            "GLOBAL_CONFIG_PATHS",
            [temp_project / "nonexistent.yaml"],
        )

        # Base config - simple YAML
        drift_yaml_content = """
rule_definitions:
  check_readme:
    description: "README must exist"
    scope: project_level
    context: "Test"
    group_name: "Documentation"
    requires_project_context: false
    validation_rules:
      document_bundle:
        bundle_type: mixed
        file_patterns:
          - README.md
        bundle_strategy: individual
      rules:
        - rule_type: "core:file_exists"
          description: "README must exist"
          file_path: "README.md"
"""
        drift_yaml = temp_project / ".drift.yaml"
        drift_yaml.write_text(drift_yaml_content)

        # Extra rules - DIFFERENT group, using .drift_rules.yaml (default location)
        extra_rules_content = """
check_license:
  description: "LICENSE must exist"
  scope: project_level
  context: "Test"
  group_name: "Legal"
  requires_project_context: false
  validation_rules:
    document_bundle:
      bundle_type: mixed
      file_patterns:
        - LICENSE
      bundle_strategy: individual
    rules:
      - rule_type: "core:file_exists"
        description: "LICENSE must exist"
        file_path: "LICENSE"
"""
        rules_file = temp_project / ".drift_rules.yaml"
        rules_file.write_text(extra_rules_content)

        # Load without CLI rules_files (uses defaults)
        loaded_config = ConfigLoader.load_config(temp_project)
        analyzer = DriftAnalyzer(loaded_config, temp_project)
        result = analyzer.analyze_documents()

        # Assert counts
        assert result.summary.total_checks == 2
        assert result.summary.checks_passed == 2
        assert result.summary.by_group.get("Documentation", 0) == 1
        assert result.summary.by_group.get("Legal", 0) == 1

    def test_total_checks_with_single_file_multiple_groups(self, temp_project, monkeypatch):
        """Test total_checks when ONE default file has rules in DIFFERENT groups.

        Scenario: .drift_rules.yaml has 2 rules, each in a different group
        Expected: total_checks = 3 (1 from .drift.yaml + 2 from .drift_rules.yaml), 3 groups total
        """
        monkeypatch.setattr(
            ConfigLoader,
            "GLOBAL_CONFIG_PATHS",
            [temp_project / "nonexistent.yaml"],
        )

        # Base config - simple YAML
        drift_yaml_content = """
rule_definitions:
  check_readme:
    description: "README must exist"
    scope: project_level
    context: "Test"
    group_name: "Documentation"
    requires_project_context: false
    validation_rules:
      document_bundle:
        bundle_type: mixed
        file_patterns:
          - README.md
        bundle_strategy: individual
      rules:
        - rule_type: "core:file_exists"
          description: "README must exist"
          file_path: "README.md"
"""
        drift_yaml = temp_project / ".drift.yaml"
        drift_yaml.write_text(drift_yaml_content)

        # Extra rules with 2 rules in DIFFERENT groups, using .drift_rules.yaml (default location)
        extra_rules_content = """
check_changelog:
  description: "CHANGELOG must exist"
  scope: project_level
  context: "Test"
  group_name: "Quality"
  requires_project_context: false
  validation_rules:
    document_bundle:
      bundle_type: mixed
      file_patterns:
        - CHANGELOG.md
      bundle_strategy: individual
    rules:
      - rule_type: "core:file_exists"
        description: "CHANGELOG must exist"
        file_path: "CHANGELOG.md"

check_contributing:
  description: "CONTRIBUTING must exist"
  scope: project_level
  context: "Test"
  group_name: "Community"
  requires_project_context: false
  validation_rules:
    document_bundle:
      bundle_type: mixed
      file_patterns:
        - CONTRIBUTING.md
      bundle_strategy: individual
    rules:
      - rule_type: "core:file_exists"
        description: "CONTRIBUTING must exist"
        file_path: "CONTRIBUTING.md"
"""
        rules_file = temp_project / ".drift_rules.yaml"
        rules_file.write_text(extra_rules_content)

        # Load without CLI rules_files (uses defaults)
        loaded_config = ConfigLoader.load_config(temp_project)
        analyzer = DriftAnalyzer(loaded_config, temp_project)
        result = analyzer.analyze_documents()

        # Assert counts
        assert result.summary.total_checks == 3, (
            f"total_checks is {result.summary.total_checks}, expected 3. "
            f"by_group: {result.summary.by_group}"
        )
        assert result.summary.checks_passed == 3
        # Verify all 3 groups are present
        assert len(result.summary.by_group) == 3
        assert result.summary.by_group.get("Documentation", 0) == 1
        assert result.summary.by_group.get("Quality", 0) == 1
        assert result.summary.by_group.get("Community", 0) == 1
