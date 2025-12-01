"""Integration tests for new validators with real Claude Code examples."""

import pytest

from drift.config.models import (
    BundleStrategy,
    DocumentBundleConfig,
    ValidationRule,
    ValidationRulesConfig,
    ValidationType,
)
from drift.documents.loader import DocumentLoader
from drift.validation.validators import DependencyDuplicateValidator, MarkdownLinkValidator


class TestDependencyDuplicateValidatorIntegration:
    """Integration tests for DependencyDuplicateValidator."""

    @pytest.fixture
    def temp_claude_project(self, tmp_path):
        """Create a temporary Claude Code project structure."""
        # Create .claude directory structure
        commands_dir = tmp_path / ".claude" / "commands"
        commands_dir.mkdir(parents=True)

        skills_dir = tmp_path / ".claude" / "skills"
        (skills_dir / "code-review").mkdir(parents=True)
        (skills_dir / "testing").mkdir(parents=True)
        (skills_dir / "linting").mkdir(parents=True)

        agents_dir = tmp_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True)

        # Create command with duplicate dependency
        # full-check depends on [code-review, testing, linting]
        # code-review depends on [linting]
        # So linting is redundant in full-check
        (commands_dir / "full-check.md").write_text(
            """---
description: Run comprehensive code quality checks
skills:
  - code-review
  - testing
  - linting
---
# Full Check Command

Run all quality checks on the codebase.
"""
        )

        # Create skills
        (skills_dir / "code-review" / "SKILL.md").write_text(
            """---
name: code-review
description: Review code for quality and best practices
skills:
  - linting
---
# Code Review Skill

Expert in conducting thorough code reviews.
"""
        )

        (skills_dir / "testing" / "SKILL.md").write_text(
            """---
name: testing
description: Write and run tests
---
# Testing Skill

Expert in writing comprehensive test suites.
"""
        )

        (skills_dir / "linting" / "SKILL.md").write_text(
            """---
name: linting
description: Check code style and formatting
---
# Linting Skill

Expert in code style and formatting standards.
"""
        )

        return tmp_path

    def test_detects_duplicate_dependencies(self, temp_claude_project):
        """Test that duplicate dependencies are detected in real project structure."""
        # Create validation config
        validation_config = ValidationRulesConfig(
            scope="project_level",
            document_bundle=DocumentBundleConfig(
                bundle_type="mixed",
                file_patterns=["**/*.md"],
                bundle_strategy=BundleStrategy.INDIVIDUAL,
            ),
            rules=[
                ValidationRule(
                    rule_type=ValidationType.DEPENDENCY_DUPLICATE,
                    description="Check for duplicate skill dependencies",
                    failure_message="Found redundant skill dependencies",
                    expected_behavior=(
                        "Skills should not be declared if already transitively included"
                    ),
                    params={
                        "resource_dirs": [".claude/commands", ".claude/skills", ".claude/agents"]
                    },
                )
            ],
        )

        # Load documents
        loader = DocumentLoader(temp_claude_project)
        bundles = loader.load_bundles(validation_config.document_bundle)

        # Run validation
        validator = DependencyDuplicateValidator(loader)

        results = []
        for bundle in bundles:
            for rule in validation_config.rules:
                result = validator.validate(rule, bundle, bundles)
                if result:
                    results.append(result)

        # Should detect that linting is redundant in full-check.md
        assert len(results) > 0
        assert any("linting" in r.observed_issue for r in results)
        assert any("redundant" in r.observed_issue.lower() for r in results)


class TestMarkdownLinkValidatorIntegration:
    """Integration tests for MarkdownLinkValidator."""

    @pytest.fixture
    def temp_docs_project(self, tmp_path):
        """Create a temporary project with documentation."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        # Create valid documentation
        (docs_dir / "guide.md").write_text(
            """# User Guide

See the [API Reference](docs/api.md) for details.
"""
        )

        (docs_dir / "api.md").write_text(
            """# API Reference

Complete API documentation.
"""
        )

        # Create documentation with broken links
        (docs_dir / "broken.md").write_text(
            """# Broken Links

This links to a [missing file](docs/missing.md).

