"""Integration tests for failure_details feature across validation framework."""

import json

import pytest

from drift.config.models import ValidationRule, ValidationType
from drift.core.types import DocumentBundle, DocumentFile
from drift.validation.validators import (
    ClaudeCircularDependenciesValidator,
    ClaudeDependencyDuplicateValidator,
    ClaudeMaxDependencyDepthValidator,
)


class TestFailureDetailsIntegration:
    """Integration tests for failure_details propagation through validation engine."""

    @pytest.fixture
    def complex_project(self, tmp_path):
        """Create complex project with multiple validation issues."""
        # Create circular dependency: skill-a ↔ skill-b
        skill_a_dir = tmp_path / ".claude" / "skills" / "skill-a"
        skill_a_dir.mkdir(parents=True)
        (skill_a_dir / "SKILL.md").write_text("---\nname: skill-a\nskills:\n  - skill-b\n---\n")

        skill_b_dir = tmp_path / ".claude" / "skills" / "skill-b"
        skill_b_dir.mkdir(parents=True)
        (skill_b_dir / "SKILL.md").write_text("---\nname: skill-b\nskills:\n  - skill-a\n---\n")

        # Create deep chain: skill-x → skill-y → skill-z → skill-w (depth 3)
        for skill_name, deps in [
            ("skill-x", ["skill-y"]),
            ("skill-y", ["skill-z"]),
            ("skill-z", ["skill-w"]),
            ("skill-w", []),
        ]:
            skill_dir = tmp_path / ".claude" / "skills" / skill_name
            skill_dir.mkdir(parents=True)
            if deps:
                deps_yaml = "\n".join([f"  - {d}" for d in deps])
                content = f"---\nname: {skill_name}\nskills:\n{deps_yaml}\n---\n"
            else:
                content = f"---\nname: {skill_name}\n---\n"
            (skill_dir / "SKILL.md").write_text(content)

        # Create duplicate: skill-p → skill-q, skill-r (where skill-q → skill-r)
        skill_r_dir = tmp_path / ".claude" / "skills" / "skill-r"
        skill_r_dir.mkdir(parents=True)
        (skill_r_dir / "SKILL.md").write_text("---\nname: skill-r\n---\n")

        skill_q_dir = tmp_path / ".claude" / "skills" / "skill-q"
        skill_q_dir.mkdir(parents=True)
        (skill_q_dir / "SKILL.md").write_text("---\nname: skill-q\nskills:\n  - skill-r\n---\n")

        skill_p_dir = tmp_path / ".claude" / "skills" / "skill-p"
        skill_p_dir.mkdir(parents=True)
        (skill_p_dir / "SKILL.md").write_text(
            "---\nname: skill-p\nskills:\n  - skill-q\n  - skill-r\n---\n"
        )

        return tmp_path

    @pytest.fixture
    def all_bundles(self, complex_project):
        """Create all bundles for complex project."""
        bundles = []
        skill_names = [
            "skill-a",
            "skill-b",
            "skill-x",
            "skill-y",
            "skill-z",
            "skill-w",
            "skill-p",
            "skill-q",
            "skill-r",
        ]

        for skill_name in skill_names:
            skill_path = complex_project / ".claude" / "skills" / skill_name / "SKILL.md"
            bundles.append(
                DocumentBundle(
                    bundle_id=skill_name,
                    bundle_type="skill",
                    bundle_strategy="individual",
                    files=[
                        DocumentFile(
                            file_path=str(skill_path),
                            relative_path=f".claude/skills/{skill_name}/SKILL.md",
                            content=skill_path.read_text(),
                        )
                    ],
                    project_path=complex_project,
                )
            )

        return bundles

    def test_multiple_validators_with_failure_details(self, complex_project, all_bundles):
        """Test that multiple validators can produce failure_details simultaneously."""
        # Test circular dependency validator
        circular_validator = ClaudeCircularDependenciesValidator()
        circular_rule = ValidationRule(
            rule_type=ValidationType.CIRCULAR_DEPENDENCIES,
            description="Check circular dependencies",
            params={"resource_dirs": [".claude/skills"]},
            failure_message="Circular dependency detected",
            expected_behavior="No cycles",
        )

        circular_result = circular_validator.validate(circular_rule, all_bundles[0], all_bundles)

        # Test max depth validator
        depth_validator = ClaudeMaxDependencyDepthValidator()
        depth_rule = ValidationRule(
            rule_type=ValidationType.MAX_DEPENDENCY_DEPTH,
            description="Check depth",
            params={"resource_dirs": [".claude/skills"], "max_depth": 2},
            failure_message="Depth exceeded",
            expected_behavior="Max depth 2",
        )

        depth_result = depth_validator.validate(depth_rule, all_bundles[2], all_bundles)

        # Test duplicate validator
        duplicate_validator = ClaudeDependencyDuplicateValidator()
        duplicate_rule = ValidationRule(
            rule_type=ValidationType.DEPENDENCY_DUPLICATE,
            description="Check duplicates",
            params={"resource_dirs": [".claude/skills"]},
            failure_message="Duplicate detected",
            expected_behavior="No duplicates",
        )

        duplicate_result = duplicate_validator.validate(duplicate_rule, all_bundles[6], all_bundles)

        # All should have failure_details
        assert circular_result is not None
        assert circular_result.failure_details is not None
        assert "circular_path" in circular_result.failure_details

        assert depth_result is not None
        assert depth_result.failure_details is not None
        assert "actual_depth" in depth_result.failure_details

        assert duplicate_result is not None
        assert duplicate_result.failure_details is not None
        assert "duplicate_resource" in duplicate_result.failure_details

    def test_failure_details_different_structures(self, complex_project, all_bundles):
        """Test that different validators produce appropriately structured failure_details."""
        validators_and_rules = [
            (
                ClaudeCircularDependenciesValidator(),
                ValidationRule(
                    rule_type=ValidationType.CIRCULAR_DEPENDENCIES,
                    description="Check circular dependencies",
                    params={"resource_dirs": [".claude/skills"]},
                    failure_message="Circular dependency",
                    expected_behavior="No cycles",
                ),
                all_bundles[0],  # skill-a with circular dep
                ["circular_path", "cycle_count", "all_cycles"],
            ),
            (
                ClaudeMaxDependencyDepthValidator(),
                ValidationRule(
                    rule_type=ValidationType.MAX_DEPENDENCY_DEPTH,
                    description="Check depth",
                    params={"resource_dirs": [".claude/skills"], "max_depth": 2},
                    failure_message="Depth exceeded",
                    expected_behavior="Max depth 2",
                ),
                all_bundles[2],  # skill-x with depth 3
                ["actual_depth", "max_depth", "dependency_chain", "violation_count"],
            ),
            (
                ClaudeDependencyDuplicateValidator(),
                ValidationRule(
                    rule_type=ValidationType.DEPENDENCY_DUPLICATE,
                    description="Check duplicates",
                    params={"resource_dirs": [".claude/skills"]},
                    failure_message="Duplicate detected",
                    expected_behavior="No duplicates",
                ),
                all_bundles[6],  # skill-p with duplicate
                ["duplicate_resource", "declared_by", "duplicate_count"],
            ),
        ]

        for validator, rule, bundle, expected_keys in validators_and_rules:
            result = validator.validate(rule, bundle, all_bundles)
            assert result is not None
            assert result.failure_details is not None

            # Verify expected keys are present
            for key in expected_keys:
                assert (
                    key in result.failure_details
                ), f"Missing key {key} in {validator.__class__.__name__}"

    def test_failure_details_json_serialization(self, complex_project, all_bundles):
        """Test that all failure_details can be serialized to JSON."""
        validators = [
            (ClaudeCircularDependenciesValidator(), all_bundles[0]),
            (ClaudeMaxDependencyDepthValidator(), all_bundles[2]),
            (ClaudeDependencyDuplicateValidator(), all_bundles[6]),
        ]

        rules = [
            ValidationRule(
                rule_type=ValidationType.CIRCULAR_DEPENDENCIES,
                description="Check circular",
                params={"resource_dirs": [".claude/skills"]},
                failure_message="Circular",
                expected_behavior="No cycles",
            ),
            ValidationRule(
                rule_type=ValidationType.MAX_DEPENDENCY_DEPTH,
                description="Check depth",
                params={"resource_dirs": [".claude/skills"], "max_depth": 2},
                failure_message="Depth",
                expected_behavior="Max 2",
            ),
            ValidationRule(
                rule_type=ValidationType.DEPENDENCY_DUPLICATE,
                description="Check dup",
                params={"resource_dirs": [".claude/skills"]},
                failure_message="Dup",
                expected_behavior="No dup",
            ),
        ]

        for (validator, bundle), rule in zip(validators, rules):
            result = validator.validate(rule, bundle, all_bundles)
            if result:
                # Should serialize without error
                try:
                    json_str = json.dumps(result.failure_details)
                    # Should deserialize back
                    deserialized = json.loads(json_str)
                    assert isinstance(deserialized, dict)
                except (TypeError, ValueError) as e:
                    pytest.fail(
                        f"JSON serialization failed for {validator.__class__.__name__}: {e}"
                    )

    def test_backward_compatibility_validators_without_failure_details(
        self, complex_project, all_bundles
    ):
        """Test that validators not using failure_details still work."""
        # This tests backward compatibility - if a validator doesn't set failure_details,
        # the system should still work
        from drift.validation.validators.base import BaseValidator

        class LegacyValidator(BaseValidator):
            """Validator that doesn't use failure_details."""

            @property
            def computation_type(self):
                return "programmatic"

            def validate(self, rule, bundle, all_bundles=None):
                # Return violation without failure_details
                from drift.core.types import DocumentRule

                return DocumentRule(
                    bundle_id=bundle.bundle_id,
                    bundle_type=bundle.bundle_type,
                    file_paths=[],
                    observed_issue="Legacy issue",
                    expected_quality="Legacy expected",
                    rule_type="legacy",
                    context="Legacy context",
                    # No failure_details set
                )

        validator = LegacyValidator()
        rule = ValidationRule(
            rule_type=ValidationType.CIRCULAR_DEPENDENCIES,
            description="Test",
            params={},
            failure_message="Test",
            expected_behavior="Test",
        )

        result = validator.validate(rule, all_bundles[0], all_bundles)

        # Should work fine, failure_details should be None
        assert result is not None
        assert result.failure_details is None

    def test_failure_details_preserved_through_document_rule(self, complex_project, all_bundles):
        """Test that failure_details is preserved when creating DocumentRule."""
        validator = ClaudeCircularDependenciesValidator()
        rule = ValidationRule(
            rule_type=ValidationType.CIRCULAR_DEPENDENCIES,
            description="Check circular",
            params={"resource_dirs": [".claude/skills"]},
            failure_message="Circular dependency",
            expected_behavior="No cycles",
        )

        result = validator.validate(rule, all_bundles[0], all_bundles)

        # Verify failure_details is in the DocumentRule
        assert result is not None
        assert hasattr(result, "failure_details")
        assert result.failure_details is not None

        # Verify it can be accessed and used
        assert isinstance(result.failure_details, dict)
        assert len(result.failure_details) > 0

    def test_failure_details_used_in_message_formatting(self, complex_project, all_bundles):
        """Test that failure_details values appear in formatted messages."""
        # Circular dependencies
        circular_validator = ClaudeCircularDependenciesValidator()
        circular_rule = ValidationRule(
            rule_type=ValidationType.CIRCULAR_DEPENDENCIES,
            description="Check circular",
            params={"resource_dirs": [".claude/skills"]},
            failure_message="Found circular dependency",
            expected_behavior="No cycles",
        )

        circular_result = circular_validator.validate(circular_rule, all_bundles[0], all_bundles)

        # Circular path should be in the message
        if circular_result:
            circular_path = circular_result.failure_details["circular_path"]
            assert circular_path in circular_result.observed_issue

        # Max depth
        depth_validator = ClaudeMaxDependencyDepthValidator()
        depth_rule = ValidationRule(
            rule_type=ValidationType.MAX_DEPENDENCY_DEPTH,
            description="Check depth",
            params={"resource_dirs": [".claude/skills"], "max_depth": 2},
            failure_message="Depth exceeded",
            expected_behavior="Max 2",
        )

        depth_result = depth_validator.validate(depth_rule, all_bundles[2], all_bundles)

        # Depth values should be in message
        if depth_result:
            assert str(depth_result.failure_details["actual_depth"]) in depth_result.observed_issue
            assert str(depth_result.failure_details["max_depth"]) in depth_result.observed_issue

    def test_empty_failure_details_handled_gracefully(self, tmp_path):
        """Test that empty or minimal failure_details don't break validation."""
        from drift.validation.validators.base import BaseValidator

        class MinimalValidator(BaseValidator):
            """Validator with minimal failure_details."""

            @property
            def computation_type(self):
                return "programmatic"

            def validate(self, rule, bundle, all_bundles=None):
                from drift.core.types import DocumentRule

                return DocumentRule(
                    bundle_id=bundle.bundle_id,
                    bundle_type=bundle.bundle_type,
                    file_paths=[],
                    observed_issue=self._format_message(rule.failure_message, {}),
                    expected_quality=rule.expected_behavior,
                    rule_type="minimal",
                    context="Test",
                    failure_details={},  # Empty dict
                )

        skill_dir = tmp_path / ".claude" / "skills" / "test"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("---\nname: test\n---\n")

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="skill",
            bundle_strategy="individual",
            files=[
                DocumentFile(
                    file_path=str(skill_dir / "SKILL.md"),
                    relative_path=".claude/skills/test/SKILL.md",
                    content="---\nname: test\n---\n",
                )
            ],
            project_path=tmp_path,
        )

        validator = MinimalValidator()
        rule = ValidationRule(
            rule_type=ValidationType.CIRCULAR_DEPENDENCIES,
            description="Test",
            params={},
            failure_message="Test message",
            expected_behavior="Test",
        )

        result = validator.validate(rule, bundle)

        # Should work fine with empty failure_details
        assert result is not None
        assert result.failure_details == {}

    def test_format_message_integration_with_validators(self, complex_project, all_bundles):
        """Test that _format_message is properly integrated in validators."""
        # Test that placeholders in failure_message get replaced
        validator = ClaudeMaxDependencyDepthValidator()
        rule = ValidationRule(
            rule_type=ValidationType.MAX_DEPENDENCY_DEPTH,
            description="Check depth",
            params={"resource_dirs": [".claude/skills"], "max_depth": 2},
            failure_message="Depth {actual_depth} exceeds max {max_depth}",
            expected_behavior="Max 2",
        )

        result = validator.validate(rule, all_bundles[2], all_bundles)

        if result:
            # Placeholders should be replaced in the message
            assert "{actual_depth}" not in result.observed_issue
            assert "{max_depth}" not in result.observed_issue
            # Actual values should be present
            assert str(result.failure_details["actual_depth"]) in result.observed_issue

    def test_all_validators_produce_serializable_output(self, complex_project, all_bundles):
        """Test that all validators produce JSON-serializable output."""
        validators_and_bundles = [
            (ClaudeCircularDependenciesValidator(), all_bundles[0]),
            (ClaudeMaxDependencyDepthValidator(), all_bundles[2]),
            (ClaudeDependencyDuplicateValidator(), all_bundles[6]),
        ]

        rules = [
            ValidationRule(
                rule_type=ValidationType.CIRCULAR_DEPENDENCIES,
                description="Check",
                params={"resource_dirs": [".claude/skills"]},
                failure_message="Issue",
                expected_behavior="Expected",
            ),
            ValidationRule(
                rule_type=ValidationType.MAX_DEPENDENCY_DEPTH,
                description="Check",
                params={"resource_dirs": [".claude/skills"], "max_depth": 2},
                failure_message="Issue",
                expected_behavior="Expected",
            ),
            ValidationRule(
                rule_type=ValidationType.DEPENDENCY_DUPLICATE,
                description="Check",
                params={"resource_dirs": [".claude/skills"]},
                failure_message="Issue",
                expected_behavior="Expected",
            ),
        ]

        for (validator, bundle), rule in zip(validators_and_bundles, rules):
            result = validator.validate(rule, bundle, all_bundles)
            if result:
                # Convert entire DocumentRule to dict (simulating JSON export)
                result_dict = result.model_dump()

                # Should be JSON serializable
                try:
                    json.dumps(result_dict)
                except (TypeError, ValueError) as e:
                    pytest.fail(
                        f"Result not JSON serializable for {validator.__class__.__name__}: {e}"
                    )
