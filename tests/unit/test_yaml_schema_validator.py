"""Tests for YamlSchemaValidator."""

import json

import pytest

from drift.config.models import ValidationRule
from drift.core.types import DocumentBundle, DocumentFile
from drift.validation.validators.core.format_validators import YamlSchemaValidator


class TestYamlSchemaValidator:
    """Tests for YamlSchemaValidator."""

    @pytest.fixture
    def validator(self):
        """Create validator instance."""
        return YamlSchemaValidator(loader=None)

    @pytest.fixture
    def bundle(self, tmp_path):
        """Create test bundle."""
        test_file = tmp_path / "config.yaml"
        content = "name: TestProject\nversion: '1.0.0'\ndebug: true\n"
        test_file.write_text(content)

        return DocumentBundle(
            bundle_id="test",
            bundle_type="mixed",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[
                DocumentFile(
                    relative_path="config.yaml",
                    content=content,
                    file_path=str(test_file),
                )
            ],
        )

    def test_valid_yaml_with_inline_schema(self, validator, bundle, tmp_path):
        """Test that validation passes with valid YAML and inline schema."""
        test_file = tmp_path / "config.yaml"
        test_file.write_text(
            "name: TestProject\nversion: '1.0.0'\nsettings:\n  debug: true\n  port: 8080\n"
        )

        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "version": {"type": "string"},
                "settings": {
                    "type": "object",
                    "properties": {
                        "debug": {"type": "boolean"},
                        "port": {"type": "number", "minimum": 1, "maximum": 65535},
                    },
                    "required": ["debug", "port"],
                },
            },
            "required": ["name", "version", "settings"],
        }

        rule = ValidationRule(
            rule_type="core:yaml_schema",
            description="Validate config.yaml",
            params={"file_path": "config.yaml", "schema": schema},
            failure_message="Invalid YAML structure",
            expected_behavior="Should match schema",
        )

        result = validator.validate(rule, bundle)
        assert result is None

    def test_invalid_yaml_missing_required_field(self, validator, bundle, tmp_path):
        """Test that validation fails when required field is missing."""
        test_file = tmp_path / "config.yaml"
        test_file.write_text("name: TestProject\nversion: '1.0.0'\n")  # Missing settings

        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "version": {"type": "string"},
                "settings": {"type": "object"},
            },
            "required": ["name", "version", "settings"],
        }

        rule = ValidationRule(
            rule_type="core:yaml_schema",
            description="Validate config.yaml",
            params={"file_path": "config.yaml", "schema": schema},
            failure_message="Invalid YAML structure",
            expected_behavior="Should match schema",
        )

        result = validator.validate(rule, bundle)
        assert result is not None
        assert "'settings' is a required property" in result.observed_issue

    def test_invalid_yaml_wrong_type(self, validator, bundle, tmp_path):
        """Test that validation fails when field has wrong type."""
        test_file = tmp_path / "config.yaml"
        test_file.write_text("name: TestProject\nversion: 123\n")  # version should be string

        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "version": {"type": "string"},
            },
            "required": ["name", "version"],
        }

        rule = ValidationRule(
            rule_type="core:yaml_schema",
            description="Validate config.yaml",
            params={"file_path": "config.yaml", "schema": schema},
            failure_message="Invalid YAML structure",
            expected_behavior="Should match schema",
        )

        result = validator.validate(rule, bundle)
        assert result is not None
        assert "123 is not of type 'string'" in result.observed_issue

    def test_validation_with_external_schema_file(self, validator, bundle, tmp_path):
        """Test validation with external schema file."""
        # Create YAML data file
        data_file = tmp_path / "data.yaml"
        data_file.write_text("username: john_doe\nemail: john@example.com\nage: 30\n")

        # Create schema file
        schema_file = tmp_path / "schema.json"
        schema = {
            "type": "object",
            "properties": {
                "username": {"type": "string"},
                "email": {"type": "string", "format": "email"},
                "age": {"type": "integer", "minimum": 0},
            },
            "required": ["username", "email"],
        }
        schema_file.write_text(json.dumps(schema))

        rule = ValidationRule(
            rule_type="core:yaml_schema",
            description="Validate data.yaml",
            params={"file_path": "data.yaml", "schema_file": "schema.json"},
            failure_message="YAML doesn't match schema",
            expected_behavior="Should conform to schema",
        )

        result = validator.validate(rule, bundle)
        assert result is None

    def test_external_schema_file_not_found(self, validator, bundle, tmp_path):
        """Test error when schema file doesn't exist."""
        data_file = tmp_path / "data.yaml"
        data_file.write_text("key: value\n")

        rule = ValidationRule(
            rule_type="core:yaml_schema",
            description="Validate data.yaml",
            params={"file_path": "data.yaml", "schema_file": "nonexistent.json"},
            failure_message="YAML doesn't match schema",
            expected_behavior="Should conform to schema",
        )

        result = validator.validate(rule, bundle)
        assert result is not None
        assert "Schema file not found" in result.observed_issue

    def test_missing_file_path(self, validator, bundle):
        """Test that validator validates bundle files when file_path is missing (bundle mode)."""
        rule = ValidationRule(
            rule_type="core:yaml_schema",
            description="Test rule",
            params={
                "schema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "version": {"type": "string"},
                        "debug": {"type": "boolean"},
                    },
                    "required": ["name", "version", "debug"],
                }
            },
            failure_message="Failure",
            expected_behavior="Should validate bundle files",
        )

        # Should validate all files in the bundle and pass since config.yaml matches the schema
        result = validator.validate(rule, bundle)
        assert result is None

    def test_missing_params(self, validator, bundle, tmp_path):
        """Test that validation fails when schema/schema_file is missing."""
        test_file = tmp_path / "data.yaml"
        test_file.write_text("key: value\n")

        rule = ValidationRule(
            rule_type="core:yaml_schema",
            description="Test rule",
            params={"file_path": "data.yaml"},
            failure_message="Failure",
            expected_behavior="Expected",
        )

        result = validator.validate(rule, bundle)
        assert result is not None
        assert "requires 'schema' or 'schema_file'" in result.observed_issue

    def test_missing_schema_and_schema_file_in_params(self, validator, bundle, tmp_path):
        """Test error when params has neither schema nor schema_file."""
        test_file = tmp_path / "data.yaml"
        test_file.write_text("key: value\n")

        rule = ValidationRule(
            rule_type="core:yaml_schema",
            description="Test rule",
            params={
                "file_path": "data.yaml",
                "other_key": "value",
            },  # Has params but no schema/schema_file
            failure_message="Failure",
            expected_behavior="Expected",
        )

        result = validator.validate(rule, bundle)
        assert result is not None
        assert "requires 'schema' or 'schema_file'" in result.observed_issue

    def test_file_not_found(self, validator, bundle):
        """Test error when YAML file doesn't exist."""
        rule = ValidationRule(
            rule_type="core:yaml_schema",
            description="Test rule",
            params={"file_path": "nonexistent.yaml", "schema": {"type": "object"}},
            failure_message="Failure",
            expected_behavior="Expected",
        )

        result = validator.validate(rule, bundle)
        assert result is not None
        assert "does not exist" in result.observed_issue

    def test_invalid_yaml_syntax(self, validator, bundle, tmp_path):
        """Test error when YAML has syntax errors."""
        test_file = tmp_path / "invalid.yaml"
        test_file.write_text("key: value\n  bad indentation:\n")

        rule = ValidationRule(
            rule_type="core:yaml_schema",
            description="Test rule",
            params={"file_path": "invalid.yaml", "schema": {"type": "object"}},
            failure_message="Failure",
            expected_behavior="Expected",
        )

        result = validator.validate(rule, bundle)
        assert result is not None
        assert "Invalid YAML" in result.observed_issue

    def test_missing_yaml_package(self, validator, bundle, tmp_path, monkeypatch):
        """Test error when pyyaml package is not installed."""
        # Hide yaml module
        import sys

        monkeypatch.setitem(sys.modules, "yaml", None)

        test_file = tmp_path / "data.yaml"
        test_file.write_text("key: value\n")

        rule = ValidationRule(
            rule_type="core:yaml_schema",
            description="Test rule",
            params={"file_path": "data.yaml", "schema": {"type": "object"}},
            failure_message="Failure",
            expected_behavior="Expected",
        )

        result = validator.validate(rule, bundle)
        assert result is not None
        assert "requires 'pyyaml' package" in result.observed_issue

    def test_nested_object_validation(self, validator, bundle, tmp_path):
        """Test validation with nested objects."""
        test_file = tmp_path / "config.yaml"
        test_file.write_text(
            "database:\n"
            "  host: localhost\n"
            "  port: 5432\n"
            "  credentials:\n"
            "    username: admin\n"
            "    password: secret\n"
        )

        schema = {
            "type": "object",
            "properties": {
                "database": {
                    "type": "object",
                    "properties": {
                        "host": {"type": "string"},
                        "port": {"type": "integer"},
                        "credentials": {
                            "type": "object",
                            "properties": {
                                "username": {"type": "string"},
                                "password": {"type": "string"},
                            },
                            "required": ["username", "password"],
                        },
                    },
                    "required": ["host", "port"],
                }
            },
            "required": ["database"],
        }

        rule = ValidationRule(
            rule_type="core:yaml_schema",
            description="Validate nested config",
            params={"file_path": "config.yaml", "schema": schema},
            failure_message="Invalid structure",
            expected_behavior="Should match nested schema",
        )

        result = validator.validate(rule, bundle)
        assert result is None

    def test_array_validation(self, validator, bundle, tmp_path):
        """Test validation with arrays."""
        test_file = tmp_path / "list.yaml"
        test_file.write_text(
            "items:\n  - name: item1\n    value: 10\n  - name: item2\n    value: 20\n"
        )

        schema = {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "value": {"type": "number"},
                        },
                        "required": ["name", "value"],
                    },
                }
            },
        }

        rule = ValidationRule(
            rule_type="core:yaml_schema",
            description="Validate array",
            params={"file_path": "list.yaml", "schema": schema},
            failure_message="Invalid array",
            expected_behavior="Should match array schema",
        )

        result = validator.validate(rule, bundle)
        assert result is None

    def test_computation_type(self, validator):
        """Test that validator reports correct computation type."""
        assert validator.computation_type == "programmatic"

    def test_file_read_generic_exception(self, validator, tmp_path, monkeypatch):
        """Test generic exception during file reading."""
        test_file = tmp_path / "data.yaml"
        test_file.write_text("name: test")

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="mixed",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[DocumentFile(relative_path="data.yaml", content="", file_path=str(test_file))],
        )

        # Mock open to raise a generic exception
        import builtins

        original_open = builtins.open

        def mock_open(path, *args, **kwargs):
            if "data.yaml" in str(path):
                raise PermissionError("Permission denied")
            return original_open(path, *args, **kwargs)

        monkeypatch.setattr(builtins, "open", mock_open)

        schema = {"type": "object", "properties": {"name": {"type": "string"}}}

        rule = ValidationRule(
            rule_type="core:yaml_schema",
            description="Test rule",
            params={"file_path": "data.yaml", "schema": schema},
            failure_message="Failure",
            expected_behavior="Expected",
        )

        result = validator.validate(rule, bundle)
        assert result is not None
        assert "Failed to read file" in result.observed_issue

    def test_missing_jsonschema_for_validation(self, validator, tmp_path, monkeypatch):
        """Test missing jsonschema package during validation."""
        test_file = tmp_path / "data.yaml"
        test_file.write_text("name: test")

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="mixed",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[DocumentFile(relative_path="data.yaml", content="", file_path=str(test_file))],
        )

        # Mock import to fail for jsonschema
        import builtins

        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "jsonschema":
                raise ImportError("No module named 'jsonschema'")
            return original_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)

        schema = {"type": "object", "properties": {"name": {"type": "string"}}}

        rule = ValidationRule(
            rule_type="core:yaml_schema",
            description="Test rule",
            params={"file_path": "data.yaml", "schema": schema},
            failure_message="Failure",
            expected_behavior="Expected",
        )

        result = validator.validate(rule, bundle)
        assert result is not None
        assert "requires 'jsonschema' package" in result.observed_issue

    def test_schema_file_read_generic_exception(self, validator, tmp_path, monkeypatch):
        """Test generic exception when reading schema file."""
        test_file = tmp_path / "data.yaml"
        test_file.write_text("name: test")

        schema_file = tmp_path / "schema.json"
        schema_file.write_text('{"type": "object"}')

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="mixed",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[DocumentFile(relative_path="data.yaml", content="", file_path=str(test_file))],
        )

        # Mock open to fail for schema file
        import builtins

        original_open = builtins.open

        def mock_open(path, *args, **kwargs):
            if "schema.json" in str(path):
                raise PermissionError("Permission denied")
            return original_open(path, *args, **kwargs)

        monkeypatch.setattr(builtins, "open", mock_open)

        rule = ValidationRule(
            rule_type="core:yaml_schema",
            description="Test rule",
            params={"file_path": "data.yaml", "schema_file": "schema.json"},
            failure_message="Failure",
            expected_behavior="Expected",
        )

        result = validator.validate(rule, bundle)
        assert result is not None
        assert "Failed to read schema file" in result.observed_issue

    def test_schema_file_with_json_format(self, validator, tmp_path):
        """Test reading schema file in JSON format."""
        test_file = tmp_path / "data.yaml"
        test_file.write_text("name: test\nage: 30")

        schema_file = tmp_path / "schema.json"
        schema_file.write_text(
            json.dumps(
                {
                    "type": "object",
                    "properties": {"name": {"type": "string"}, "age": {"type": "number"}},
                    "required": ["name", "age"],
                }
            )
        )

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="mixed",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[DocumentFile(relative_path="data.yaml", content="", file_path=str(test_file))],
        )

        rule = ValidationRule(
            rule_type="core:yaml_schema",
            description="Test rule",
            params={"file_path": "data.yaml", "schema_file": "schema.json"},
            failure_message="Failure",
            expected_behavior="Expected",
        )

        result = validator.validate(rule, bundle)
        assert result is None  # Should pass

    def test_schema_file_yaml_fallback(self, validator, tmp_path):
        """Test that schema file falls back to YAML when JSON parsing fails."""
        test_file = tmp_path / "data.yaml"
        test_file.write_text("name: test\nage: 30")

        # Create a schema file in YAML format (not valid JSON)
        schema_file = tmp_path / "schema.yaml"
        schema_file.write_text(
            """
type: object
properties:
  name:
    type: string
  age:
    type: number
required:
  - name
  - age
"""
        )

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="mixed",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[DocumentFile(relative_path="data.yaml", content="", file_path=str(test_file))],
        )

        rule = ValidationRule(
            rule_type="core:yaml_schema",
            description="Test rule",
            params={"file_path": "data.yaml", "schema_file": "schema.yaml"},
            failure_message="Failure",
            expected_behavior="Expected",
        )

        result = validator.validate(rule, bundle)
        assert result is None  # Should pass - YAML fallback works

    def test_validation_with_complex_schema(self, validator, tmp_path):
        """Test validation with a more complex schema for code coverage."""
        test_file = tmp_path / "data.yaml"
        test_file.write_text("name: test\nage: 30\nemail: test@example.com")

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="mixed",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[DocumentFile(relative_path="data.yaml", content="", file_path=str(test_file))],
        )

        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string", "minLength": 1},
                "age": {"type": "number", "minimum": 0},
                "email": {"type": "string", "format": "email"},
            },
            "required": ["name", "age"],
        }

        rule = ValidationRule(
            rule_type="core:yaml_schema",
            description="Test rule",
            params={"file_path": "data.yaml", "schema": schema},
            failure_message="Failure",
            expected_behavior="Expected",
        )

        result = validator.validate(rule, bundle)
        assert result is None  # Should pass

    def test_trigger_schema_error(self, validator, tmp_path):
        """Test that SchemaError is caught when schema is structurally invalid."""
        test_file = tmp_path / "data.yaml"
        test_file.write_text("name: test")

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="mixed",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[DocumentFile(relative_path="data.yaml", content="", file_path=str(test_file))],
        )

        # Schema with invalid type for "type" field (should be string or array, not number)
        schema = {
            "type": 123,  # Invalid - type should be string not number
            "properties": {"name": {"type": "string"}},
        }

        rule = ValidationRule(
            rule_type="core:yaml_schema",
            description="Test rule",
            params={"file_path": "data.yaml", "schema": schema},
            failure_message="Failure",
            expected_behavior="Expected",
        )

        result = validator.validate(rule, bundle)
        # Should catch SchemaError and return failure
        assert result is not None
        assert "Invalid schema" in result.observed_issue

    # ==================== Bundle Mode Tests ====================

    def test_bundle_mode_validates_all_files(self, validator, tmp_path):
        """Test that validator iterates over bundle.files when file_path not provided."""
        # Create test files
        file1 = tmp_path / "file1.yaml"
        file2 = tmp_path / "file2.yaml"
        file3 = tmp_path / "file3.yaml"

        file1.write_text("name: John\nage: 30\n")
        file2.write_text("name: Jane\n")  # Missing 'age'
        file3.write_text("name: Bob\nage: 25\n")

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="mixed",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[
                DocumentFile(
                    relative_path="file1.yaml",
                    content=file1.read_text(),
                    file_path=str(file1),
                ),
                DocumentFile(
                    relative_path="file2.yaml",
                    content=file2.read_text(),
                    file_path=str(file2),
                ),
                DocumentFile(
                    relative_path="file3.yaml",
                    content=file3.read_text(),
                    file_path=str(file3),
                ),
            ],
        )

        schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}, "age": {"type": "number"}},
            "required": ["name", "age"],
        }

        # Validate without file_path - should check all files in bundle
        rule = ValidationRule(
            rule_type="core:yaml_schema",
            description="Check for required fields",
            params={"schema": schema},  # file2 missing 'age'
            failure_message="Invalid YAML structure",
            expected_behavior="All files should have name and age",
        )

        result = validator.validate(rule, bundle)

        # Should fail because file2.yaml doesn't have 'age'
        assert result is not None
        assert "file2.yaml" in result.file_paths
        assert "'age' is a required property" in result.observed_issue

        # file1 and file3 should NOT be in failures
        assert "file1.yaml" not in result.file_paths
        assert "file3.yaml" not in result.file_paths

    def test_bundle_mode_all_files_pass(self, validator, tmp_path):
        """Test that bundle mode returns None when all files pass."""
        file1 = tmp_path / "file1.yaml"
        file2 = tmp_path / "file2.yaml"

        file1.write_text("name: John\nage: 30\n")
        file2.write_text("name: Jane\nage: 25\n")

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="mixed",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[
                DocumentFile(
                    relative_path="file1.yaml",
                    content=file1.read_text(),
                    file_path=str(file1),
                ),
                DocumentFile(
                    relative_path="file2.yaml",
                    content=file2.read_text(),
                    file_path=str(file2),
                ),
            ],
        )

        schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}, "age": {"type": "number"}},
            "required": ["name", "age"],
        }

        rule = ValidationRule(
            rule_type="core:yaml_schema",
            description="Check for required fields",
            params={"schema": schema},
            failure_message="Invalid YAML structure",
            expected_behavior="All files should have name and age",
        )

        result = validator.validate(rule, bundle)
        assert result is None  # All files pass

    def test_bundle_mode_vs_file_path_mode(self, validator, tmp_path):
        """Test that file_path param validates specific file, not bundle files."""
        # Create files
        bundle_file = tmp_path / "bundle_file.yaml"
        specific_file = tmp_path / "specific.yaml"

        bundle_file.write_text("name: John\nage: 30\n")  # Valid
        specific_file.write_text("name: Jane\n")  # Missing 'age'

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="mixed",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[
                DocumentFile(
                    relative_path="bundle_file.yaml",
                    content=bundle_file.read_text(),
                    file_path=str(bundle_file),
                ),
            ],
        )

        schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}, "age": {"type": "number"}},
            "required": ["name", "age"],
        }

        # When file_path provided, should validate that specific file (not bundle files)
        rule = ValidationRule(
            rule_type="core:yaml_schema",
            description="Check specific file",
            params={
                "file_path": "specific.yaml",  # Not in bundle
                "schema": schema,
            },
            failure_message="Invalid YAML structure",
            expected_behavior="File should have name and age",
        )

        result = validator.validate(rule, bundle)

        # Should fail on specific.yaml, not bundle_file.yaml
        assert result is not None
        assert "specific.yaml" in result.file_paths
        assert "'age' is a required property" in result.observed_issue