Also see [nonexistent](docs/does-not-exist.md).
"""
        )

        return tmp_path

    def test_detects_broken_local_links(self, temp_docs_project):
        """Test that broken local links are detected."""
        validation_config = ValidationRulesConfig(
            scope="project_level",
            document_bundle=DocumentBundleConfig(
                bundle_type="mixed",
                file_patterns=["docs/**/*.md"],
                bundle_strategy=BundleStrategy.INDIVIDUAL,
            ),
            rules=[
                ValidationRule(
                    rule_type=ValidationType.MARKDOWN_LINK,
                    description="Check for broken links in documentation",
                    failure_message="Found broken links",
                    expected_behavior="All links should point to existing files",
                    params={
                        "check_local_files": True,
                        "check_external_urls": False,
                    },
                )
            ],
        )

        # Load documents
        loader = DocumentLoader(temp_docs_project)
        bundles = loader.load_bundles(validation_config.document_bundle)

        # Run validation
        validator = MarkdownLinkValidator(loader)

        results = []
        for bundle in bundles:
            for rule in validation_config.rules:
                result = validator.validate(rule, bundle, bundles)
                if result:
                    results.append(result)

        # Should detect broken links in broken.md
        assert len(results) > 0
        broken_result = [r for r in results if "broken.md" in str(r.file_paths)]
        assert len(broken_result) > 0
        assert "docs/missing.md" in broken_result[0].observed_issue
        assert "docs/does-not-exist.md" in broken_result[0].observed_issue

    def test_validates_correct_links_pass(self, temp_docs_project):
        """Test that correct links pass validation."""
        validation_config = ValidationRulesConfig(
            scope="project_level",
            document_bundle=DocumentBundleConfig(
                bundle_type="mixed",
                file_patterns=["docs/guide.md"],  # Only check the valid file
                bundle_strategy=BundleStrategy.INDIVIDUAL,
            ),
            rules=[
                ValidationRule(
                    rule_type=ValidationType.MARKDOWN_LINK,
                    description="Check for broken links",
                    failure_message="Found broken links",
                    expected_behavior="All links should be valid",
                    params={
                        "check_local_files": True,
                        "check_external_urls": False,
                    },
                )
            ],
        )

        # Load documents
        loader = DocumentLoader(temp_docs_project)
        bundles = loader.load_bundles(validation_config.document_bundle)

        # Run validation
        validator = MarkdownLinkValidator(loader)

        results = []
        for bundle in bundles:
            for rule in validation_config.rules:
                result = validator.validate(rule, bundle, bundles)
                if result:
                    results.append(result)

        # Should have no violations for guide.md (api.md exists)
        assert len(results) == 0

    def test_validates_with_relative_and_project_root_fallback(self, tmp_path):
        """Test that validator checks both file-relative and project-root paths."""
        # Create project structure with:
        # - A file at project root (test.sh)
        # - A resources directory relative to a skill
        # - Mixed references that should be found via fallback

        # Create project root file
        (tmp_path / "test.sh").write_text("#!/bin/bash\necho test")

        # Create skill with local resources directory
        skill_dir = tmp_path / ".claude" / "skills" / "testing"
        skill_dir.mkdir(parents=True)

        resources_dir = skill_dir / "resources"
        resources_dir.mkdir()
        (resources_dir / "mocking-aws.md").write_text("# Mocking AWS")

        # Create skill file that references:
        # 1. Local resource (should be found relative to skill directory)
        # 2. Project root file (should be found via fallback to project root)
        # 3. Non-existent file (should be reported as broken)
        (skill_dir / "SKILL.md").write_text(
            """# Testing Skill

See [Mocking Guide](resources/mocking-aws.md) for AWS mocking.

Run [test script](test.sh) from project root.

