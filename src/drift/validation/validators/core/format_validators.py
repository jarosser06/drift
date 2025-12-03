"""Validators for file format validation (JSON Schema, YAML Schema, YAML Frontmatter)."""

import json
from typing import Any, List, Literal, Optional

from drift.config.models import ValidationRule
from drift.core.types import DocumentBundle, DocumentRule
from drift.validation.validators.base import BaseValidator


class JsonSchemaValidator(BaseValidator):
    """Validator for JSON schema validation.

    Validates JSON files against JSON Schema specifications.
    Supports inline schemas via params or external schema files.
    """

    @property
    def computation_type(self) -> Literal["programmatic", "llm"]:
        """Return computation type for this validator."""
        return "programmatic"

    def validate(
        self,
        rule: ValidationRule,
        bundle: DocumentBundle,
        all_bundles: Optional[List[DocumentBundle]] = None,
    ) -> Optional[DocumentRule]:
        """Validate JSON file against schema.

        Schema can be provided via:
        - rule.params['schema']: Inline schema dict
        - rule.params['schema_file']: Path to schema file (relative to project)

        -- rule: ValidationRule with file_path and schema
        -- bundle: Document bundle being validated
        -- all_bundles: Not used for this validator

        Returns DocumentRule if validation fails, None if passes.
        """
        if not rule.file_path:
            raise ValueError("JsonSchemaValidator requires rule.file_path")

        if not rule.params:
            raise ValueError("JsonSchemaValidator requires params with 'schema' or 'schema_file'")

        project_path = bundle.project_path
        file_path = project_path / rule.file_path

        # Check if file exists
        if not file_path.exists() or not file_path.is_file():
            return self._create_failure(
                rule=rule,
                bundle=bundle,
                file_paths=[rule.file_path],
                observed_issue=f"File {rule.file_path} does not exist",
            )

        # Load JSON data
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            return self._create_failure(
                rule=rule,
                bundle=bundle,
                file_paths=[rule.file_path],
                observed_issue=f"Invalid JSON: {e}",
            )
        except Exception as e:
            return self._create_failure(
                rule=rule,
                bundle=bundle,
                file_paths=[rule.file_path],
                observed_issue=f"Failed to read file: {e}",
            )

        # Load schema
        schema = self._load_json_schema(rule, project_path)
        if isinstance(schema, str):  # Error message
            return self._create_failure(
                rule=rule,
                bundle=bundle,
                file_paths=[rule.file_path],
                observed_issue=schema,
            )

        # Validate against schema
        try:
            import jsonschema
        except ImportError:
            return self._create_failure(
                rule=rule,
                bundle=bundle,
                file_paths=[rule.file_path],
                observed_issue=(
                    "JSON Schema validation requires 'jsonschema' package. "
                    "Install with: pip install jsonschema"
                ),
            )

        try:
            jsonschema.validate(instance=data, schema=schema)
            return None  # Validation passed
        except jsonschema.ValidationError as e:
            # Format error message with path and details
            path = "/" + "/".join(str(p) for p in e.absolute_path) if e.absolute_path else "root"
            return self._create_failure(
                rule=rule,
                bundle=bundle,
                file_paths=[rule.file_path],
                observed_issue=f"Schema validation failed at {path}: {e.message}",
            )
        except jsonschema.SchemaError as e:
            return self._create_failure(
                rule=rule,
                bundle=bundle,
                file_paths=[rule.file_path],
                observed_issue=f"Invalid schema: {e.message}",
            )

    def _load_json_schema(self, rule: ValidationRule, project_path: Any) -> Any:
        """Load JSON schema from params or file.

        -- rule: ValidationRule with params
        -- project_path: Project root path

        Returns schema dict or error message string.
        """
        if "schema" in rule.params:
            # Inline schema
            return rule.params["schema"]
        elif "schema_file" in rule.params:
            # External schema file
            schema_file = project_path / rule.params["schema_file"]
            if not schema_file.exists():
                return f"Schema file not found: {rule.params['schema_file']}"

            try:
                with open(schema_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except json.JSONDecodeError as e:
                return f"Invalid JSON in schema file: {e}"
            except Exception as e:
                return f"Failed to read schema file: {e}"
        else:
            return "JsonSchemaValidator requires 'schema' or 'schema_file' in params"

    def _create_failure(
        self,
        rule: ValidationRule,
        bundle: DocumentBundle,
        file_paths: List[str],
        observed_issue: str,
    ) -> DocumentRule:
        """Create a DocumentRule for a validation failure.

        -- rule: The validation rule that failed
        -- bundle: The document bundle being validated
        -- file_paths: List of file paths involved in the failure
        -- observed_issue: Specific issue observed

        Returns DocumentRule representing the failure.
        """
        return DocumentRule(
            bundle_id=bundle.bundle_id,
            bundle_type=bundle.bundle_type,
            file_paths=file_paths,
            observed_issue=observed_issue,
            expected_quality=rule.expected_behavior,
            rule_type="",  # Will be set by analyzer
            context=f"Validation rule: {rule.description}",
        )


class YamlSchemaValidator(BaseValidator):
    """Validator for YAML schema validation.

    Validates YAML files against schema specifications (same format as JSON Schema).
    Supports inline schemas via params or external schema files.
    """

    @property
    def computation_type(self) -> Literal["programmatic", "llm"]:
        """Return computation type for this validator."""
        return "programmatic"

    def validate(
        self,
        rule: ValidationRule,
        bundle: DocumentBundle,
        all_bundles: Optional[List[DocumentBundle]] = None,
    ) -> Optional[DocumentRule]:
        """Validate YAML file against schema.

        Schema can be provided via:
        - rule.params['schema']: Inline schema dict
        - rule.params['schema_file']: Path to schema file (relative to project)

        -- rule: ValidationRule with file_path and schema
        -- bundle: Document bundle being validated
        -- all_bundles: Not used for this validator

        Returns DocumentRule if validation fails, None if passes.
        """
        if not rule.file_path:
            raise ValueError("YamlSchemaValidator requires rule.file_path")

        if not rule.params:
            raise ValueError("YamlSchemaValidator requires params with 'schema' or 'schema_file'")

        project_path = bundle.project_path
        file_path = project_path / rule.file_path

        # Check if file exists
        if not file_path.exists() or not file_path.is_file():
            return self._create_failure(
                rule=rule,
                bundle=bundle,
                file_paths=[rule.file_path],
                observed_issue=f"File {rule.file_path} does not exist",
            )

        # Load YAML data
        try:
            import yaml
        except ImportError:
            return self._create_failure(
                rule=rule,
                bundle=bundle,
                file_paths=[rule.file_path],
                observed_issue=(
                    "YAML validation requires 'pyyaml' package. " "Install with: pip install pyyaml"
                ),
            )

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            return self._create_failure(
                rule=rule,
                bundle=bundle,
                file_paths=[rule.file_path],
                observed_issue=f"Invalid YAML: {e}",
            )
        except Exception as e:
            return self._create_failure(
                rule=rule,
                bundle=bundle,
                file_paths=[rule.file_path],
                observed_issue=f"Failed to read file: {e}",
            )

        # Load schema
        schema = self._load_yaml_schema(rule, project_path)
        if isinstance(schema, str):  # Error message
            return self._create_failure(
                rule=rule,
                bundle=bundle,
                file_paths=[rule.file_path],
                observed_issue=schema,
            )

        # Validate against schema using jsonschema
        try:
            import jsonschema
        except ImportError:
            return self._create_failure(
                rule=rule,
                bundle=bundle,
                file_paths=[rule.file_path],
                observed_issue=(
                    "YAML Schema validation requires 'jsonschema' package. "
                    "Install with: pip install jsonschema"
                ),
            )

        try:
            jsonschema.validate(instance=data, schema=schema)
            return None  # Validation passed
        except jsonschema.ValidationError as e:
            # Format error message with path and details
            path = "/" + "/".join(str(p) for p in e.absolute_path) if e.absolute_path else "root"
            return self._create_failure(
                rule=rule,
                bundle=bundle,
                file_paths=[rule.file_path],
                observed_issue=f"Schema validation failed at {path}: {e.message}",
            )
        except jsonschema.SchemaError as e:
            return self._create_failure(
                rule=rule,
                bundle=bundle,
                file_paths=[rule.file_path],
                observed_issue=f"Invalid schema: {e.message}",
            )

    def _load_yaml_schema(self, rule: ValidationRule, project_path: Any) -> Any:
        """Load YAML schema from params or file.

        -- rule: ValidationRule with params
        -- project_path: Project root path

        Returns schema dict or error message string.
        """
        if "schema" in rule.params:
            # Inline schema
            return rule.params["schema"]
        elif "schema_file" in rule.params:
            # External schema file (can be YAML or JSON)
            schema_file = project_path / rule.params["schema_file"]
            if not schema_file.exists():
                return f"Schema file not found: {rule.params['schema_file']}"

            try:
                with open(schema_file, "r", encoding="utf-8") as f:
                    # Try JSON first, then YAML
                    content = f.read()
                    try:
                        return json.loads(content)
                    except json.JSONDecodeError:
                        import yaml

                        return yaml.safe_load(content)
            except Exception as e:
                return f"Failed to read schema file: {e}"
        else:
            return "YamlSchemaValidator requires 'schema' or 'schema_file' in params"

    def _create_failure(
        self,
        rule: ValidationRule,
        bundle: DocumentBundle,
        file_paths: List[str],
        observed_issue: str,
    ) -> DocumentRule:
        """Create a DocumentRule for a validation failure.

        -- rule: The validation rule that failed
        -- bundle: The document bundle being validated
        -- file_paths: List of file paths involved in the failure
        -- observed_issue: Specific issue observed

        Returns DocumentRule representing the failure.
        """
        return DocumentRule(
            bundle_id=bundle.bundle_id,
            bundle_type=bundle.bundle_type,
            file_paths=file_paths,
            observed_issue=observed_issue,
            expected_quality=rule.expected_behavior,
            rule_type="",  # Will be set by analyzer
            context=f"Validation rule: {rule.description}",
        )


class YamlFrontmatterValidator(BaseValidator):
    """Validator for YAML frontmatter in Markdown files.

    Validates that Markdown files have valid YAML frontmatter
    with required fields.
    """

    @property
    def computation_type(self) -> Literal["programmatic", "llm"]:
        """Return computation type for this validator."""
        return "programmatic"

    def validate(
        self,
        rule: ValidationRule,
        bundle: DocumentBundle,
        all_bundles: Optional[List[DocumentBundle]] = None,
    ) -> Optional[DocumentRule]:
        """Validate YAML frontmatter in Markdown files.

        Checks for:
        - Valid YAML frontmatter delimited by ---
        - Required fields specified in rule.params['required_fields']

        -- rule: ValidationRule with params (required_fields, schema)
        -- bundle: Document bundle being validated
        -- all_bundles: Not used for this validator

        Returns DocumentRule if validation fails, None if passes.
        """
        # Support both single-file mode (via rule.file_path) and bundle mode
        if rule.file_path:
            # Legacy single-file mode
            project_path = bundle.project_path
            file_path = project_path / rule.file_path

            # Check if file exists
            if not file_path.exists() or not file_path.is_file():
                return self._create_failure(
                    rule=rule,
                    bundle=bundle,
                    file_paths=[rule.file_path],
                    observed_issue=f"File {rule.file_path} does not exist",
                )

            # Read file content
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
            except Exception as e:
                return self._create_failure(
                    rule=rule,
                    bundle=bundle,
                    file_paths=[rule.file_path],
                    observed_issue=f"Failed to read file: {e}",
                )

            # Validate single file
            return self._validate_file_content(rule, bundle, rule.file_path, content)
        else:
            # Bundle mode - validate all files in bundle
            failed_files = []

            for file in bundle.files:
                # Validate each file's frontmatter
                result = self._validate_file_content(rule, bundle, file.relative_path, file.content)
                if result:
                    # Collect failed file info
                    failed_files.append((file.relative_path, result.observed_issue))

            if failed_files:
                # Build detailed message
                messages = []
                for rel_path, issue in failed_files:
                    messages.append(f"{rel_path}: {issue}")

                return DocumentRule(
                    bundle_id=bundle.bundle_id,
                    bundle_type=bundle.bundle_type,
                    file_paths=[f[0] for f in failed_files],
                    observed_issue="; ".join(messages),
                    expected_quality=rule.expected_behavior,
                    rule_type="",
                    context=f"Validation rule: {rule.description}",
                )

            return None  # All files passed

    def _validate_file_content(
        self,
        rule: ValidationRule,
        bundle: DocumentBundle,
        file_path: str,
        content: str,
    ) -> Optional[DocumentRule]:
        """Validate frontmatter in a single file's content.

        -- rule: ValidationRule with params
        -- bundle: Document bundle for context
        -- file_path: Relative path of file being validated
        -- content: File content to validate

        Returns DocumentRule if validation fails, None if passes.
        """
        # Extract frontmatter
        frontmatter_data = self._extract_frontmatter(content)
        if isinstance(frontmatter_data, str):  # Error message
            return self._create_failure(
                rule=rule,
                bundle=bundle,
                file_paths=[file_path],
                observed_issue=frontmatter_data,
            )

        # Check required fields
        if rule.params and "required_fields" in rule.params:
            required_fields = rule.params["required_fields"]
            missing_fields = [field for field in required_fields if field not in frontmatter_data]

            if missing_fields:
                return self._create_failure(
                    rule=rule,
                    bundle=bundle,
                    file_paths=[file_path],
                    observed_issue=(
                        f"Missing required frontmatter fields: {', '.join(missing_fields)}"
                    ),
                )

        # Optionally validate schema if provided
        if rule.params and "schema" in rule.params:
            try:
                import jsonschema

                schema = rule.params["schema"]
                jsonschema.validate(instance=frontmatter_data, schema=schema)
            except ImportError:
                return self._create_failure(
                    rule=rule,
                    bundle=bundle,
                    file_paths=[file_path],
                    observed_issue=(
                        "Frontmatter schema validation requires 'jsonschema' package. "
                        "Install with: pip install jsonschema"
                    ),
                )
            except jsonschema.ValidationError as e:
                path = (
                    "/" + "/".join(str(p) for p in e.absolute_path) if e.absolute_path else "root"
                )
                return self._create_failure(
                    rule=rule,
                    bundle=bundle,
                    file_paths=[file_path],
                    observed_issue=f"Frontmatter schema validation failed at {path}: {e.message}",
                )
            except jsonschema.SchemaError as e:
                return self._create_failure(
                    rule=rule,
                    bundle=bundle,
                    file_paths=[file_path],
                    observed_issue=f"Invalid schema: {e.message}",
                )

        return None  # Validation passed

    def _extract_frontmatter(self, content: str) -> Any:
        """Extract and parse YAML frontmatter from content.

        -- content: File content

        Returns parsed frontmatter dict or error message string.
        """
        # Check for frontmatter delimiters
        if not content.startswith("---"):
            return "No YAML frontmatter found (must start with ---)"

        # Find closing delimiter
        lines = content.split("\n")
        closing_idx = None
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                closing_idx = i
                break

        if closing_idx is None:
            return "YAML frontmatter not properly closed (missing closing ---)"

        # Extract frontmatter content
        frontmatter_content = "\n".join(lines[1:closing_idx])

        # Parse YAML
        try:
            import yaml
        except ImportError:
            return (
                "YAML frontmatter validation requires 'pyyaml' package. "
                "Install with: pip install pyyaml"
            )

        try:
            data = yaml.safe_load(frontmatter_content)
            if data is None:
                return "YAML frontmatter is empty"
            return data
        except yaml.YAMLError as e:
            return f"Invalid YAML in frontmatter: {e}"

    def _create_failure(
        self,
        rule: ValidationRule,
        bundle: DocumentBundle,
        file_paths: List[str],
        observed_issue: str,
    ) -> DocumentRule:
        """Create a DocumentRule for a validation failure.

        -- rule: The validation rule that failed
        -- bundle: The document bundle being validated
        -- file_paths: List of file paths involved in the failure
        -- observed_issue: Specific issue observed

        Returns DocumentRule representing the failure.
        """
        return DocumentRule(
            bundle_id=bundle.bundle_id,
            bundle_type=bundle.bundle_type,
            file_paths=file_paths,
            observed_issue=observed_issue,
            expected_quality=rule.expected_behavior,
            rule_type="",  # Will be set by analyzer
            context=f"Validation rule: {rule.description}",
        )
