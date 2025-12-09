"""Tests for JsonSchemaValidator."""

import json
import sys

import pytest

from drift.config.models import ValidationRule
from drift.core.types import DocumentBundle, DocumentFile
from drift.validation.validators.core.format_validators import JsonSchemaValidator


class TestJsonSchemaValidator:
    """Tests for JsonSchemaValidator."""

    @pytest.fixture
    def validator(self):
        """Create validator instance."""
        return JsonSchemaValidator()

    @pytest.fixture
    def tmp_path(self, tmp_path):
        """Provide tmp_path fixture."""
        return tmp_path

    @pytest.fixture
    def bundle_with_json(self, tmp_path):
        """Create bundle with a test JSON file."""
        test_file = tmp_path / "config.json"
        content = json.dumps({"name": "test", "version": "1.0.0", "count": 42})
        test_file.write_text(content)

        return DocumentBundle(
            bundle_id="test",
            bundle_type="mixed",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[
                DocumentFile(
                    relative_path="config.json",
                    content=content,
                    file_path=str(test_file),
                )
            ],
        )

    # ==================== Basic Validation Tests ====================

    def test_valid_json_with_inline_schema(self, validator, tmp_path):
        """Test that validation passes with valid JSON and inline schema."""
        test_file = tmp_path / "data.json"
        test_file.write_text(json.dumps({"name": "John", "age": 30}))

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="mixed",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[DocumentFile(relative_path="data.json", content="", file_path=str(test_file))],
        )

        schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}, "age": {"type": "number"}},
            "required": ["name", "age"],
        }

        rule = ValidationRule(
            rule_type="core:json_schema",
            description="Validate data.json",
            params={"file_path": "data.json", "schema": schema},
            failure_message="Invalid JSON structure",
            expected_behavior="Should match schema",
        )

        result = validator.validate(rule, bundle)
        assert result is None

    def test_invalid_json_missing_required_field(self, validator, tmp_path):
        """Test that validation fails when required field is missing."""
        test_file = tmp_path / "data.json"
        test_file.write_text(json.dumps({"name": "John"}))  # Missing 'age'

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="mixed",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[DocumentFile(relative_path="data.json", content="", file_path=str(test_file))],
        )

        schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}, "age": {"type": "number"}},
            "required": ["name", "age"],
        }

        rule = ValidationRule(
            rule_type="core:json_schema",
            description="Validate data.json",
            params={"file_path": "data.json", "schema": schema},
            failure_message="Invalid JSON structure",
            expected_behavior="Should match schema",
        )

        result = validator.validate(rule, bundle)
        assert result is not None
        assert "age" in result.observed_issue or "required" in result.observed_issue.lower()

    def test_invalid_json_wrong_type(self, validator, tmp_path):
        """Test that validation fails when field has wrong type."""
        test_file = tmp_path / "data.json"
        test_file.write_text(json.dumps({"name": "John", "age": "thirty"}))  # age should be number

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="mixed",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[DocumentFile(relative_path="data.json", content="", file_path=str(test_file))],
        )

        schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}, "age": {"type": "number"}},
            "required": ["name", "age"],
        }

        rule = ValidationRule(
            rule_type="core:json_schema",
            description="Validate data.json",
            params={"file_path": "data.json", "schema": schema},
            failure_message="Invalid JSON structure",
            expected_behavior="Should match schema",
        )

        result = validator.validate(rule, bundle)
        assert result is not None
        assert "age" in result.observed_issue or "type" in result.observed_issue.lower()

    # ==================== External Schema File Tests ====================

    def test_validation_with_external_schema_file(self, validator, tmp_path):
        """Test validation using external schema file."""
        # Create JSON file
        data_file = tmp_path / "data.json"
        data_file.write_text(json.dumps({"name": "John", "age": 30}))

        # Create schema file
        schema_file = tmp_path / "schema.json"
        schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}, "age": {"type": "number"}},
            "required": ["name", "age"],
        }
        schema_file.write_text(json.dumps(schema))

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="mixed",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[DocumentFile(relative_path="data.json", content="", file_path=str(data_file))],
        )

        rule = ValidationRule(
            rule_type="core:json_schema",
            description="Validate data.json",
            params={"file_path": "data.json", "schema_file": "schema.json"},
            failure_message="Invalid JSON structure",
            expected_behavior="Should match schema",
        )

        result = validator.validate(rule, bundle)
        assert result is None

    def test_external_schema_file_not_found(self, validator, bundle_with_json):
        """Test that validation fails gracefully when schema file doesn't exist."""
        rule = ValidationRule(
            rule_type="core:json_schema",
            description="Validate config.json",
            params={"file_path": "config.json", "schema_file": "nonexistent_schema.json"},
            failure_message="Invalid JSON structure",
            expected_behavior="Should match schema",
        )

        result = validator.validate(rule, bundle_with_json)
        assert result is not None
        assert "Schema file not found" in result.observed_issue

    def test_external_schema_file_invalid_json(self, validator, tmp_path):
        """Test that validation fails when schema file contains invalid JSON."""
        data_file = tmp_path / "data.json"
        data_file.write_text(json.dumps({"name": "John"}))

        schema_file = tmp_path / "bad_schema.json"
        schema_file.write_text("{invalid json}")

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="mixed",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[DocumentFile(relative_path="data.json", content="", file_path=str(data_file))],
        )

        rule = ValidationRule(
            rule_type="core:json_schema",
            description="Validate data.json",
            params={"file_path": "data.json", "schema_file": "bad_schema.json"},
            failure_message="Invalid JSON structure",
            expected_behavior="Should match schema",
        )

        result = validator.validate(rule, bundle)
        assert result is not None
        assert "Invalid JSON in schema file" in result.observed_issue

    # ==================== Error Handling Tests ====================

    def test_missing_file_path(self, validator, bundle_with_json):
        """Test that validator raises error when file_path is missing."""
        rule = ValidationRule(
            rule_type="core:json_schema",
            description="No file path",
            params={"schema": {"type": "object"}},
            failure_message="Error",
            expected_behavior="Should error",
        )

        with pytest.raises(ValueError, match="requires params.file_path"):
            validator.validate(rule, bundle_with_json)

    def test_missing_params(self, validator, bundle_with_json):
        """Test that validation fails when schema/schema_file is missing."""
        rule = ValidationRule(
            rule_type="core:json_schema",
            description="No schema",
            params={"file_path": "config.json"},
            failure_message="Error",
            expected_behavior="Should error",
        )

        result = validator.validate(rule, bundle_with_json)
        assert result is not None
        assert "requires 'schema' or 'schema_file'" in result.observed_issue

    def test_missing_schema_and_schema_file(self, validator, bundle_with_json):
        """Test that validation fails when neither schema nor schema_file provided."""
        rule = ValidationRule(
            rule_type="core:json_schema",
            description="No schema",
            params={"file_path": "config.json", "other_param": "value"},
            failure_message="Error",
            expected_behavior="Should error",
        )

        result = validator.validate(rule, bundle_with_json)
        assert result is not None
        assert "requires 'schema' or 'schema_file'" in result.observed_issue

    def test_file_not_found(self, validator, bundle_with_json):
        """Test validation when JSON file doesn't exist."""
        rule = ValidationRule(
            rule_type="core:json_schema",
            description="Check nonexistent file",
            params={"file_path": "nonexistent.json", "schema": {"type": "object"}},
            failure_message="File not found",
            expected_behavior="File should exist",
        )

        result = validator.validate(rule, bundle_with_json)
        assert result is not None
        assert "does not exist" in result.observed_issue

    def test_invalid_json_syntax(self, validator, tmp_path):
        """Test validation with malformed JSON file."""
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("{not valid json}")

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="mixed",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[DocumentFile(relative_path="bad.json", content="", file_path=str(bad_file))],
        )

        rule = ValidationRule(
            rule_type="core:json_schema",
            description="Validate bad JSON",
            params={"file_path": "bad.json", "schema": {"type": "object"}},
            failure_message="Invalid JSON",
            expected_behavior="Should be valid JSON",
        )

        result = validator.validate(rule, bundle)
        assert result is not None
        assert "Invalid JSON" in result.observed_issue

    def test_missing_jsonschema_package(self, validator, tmp_path, monkeypatch):
        """Test that validation fails gracefully when jsonschema package is missing."""
        test_file = tmp_path / "data.json"
        test_file.write_text(json.dumps({"name": "test"}))

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="mixed",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[DocumentFile(relative_path="data.json", content="", file_path=str(test_file))],
        )

        rule = ValidationRule(
            rule_type="core:json_schema",
            description="Validate JSON",
            params={"file_path": "data.json", "schema": {"type": "object"}},
            failure_message="Error",
            expected_behavior="Should validate",
        )

        # Make the import fail
        import builtins

        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "jsonschema":
                raise ImportError("No module named 'jsonschema'")
            return original_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)
        monkeypatch.delitem(sys.modules, "jsonschema", raising=False)

        result = validator.validate(rule, bundle)
        assert result is not None
        assert "pip install jsonschema" in result.observed_issue

    # ==================== Complex Schema Tests ====================

    def test_nested_object_validation(self, validator, tmp_path):
        """Test validation with nested objects."""
        test_file = tmp_path / "nested.json"
        data = {"user": {"name": "John", "email": "john@example.com"}, "active": True}
        test_file.write_text(json.dumps(data))

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="mixed",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[DocumentFile(relative_path="nested.json", content="", file_path=str(test_file))],
        )

        schema = {
            "type": "object",
            "properties": {
                "user": {
                    "type": "object",
                    "properties": {"name": {"type": "string"}, "email": {"type": "string"}},
                    "required": ["name", "email"],
                },
                "active": {"type": "boolean"},
            },
            "required": ["user", "active"],
        }

        rule = ValidationRule(
            rule_type="core:json_schema",
            description="Validate nested structure",
            params={"file_path": "nested.json", "schema": schema},
            failure_message="Invalid structure",
            expected_behavior="Should match nested schema",
        )

        result = validator.validate(rule, bundle)
        assert result is None

    def test_array_validation(self, validator, tmp_path):
        """Test validation with arrays."""
        test_file = tmp_path / "array.json"
        data = {"items": [{"id": 1, "name": "Item 1"}, {"id": 2, "name": "Item 2"}]}
        test_file.write_text(json.dumps(data))

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="mixed",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[DocumentFile(relative_path="array.json", content="", file_path=str(test_file))],
        )

        schema = {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {"id": {"type": "number"}, "name": {"type": "string"}},
                        "required": ["id", "name"],
                    },
                }
            },
        }

        rule = ValidationRule(
            rule_type="core:json_schema",
            description="Validate array",
            params={"file_path": "array.json", "schema": schema},
            failure_message="Invalid array structure",
            expected_behavior="Should match array schema",
        )

        result = validator.validate(rule, bundle)
        assert result is None

    def test_enum_validation(self, validator, tmp_path):
        """Test validation with enum constraints."""
        test_file = tmp_path / "enum.json"
        test_file.write_text(json.dumps({"status": "active"}))

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="mixed",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[DocumentFile(relative_path="enum.json", content="", file_path=str(test_file))],
        )

        schema = {
            "type": "object",
            "properties": {"status": {"type": "string", "enum": ["active", "inactive", "pending"]}},
        }

        rule = ValidationRule(
            rule_type="core:json_schema",
            description="Validate enum",
            params={"file_path": "enum.json", "schema": schema},
            failure_message="Invalid status",
            expected_behavior="Status should be valid enum value",
        )

        result = validator.validate(rule, bundle)
        assert result is None

    def test_enum_validation_invalid_value(self, validator, tmp_path):
        """Test validation fails with invalid enum value."""
        test_file = tmp_path / "enum.json"
        test_file.write_text(json.dumps({"status": "invalid_status"}))

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="mixed",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[DocumentFile(relative_path="enum.json", content="", file_path=str(test_file))],
        )

        schema = {
            "type": "object",
            "properties": {"status": {"type": "string", "enum": ["active", "inactive", "pending"]}},
        }

        rule = ValidationRule(
            rule_type="core:json_schema",
            description="Validate enum",
            params={"file_path": "enum.json", "schema": schema},
            failure_message="Invalid status",
            expected_behavior="Status should be valid enum value",
        )

        result = validator.validate(rule, bundle)
        assert result is not None

    def test_computation_type(self, validator):
        """Test that computation_type is programmatic."""
        assert validator.computation_type == "programmatic"

    def test_empty_json_object(self, validator, tmp_path):
        """Test validation with empty JSON object."""
        test_file = tmp_path / "empty.json"
        test_file.write_text(json.dumps({}))

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="mixed",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[DocumentFile(relative_path="empty.json", content="", file_path=str(test_file))],
        )

        schema = {"type": "object", "properties": {}}

        rule = ValidationRule(
            rule_type="core:json_schema",
            description="Validate empty object",
            params={"file_path": "empty.json", "schema": schema},
            failure_message="Invalid JSON",
            expected_behavior="Should be valid empty object",
        )

        result = validator.validate(rule, bundle)
        assert result is None

    def test_additional_properties_allowed(self, validator, tmp_path):
        """Test validation allows additional properties by default."""
        test_file = tmp_path / "data.json"
        test_file.write_text(json.dumps({"name": "John", "age": 30, "extra": "value"}))

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="mixed",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[DocumentFile(relative_path="data.json", content="", file_path=str(test_file))],
        )

        schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}, "age": {"type": "number"}},
        }

        rule = ValidationRule(
            rule_type="core:json_schema",
            description="Validate with extra properties",
            params={"file_path": "data.json", "schema": schema},
            failure_message="Invalid JSON",
            expected_behavior="Should allow additional properties",
        )

        result = validator.validate(rule, bundle)
        assert result is None

    def test_additional_properties_not_allowed(self, validator, tmp_path):
        """Test validation fails when additional properties are not allowed."""
        test_file = tmp_path / "data.json"
        test_file.write_text(json.dumps({"name": "John", "age": 30, "extra": "value"}))

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="mixed",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[DocumentFile(relative_path="data.json", content="", file_path=str(test_file))],
        )

        schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}, "age": {"type": "number"}},
            "additionalProperties": False,
        }

        rule = ValidationRule(
            rule_type="core:json_schema",
            description="Validate strict schema",
            params={"file_path": "data.json", "schema": schema},
            failure_message="Invalid JSON",
            expected_behavior="Should not allow additional properties",
        )

        result = validator.validate(rule, bundle)
        assert result is not None

    def test_file_read_generic_exception(self, validator, tmp_path, monkeypatch):
        """Test generic exception during file reading."""
        test_file = tmp_path / "data.json"
        test_file.write_text(json.dumps({"name": "test"}))

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="mixed",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[DocumentFile(relative_path="data.json", content="", file_path=str(test_file))],
        )

        # Mock open to raise a generic exception
        import builtins

        original_open = builtins.open

        def mock_open(path, *args, **kwargs):
            if "data.json" in str(path):
                raise PermissionError("Permission denied")
            return original_open(path, *args, **kwargs)

        monkeypatch.setattr(builtins, "open", mock_open)

        schema = {"type": "object", "properties": {"name": {"type": "string"}}}

        rule = ValidationRule(
            rule_type="core:json_schema",
            description="Test rule",
            params={"file_path": "data.json", "schema": schema},
            failure_message="Failure",
            expected_behavior="Expected",
        )

        result = validator.validate(rule, bundle)
        assert result is not None
        assert "Failed to read file" in result.observed_issue

    def test_generic_validation_coverage(self, validator, tmp_path):
        """Test validation with valid data to ensure code paths are covered."""
        test_file = tmp_path / "data.json"
        test_file.write_text(json.dumps({"name": "test", "age": 30}))

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="mixed",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[DocumentFile(relative_path="data.json", content="", file_path=str(test_file))],
        )

        schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}, "age": {"type": "number"}},
            "required": ["name", "age"],
        }

        rule = ValidationRule(
            rule_type="core:json_schema",
            description="Test rule",
            params={"file_path": "data.json", "schema": schema},
            failure_message="Failure",
            expected_behavior="Expected",
        )

        result = validator.validate(rule, bundle)
        assert result is None  # Should pass validation

    def test_schema_file_read_exception(self, validator, tmp_path, monkeypatch):
        """Test exception when reading schema file."""
        test_file = tmp_path / "data.json"
        test_file.write_text(json.dumps({"name": "test"}))

        schema_file = tmp_path / "schema.json"
        schema_file.write_text(json.dumps({"type": "object"}))

        _ = DocumentBundle(
            bundle_id="test",
            bundle_type="mixed",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[DocumentFile(relative_path="data.json", content="", file_path=str(test_file))],
        )

        # Mock open to raise exception for schema file
        import builtins

        original_open = builtins.open

        def mock_open(path, *args, **kwargs):
            if "schema.json" in str(path):
                raise PermissionError("Permission denied")
            return original_open(path, *args, **kwargs)

        monkeypatch.setattr(builtins, "open", mock_open)

        _ = ValidationRule(
            rule_type="core:json_schema",
            description="Test rule",
            params={"file_path": "data.json", "schema_file": "schema.json"},
            failure_message="Failure",
            expected_behavior="Expected",
        )

    def test_trigger_schema_error(self, validator, tmp_path):
        """Test that SchemaError is caught when schema is structurally invalid."""
        test_file = tmp_path / "data.json"
        test_file.write_text(json.dumps({"name": "test"}))

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="mixed",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[DocumentFile(relative_path="data.json", content="", file_path=str(test_file))],
        )

        # Schema with invalid type for "type" field (should be string or array, not number)
        schema = {
            "type": 123,  # Invalid - type should be string not number
            "properties": {"name": {"type": "string"}},
        }

        rule = ValidationRule(
            rule_type="core:json_schema",
            description="Test rule",
            params={"file_path": "data.json", "schema": schema},
            failure_message="Failure",
            expected_behavior="Expected",
        )

        result = validator.validate(rule, bundle)
        # Should catch SchemaError and return failure
        assert result is not None
        assert "Invalid schema" in result.observed_issue
