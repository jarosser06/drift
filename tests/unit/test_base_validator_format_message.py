"""Tests for BaseValidator._format_message() method."""

import pytest

from drift.validation.validators.base import BaseValidator


class ConcreteValidator(BaseValidator):
    """Concrete implementation of BaseValidator for testing."""

    validation_type = "test:concrete"

    @property
    def computation_type(self):
        """Return computation type."""
        return "programmatic"

    def validate(self, rule, bundle, all_bundles=None):
        """Perform validation (dummy implementation)."""
        return None


class TestBaseValidatorFormatMessage:
    """Tests for BaseValidator._format_message() method."""

    @pytest.fixture
    def validator(self):
        """Create validator instance for testing."""
        return ConcreteValidator()

    def test_format_message_with_single_placeholder(self, validator):
        """Test formatting message with single placeholder."""
        template = "Found issue: {issue_type}"
        details = {"issue_type": "circular dependency"}

        result = validator._format_message(template, details)

        assert result == "Found issue: circular dependency"

    def test_format_message_with_multiple_placeholders(self, validator):
        """Test formatting message with multiple placeholders."""
        template = "Depth {actual_depth} exceeds max {max_depth}"
        details = {"actual_depth": 5, "max_depth": 3}

        result = validator._format_message(template, details)

        assert result == "Depth 5 exceeds max 3"

    def test_format_message_with_string_values(self, validator):
        """Test formatting message with string values."""
        template = "Circular dependency: {circular_path}"
        details = {"circular_path": "A → B → C → A"}

        result = validator._format_message(template, details)

        assert result == "Circular dependency: A → B → C → A"

    def test_format_message_with_integer_values(self, validator):
        """Test formatting message with integer values."""
        template = "Found {count} violations"
        details = {"count": 42}

        result = validator._format_message(template, details)

        assert result == "Found 42 violations"

    def test_format_message_with_missing_placeholder(self, validator):
        """Test that missing placeholders are left unchanged."""
        template = "Found {issue_type} in {location}"
        details = {"issue_type": "circular dependency"}  # missing 'location'

        result = validator._format_message(template, details)

        # Missing placeholder should remain in template
        assert result == "Found circular dependency in {location}"

    def test_format_message_with_empty_details(self, validator):
        """Test formatting message with empty details dictionary."""
        template = "Found {issue_type}"
        details = {}

        result = validator._format_message(template, details)

        # Placeholder should remain unchanged
        assert result == "Found {issue_type}"

    def test_format_message_with_none_details(self, validator):
        """Test formatting message with None details."""
        template = "Found {issue_type}"
        details = None

        result = validator._format_message(template, details)

        # Should return template unchanged
        assert result == "Found {issue_type}"

    def test_format_message_with_no_placeholders(self, validator):
        """Test formatting message with no placeholders."""
        template = "No placeholders here"
        details = {"unused": "value"}

        result = validator._format_message(template, details)

        # Should return template unchanged
        assert result == "No placeholders here"

    def test_format_message_with_extra_details(self, validator):
        """Test formatting message with extra unused details."""
        template = "Found {issue_type}"
        details = {
            "issue_type": "circular dependency",
            "extra_field": "not used",
            "another_field": 123,
        }

        result = validator._format_message(template, details)

        # Only used placeholder should be replaced
        assert result == "Found circular dependency"

    def test_format_message_with_special_characters(self, validator):
        """Test formatting with special characters in values."""
        template = "Path: {file_path}"
        details = {"file_path": "/path/to/file.md"}

        result = validator._format_message(template, details)

        assert result == "Path: /path/to/file.md"

    def test_format_message_with_unicode_characters(self, validator):
        """Test formatting with unicode characters in values."""
        template = "Cycle: {circular_path}"
        details = {"circular_path": "skill-a → skill-b → skill-c"}

        result = validator._format_message(template, details)

        assert result == "Cycle: skill-a → skill-b → skill-c"

    def test_format_message_with_nested_braces_in_value(self, validator):
        """Test formatting when value contains braces."""
        template = "Error: {error_msg}"
        details = {"error_msg": "Expected {format} but got {actual}"}

        result = validator._format_message(template, details)

        # Value with braces should be inserted as-is
        assert result == "Error: Expected {format} but got {actual}"

    def test_format_message_preserves_multiple_placeholders(self, validator):
        """Test that same placeholder can appear multiple times."""
        template = "{name} depends on {name} (self-reference)"
        details = {"name": "skill-a"}

        result = validator._format_message(template, details)

        # Both instances should be replaced
        assert result == "skill-a depends on skill-a (self-reference)"

    def test_format_message_with_complex_template(self, validator):
        """Test formatting complex multi-line template."""
        template = (
            "Found {violation_count} violations:\n"
            "- Max depth: {max_depth}\n"
            "- Actual depth: {actual_depth}\n"
            "- Chain: {dependency_chain}"
        )
        details = {
            "violation_count": 3,
            "max_depth": 5,
            "actual_depth": 7,
            "dependency_chain": "A → B → C → D → E → F → G",
        }

        result = validator._format_message(template, details)

        expected = (
            "Found 3 violations:\n"
            "- Max depth: 5\n"
            "- Actual depth: 7\n"
            "- Chain: A → B → C → D → E → F → G"
        )
        assert result == expected

    def test_format_message_with_boolean_values(self, validator):
        """Test formatting with boolean values."""
        template = "Validation passed: {passed}"
        details = {"passed": True}

        result = validator._format_message(template, details)

        assert result == "Validation passed: True"

    def test_format_message_with_float_values(self, validator):
        """Test formatting with float values."""
        template = "Coverage: {coverage}%"
        details = {"coverage": 95.5}

        result = validator._format_message(template, details)

        assert result == "Coverage: 95.5%"

    def test_format_message_with_list_values(self, validator):
        """Test formatting with list values converted to string."""
        template = "Files: {files}"
        details = {"files": ["file1.md", "file2.md", "file3.md"]}

        result = validator._format_message(template, details)

        # List should be converted to string representation
        assert "file1.md" in result
        assert "file2.md" in result
        assert "file3.md" in result

    def test_format_message_with_dict_values(self, validator):
        """Test formatting with dict values converted to string."""
        template = "Metadata: {metadata}"
        details = {"metadata": {"key": "value", "count": 42}}

        result = validator._format_message(template, details)

        # Dict should be converted to string representation
        assert "key" in result or "metadata" in result

    def test_format_message_empty_string_value(self, validator):
        """Test formatting with empty string value."""
        template = "Message: {message}"
        details = {"message": ""}

        result = validator._format_message(template, details)

        assert result == "Message: "

    def test_format_message_zero_value(self, validator):
        """Test formatting with zero value."""
        template = "Count: {count}"
        details = {"count": 0}

        result = validator._format_message(template, details)

        assert result == "Count: 0"

    def test_format_message_preserves_literal_braces(self, validator):
        """Test that double braces are preserved as literal braces."""
        # Note: This tests the current simple implementation behavior
        # The method uses simple string replacement, not format()
        template = "Use {{placeholder}} syntax for {value}"
        details = {"value": "interpolation"}

        result = validator._format_message(template, details)

        # With simple replacement, double braces stay as-is
        assert result == "Use {{placeholder}} syntax for interpolation"

    @pytest.mark.parametrize(
        "template,details,expected",
        [
            # Basic cases
            ("Error: {msg}", {"msg": "test"}, "Error: test"),
            ("{a} and {b}", {"a": 1, "b": 2}, "1 and 2"),
            # Edge cases
            ("", {}, ""),
            ("No placeholders", {"key": "val"}, "No placeholders"),
            ("{key}", {}, "{key}"),  # Missing key
            # Special values
            ("{val}", {"val": None}, "None"),  # None converts to string "None"
            ("{val}", {"val": ""}, ""),  # Empty string replaces placeholder
        ],
    )
    def test_format_message_parametrized(self, validator, template, details, expected):
        """Test various template/details combinations."""
        result = validator._format_message(template, details)
        assert result == expected

    def test_format_message_with_none_value_in_details(self, validator):
        """Test that None values in details dict are converted to string."""
        template = "Value: {value}"
        details = {"value": None}

        result = validator._format_message(template, details)

        # None should be converted to string "None"
        assert result == "Value: None"