Missing [nonexistent file](does-not-exist.md).
"""
        )

        validation_config = ValidationRulesConfig(
            scope="project_level",
            document_bundle=DocumentBundleConfig(
                bundle_type="skill",
                file_patterns=[".claude/skills/*/SKILL.md"],
                bundle_strategy=BundleStrategy.INDIVIDUAL,
            ),
            rules=[
                ValidationRule(
                    rule_type=ValidationType.MARKDOWN_LINK,
                    description="Check for broken links",
                    failure_message="Found broken links",
                    expected_behavior="All links should be valid",
                    params={
                        "check_local_files": True,
                        "check_external_urls": False,
                    },
                )
            ],
        )

        # Load documents
        loader = DocumentLoader(tmp_path)
        bundles = loader.load_bundles(validation_config.document_bundle)

        # Run validation
        validator = MarkdownLinkValidator(loader)

        results = []
        for bundle in bundles:
            for rule in validation_config.rules:
                result = validator.validate(rule, bundle, bundles)
                if result:
                    results.append(result)

        # Should only have one violation for the nonexistent file
        assert len(results) == 1
        assert "does-not-exist.md" in results[0].observed_issue

        # Should NOT report mocking-aws.md (found relative to file)
        assert "mocking-aws.md" not in results[0].observed_issue

        # Should NOT report test.sh (found relative to project root)
        assert "test.sh" not in results[0].observed_issue


class TestEndToEndValidation:
    """End-to-end integration tests."""

    @pytest.fixture
    def complete_project(self, tmp_path):
        """Create a complete project with various issues."""
        # Create Claude Code structure
        claude_dir = tmp_path / ".claude"
        (claude_dir / "commands").mkdir(parents=True)
        (claude_dir / "skills" / "skill-a").mkdir(parents=True)
        (claude_dir / "skills" / "skill-b").mkdir(parents=True)

        # Command with duplicate dependency
        (claude_dir / "commands" / "test.md").write_text(
            """---
skills:
  - skill-a
  - skill-b
---
See [documentation](../../docs/readme.md) for details.
"""
        )

        # Skills
        (claude_dir / "skills" / "skill-a" / "SKILL.md").write_text(
            """---
name: skill-a
skills:
  - skill-b
---
Skill A depends on [Skill B](../skill-b/SKILL.md).
"""
        )

        (claude_dir / "skills" / "skill-b" / "SKILL.md").write_text(
            """---
name: skill-b
---
Base skill.
"""
        )

        # Create docs with broken link
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "readme.md").write_text(
            """# README

Check the [missing guide](guide.md).
"""
        )

        return tmp_path

    def test_multiple_validators_detect_issues(self, complete_project):
        """Test that multiple validators can run and detect different issues."""
        validation_config = ValidationRulesConfig(
            scope="project_level",
            document_bundle=DocumentBundleConfig(
                bundle_type="mixed",
                file_patterns=["**/*.md"],
                bundle_strategy=BundleStrategy.INDIVIDUAL,
            ),
            rules=[
                ValidationRule(
                    rule_type=ValidationType.DEPENDENCY_DUPLICATE,
                    description="Check for duplicate dependencies",
                    failure_message="Found redundant dependencies",
                    expected_behavior="No transitive duplicates",
                    params={"resource_dirs": [".claude/commands", ".claude/skills"]},
                ),
                ValidationRule(
                    rule_type=ValidationType.MARKDOWN_LINK,
                    description="Check for broken links",
                    failure_message="Found broken links",
                    expected_behavior="All links should be valid",
                    params={
                        "check_local_files": True,
                        "check_external_urls": False,
                    },
                ),
            ],
        )

        # Load documents
        loader = DocumentLoader(complete_project)
        bundles = loader.load_bundles(validation_config.document_bundle)

        # Run validation with both validators
        dep_validator = DependencyDuplicateValidator(loader)
        link_validator = MarkdownLinkValidator(loader)

        all_results = []
        for bundle in bundles:
            for rule in validation_config.rules:
                if rule.rule_type == ValidationType.DEPENDENCY_DUPLICATE:
                    result = dep_validator.validate(rule, bundle, bundles)
                elif rule.rule_type == ValidationType.MARKDOWN_LINK:
                    result = link_validator.validate(rule, bundle, bundles)
                else:
                    result = None
                if result:
                    all_results.append(result)

        # Should have both types of violations
        assert len(all_results) >= 2

        # Check for dependency duplicate violation
        dep_violations = [r for r in all_results if "redundant" in r.observed_issue.lower()]
        assert len(dep_violations) > 0
        assert any("skill-b" in v.observed_issue for v in dep_violations)

        # Check for broken link violation
        link_violations = [r for r in all_results if "broken links" in r.observed_issue.lower()]
        assert len(link_violations) > 0
        assert any("guide.md" in v.observed_issue for v in link_violations)
