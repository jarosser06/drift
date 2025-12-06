# Validators Reference

This document provides comprehensive documentation for all validator types available in Drift, including the `failure_details` feature that enables detailed, actionable violation messages.

## Table of Contents

- [Default Failure Messages](#default-failure-messages)
- [Custom Validator Plugins](#custom-validator-plugins)
- [Failure Details Feature](#failure-details-feature)
- [File Validators](#file-validators)
- [Regex Validators](#regex-validators)
- [List Validators](#list-validators)
- [Markdown Validators](#markdown-validators)
- [Format Validators](#format-validators)
- [Dependency Validators](#dependency-validators)
- [Claude Code Validators](#claude-code-validators)
- [LLM-Based Validators](#llm-based-validators)

---

## Default Failure Messages

Validators provide sensible default failure messages, eliminating the need to specify `failure_message` and `expected_behavior` in every validation rule.

### Overview

Every validator includes built-in default messages that describe what failed and what's expected. You can still override these with custom messages when needed, and custom messages support template variable substitution using `{placeholder}` syntax.

### How It Works

1. **No custom message**: Validator uses its default message
2. **Custom message with templates**: Variables like `{file_path}` are replaced with actual values
3. **Custom message without templates**: Validator appends relevant details automatically

### Benefits

- **Less configuration**: Validators work out-of-the-box without requiring message configuration
- **Consistent messaging**: Built-in messages follow a standard format across all validators
- **Flexible customization**: Override defaults when you need custom wording or localization
- **Always show details**: Even custom messages without placeholders get relevant details appended

### Example: Using Defaults

```yaml
# Minimal configuration - uses validator defaults
phases:
  - name: Check README
    type: core:file_exists
    file_path: README.md
    # No failure_message needed!
    # Default: "File {file_path} does not exist"
```

### Example: Custom Message with Templates

```yaml
# Custom message with template variables
phases:
  - name: Check README
    type: core:file_exists
    file_path: README.md
    failure_message: "⚠️ Missing required file: {file_path}"
    expected_behavior: "All projects must have a README"
```

### Example: Custom Message without Templates

```yaml
# Custom message without templates still gets details appended
phases:
  - name: Check Dependencies
    type: core:circular_dependencies
    params:
      resource_dirs: [".claude/skills"]
    failure_message: "Circular dependency found"
    # Result: "Circular dependency found: skill-a → skill-b → skill-a"
```

### Default Messages by Validator

All validators provide contextual default messages. Here are some examples:

**File Validators:**
- `core:file_exists` → "File {file_path} does not exist"
- `core:file_size` → "File size constraint violated"
- `core:token_count` → "File token count constraint violated"

**Dependency Validators:**
- `core:circular_dependencies` → "Circular dependency detected: {circular_path}"
- `core:max_dependency_depth` → "Dependency depth {actual_depth} exceeds maximum {max_depth}"
- `core:dependency_duplicate` → "Duplicate dependency found: {dependency}"

**Format Validators:**
- `core:json_schema` → "JSON schema validation failed"
- `core:yaml_schema` → "YAML schema validation failed"
- `core:yaml_frontmatter` → "YAML frontmatter validation failed"

**Regex & List Validators:**
- `core:regex_match` → "Pattern match validation failed"
- `core:list_match` → "List match validation failed"
- `core:markdown_link` → "Broken link found: {link}"

See individual validator documentation below for complete details and available template variables.

---

## Custom Validator Plugins

Drift supports loading custom validators from third-party Python packages, enabling extensible validation beyond the built-in `core:` validators.

### Overview

The plugin system allows you to:
- Create custom validators for domain-specific checks (security scans, license compliance, etc.)
- Package and distribute validators as Python packages
- Load validators dynamically without modifying Drift's codebase
- Use namespaced validation types to prevent conflicts

### Creating a Custom Validator

1. **Create a validator class** that inherits from `BaseValidator`:

```python
# my_package/validators.py
from typing import List, Literal, Optional
from drift.validation.validators import BaseValidator
from drift.config.models import ValidationRule
from drift.core.types import DocumentBundle, DocumentRule


class SecurityScanValidator(BaseValidator):
    """Custom validator for security vulnerability scanning."""

    @property
    def validation_type(self) -> str:
        """Return the namespaced validation type."""
        return "security:vulnerability_scan"

    @property
    def computation_type(self) -> Literal["programmatic", "llm"]:
        """This is a programmatic validator."""
        return "programmatic"

    @property
    def default_failure_message(self) -> str:
        """Default message when vulnerabilities found."""
        return "Security vulnerabilities detected: {vulnerability_count} issues"

    @property
    def default_expected_behavior(self) -> str:
        """Expected behavior description."""
        return "No security vulnerabilities should exist"

    def validate(
        self,
        rule: ValidationRule,
        bundle: DocumentBundle,
        all_bundles: Optional[List[DocumentBundle]] = None,
    ) -> Optional[DocumentRule]:
        """Run security scan on files in bundle."""
        # Your validation logic here
        vulnerabilities = self._scan_for_vulnerabilities(bundle)

        if vulnerabilities:
            failure_details = {
                "vulnerability_count": len(vulnerabilities),
                "vulnerabilities": vulnerabilities
            }

            return DocumentRule(
                bundle_id=bundle.bundle_id,
                bundle_type=bundle.bundle_type,
                file_paths=[v["file"] for v in vulnerabilities],
                observed_issue=self._get_failure_message(rule, failure_details),
                expected_quality=self._get_expected_behavior(rule),
                rule_type="",
                context=f"Validation rule: {rule.description}",
                failure_details=failure_details,
            )

        return None  # Validation passed
```

2. **Package your validator** as an installable Python package:

```toml
# pyproject.toml
[project]
name = "my-drift-validators"
version = "1.0.0"
dependencies = ["ai-drift>=0.4.0"]
```

3. **Install the package**:

```bash
pip install my-drift-validators
```

4. **Use in `.drift.yaml`** with the `provider` field:

```yaml
phases:
  - name: Security Scan
    type: security:vulnerability_scan
    provider: "my_package.validators:SecurityScanValidator"
    params:
      scan_level: "strict"
    # Optional: override default messages
    failure_message: "🔒 Found {vulnerability_count} security issues"
    expected_behavior: "Code must pass security scan"
```

### Namespace Requirements

- **Format**: `namespace:type` (e.g., `security:scan`, `compliance:license`)
- **Pattern**: Lowercase letters, numbers, underscores only (`^[a-z_][a-z0-9_]*:[a-z_][a-z0-9_]*$`)
- **Reserved namespace**: `core:` is reserved for built-in validators
- **Custom namespaces**: Use your company/project name (e.g., `acme:security_scan`)

### Provider Format

The `provider` field specifies how to load your validator:

**Format**: `module.path:ClassName`

**Examples**:
- `my_package.validators:SecurityValidator`
- `company.drift_plugins:LicenseChecker`
- `my_app.custom_validators:CustomValidator`

### Validation Rules

**Core validators** (`core:*`) must not have a `provider` field, while **custom validators** (any other namespace) require a `provider` field. Invalid combinations will raise a validation error at configuration time.

```yaml
# Core validator - no provider needed
phases:
  - type: core:file_exists
    file_path: README.md

# Custom validator - provider required
phases:
  - type: security:scan
    provider: "my_pkg.validators:SecurityValidator"
```

### Best Practices

1. **Namespace uniquely**: Use your organization or package name as the namespace
2. **Provide defaults**: Always implement `default_failure_message` and `default_expected_behavior`
3. **Use templates**: Include placeholder variables in default messages for flexibility
4. **Return details**: Populate `failure_details` with actionable information
5. **Handle errors**: Raise clear exceptions for invalid configuration
6. **Document thoroughly**: Provide docstrings explaining parameters and behavior

### Example: Full Custom Validator

```python
from pathlib import Path
from typing import List, Literal, Optional
from drift.validation.validators import BaseValidator
from drift.config.models import ValidationRule
from drift.core.types import DocumentBundle, DocumentRule


class LicenseCheckValidator(BaseValidator):
    """Validates that all code files have proper license headers."""

    @property
    def validation_type(self) -> str:
        return "compliance:license_check"

    @property
    def computation_type(self) -> Literal["programmatic", "llm"]:
        return "programmatic"

    @property
    def default_failure_message(self) -> str:
        return "Missing license headers in {file_count} files"

    @property
    def default_expected_behavior(self) -> str:
        return "All source files should have license headers"

    def validate(
        self,
        rule: ValidationRule,
        bundle: DocumentBundle,
        all_bundles: Optional[List[DocumentBundle]] = None,
    ) -> Optional[DocumentRule]:
        required_header = rule.params.get("header", "Copyright")
        file_extensions = rule.params.get("extensions", [".py", ".js"])

        missing_headers = []
        for file in bundle.files:
            if any(file.relative_path.endswith(ext) for ext in file_extensions):
                content = Path(file.file_path).read_text()
                if required_header not in content[:500]:  # Check first 500 chars
                    missing_headers.append(file.relative_path)

        if missing_headers:
            failure_details = {
                "file_count": len(missing_headers),
                "files": missing_headers,
                "required_header": required_header
            }

            return DocumentRule(
                bundle_id=bundle.bundle_id,
                bundle_type=bundle.bundle_type,
                file_paths=missing_headers,
                observed_issue=self._get_failure_message(rule, failure_details),
                expected_quality=self._get_expected_behavior(rule),
                rule_type="",
                context=f"Validation rule: {rule.description}",
                failure_details=failure_details,
            )

        return None
```

**Usage**:
```yaml
phases:
  - name: License Check
    type: compliance:license_check
    provider: "my_company.validators:LicenseCheckValidator"
    params:
      header: "Copyright (C) 2025"
      extensions: [".py", ".js", ".ts"]
```

### Caching and Performance

Drift automatically caches loaded validator classes for performance:
- Validators are loaded once per validation run
- Class-level caching prevents redundant imports
- Multiple rules can share the same validator instance

No special configuration needed - caching is automatic.

---

## Failure Details Feature

The `failure_details` feature allows validators to return structured data about validation failures, which can then be interpolated into failure messages using template placeholders.

### How It Works

When a validator detects a failure, it can populate a `failure_details` dictionary with specific information about what went wrong. This data is then used to format the `failure_message` template defined in your rule.

### Template Placeholders

Use `{placeholder}` syntax in your `failure_message` to reference values from `failure_details`:

```yaml
failure_message: "Circular dependency detected: {circular_path}"
```

When a circular dependency is found, the validator populates `failure_details`:

```python
failure_details = {
    "circular_path": "agent_a → agent_b → agent_a"
}
```

The final message becomes:
```
Circular dependency detected: agent_a → agent_b → agent_a
```

### Benefits

1. **Actionable Messages**: Users see exactly what's wrong with specific details
2. **Reusable Rules**: Same rule can handle different failure scenarios
3. **Structured Data**: Failure details can be consumed programmatically (JSON output)
4. **Backward Compatible**: If `failure_details` is not populated, the message is used as-is

### Example Usage

```yaml
phases:
  - name: check_depth
    type: max_dependency_depth
    params:
      max_depth: 3
      resource_dirs:
        - .claude/agents
        - .claude/skills
    failure_message: "Dependency depth {actual_depth} exceeds maximum {max_depth}"
    expected_behavior: "Keep dependency chains under 3 levels"
```

Output when validation fails:
```
Dependency depth 5 exceeds maximum 3. Chain: agent_a → skill_b → skill_c → skill_d → skill_e
```

---

## File Validators

### file_exists

Check if specified file(s) exist in the project.

**Computation Type:** Programmatic (no LLM required)

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `file_path` | string | Yes | - | Path to file (supports glob patterns) |

**Supports:** Single files and glob patterns (`*.md`, `**/*.py`)

**Example:**

```yaml
phases:
  - name: check_readme
    type: file_exists
    file_path: README.md
    failure_message: "README.md is missing"
    expected_behavior: "Project must have README.md"
```

**Example with glob pattern:**

```yaml
phases:
  - name: check_tests
    type: file_exists
    file_path: "tests/**/*.py"
    failure_message: "No test files found"
    expected_behavior: "Project must have test files"
```

**Failure Messages:**

- Without file_path: `FileExistsValidator requires rule.file_path`
- File not found: `<failure_message from rule>`
- No glob matches: `<failure_message from rule>`

**Failure Details:** None (simple existence check)

**Example Output:**

When a specific file is missing:
```
README.md is missing
```

When using glob patterns and no files match:
```
No test files found
```

---

### file_size

Validate file size constraints (line count or byte size).

**Computation Type:** Programmatic (no LLM required)

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `file_path` | string | Yes | - | Path to file to check |
| `max_count` | integer | No | - | Maximum number of lines |
| `min_count` | integer | No | - | Minimum number of lines |
| `max_size` | integer | No | - | Maximum file size in bytes |
| `min_size` | integer | No | - | Minimum file size in bytes |

**Example (line count):**

```yaml
phases:
  - name: check_claude_md_size
    type: file_size
    file_path: CLAUDE.md
    max_count: 200
    failure_message: "CLAUDE.md exceeds 200 lines"
    expected_behavior: "CLAUDE.md should be concise (under 200 lines)"
```

**Example (byte size):**

```yaml
phases:
  - name: check_config_size
    type: file_size
    file_path: .drift.yaml
    max_size: 10240
    failure_message: "Config file exceeds 10KB"
    expected_behavior: "Config should be under 10KB"
```

**Failure Messages:**

- File not found: `File {file_path} does not exist`
- Line count exceeded: `File has {actual} lines (exceeds max {max_count})`
- Line count too low: `File has {actual} lines (below min {min_count})`
- Byte size exceeded: `File is {actual} bytes (exceeds max {max_size})`
- Byte size too low: `File is {actual} bytes (below min {min_size})`

**Failure Details:** None

**Example Output:**

When file exceeds maximum line count:
```
File has 250 lines (exceeds max 200)
```

When file is below minimum byte size:
```
File is 512 bytes (below min 1024)
```

---

## Regex Validators

### regex_match

Check if file content matches a regex pattern.

**Computation Type:** Programmatic (no LLM required)

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `pattern` | string | Yes | - | Regular expression pattern |
| `file_path` | string | No | - | Specific file to check (if omitted, checks all bundle files) |
| `flags` | integer | No | `0` | Regex flags (e.g., `8` for `re.MULTILINE`) |

**Common Regex Flags:**

- `8` = `re.MULTILINE` - `^` and `$` match line boundaries
- `2` = `re.IGNORECASE` - Case-insensitive matching
- `16` = `re.DOTALL` - `.` matches newlines

**Example:**

```yaml
phases:
  - name: check_tools_format
    type: regex_match
    pattern: '^tools:\s+[A-Z][\w_]+(?:,\s*[A-Z][\w_]+)*\s*$'
    flags: 8
    failure_message: "Agent tools field uses wrong format"
    expected_behavior: "Tools should be comma-separated on single line"
```

**Example (bundle mode):**

```yaml
phases:
  - name: check_frontmatter_name
    type: regex_match
    pattern: '^name:\s+\w+$'
    flags: 8
    failure_message: "Frontmatter missing name field"
    expected_behavior: "All files must have name in frontmatter"
```

**Failure Messages:**

- Pattern not provided: `RegexMatchValidator requires rule.pattern`
- Invalid pattern: `Invalid regex pattern: {error}`
- File not found: `File not found: {file_path}`
- Pattern not matched: `<failure_message from rule>`

**Failure Details:** None

**Example Output:**

When pattern is not found in a specific file:
```
Agent tools field uses wrong format
```

When validating multiple files in a bundle (context provides details):
```
Agent tools field uses wrong format
```

---

## List Validators

### list_match

Check if list items match expected values.

**Computation Type:** Programmatic (no LLM required)

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `items` | param_spec | Yes | - | List to check (supports `string_list`, `resource_list`) |
| `target` | param_spec | Yes | - | List to compare against (supports `string_list`, `resource_list`, `file_content`) |
| `match_mode` | string | No | `all_in` | Match mode: `all_in`, `none_in`, `exact` |

**Match Modes:**

- `all_in`: All items must be in target
- `none_in`: No items should be in target
- `exact`: Lists must match exactly (order-independent)

**Example:**

```yaml
phases:
  - name: check_dependencies
    type: list_match
    params:
      items:
        type: resource_list
        value: skills
      target:
        type: file_content
        value: CLAUDE.md
      match_mode: all_in
    failure_message: "Skills not documented in CLAUDE.md"
    expected_behavior: "All skills should be mentioned in CLAUDE.md"
```

**Failure Messages:**

- Missing params: `ListMatchValidator requires 'items' and 'target' params`
- Items not found: `Items not found in target: {missing}`
- Items found (none_in): `Items found in target but should not be: {found}`
- Exact mismatch: `Lists do not match exactly. Items: {items}, Target: {target}`

**Failure Details:** None

**Example Output:**

When items are not found in target (all_in mode):
```
Skills not documented in CLAUDE.md
```

When items are found but shouldn't be (none_in mode):
```
Skills not documented in CLAUDE.md
```

When lists don't match exactly (exact mode):
```
Skills not documented in CLAUDE.md
```

---

### list_regex_match

Check if list items match regex patterns extracted from files.

**Computation Type:** Programmatic (no LLM required)

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `items` | param_spec | Yes | - | List to check (supports `string_list`, `resource_list`) |
| `file_path` | param_spec | Yes | - | File path to search in |
| `pattern` | string | Yes | - | Regex pattern to extract matches from file |
| `match_mode` | string | No | `all_in` | Match mode: `all_in`, `none_in` |

**Example:**

```yaml
phases:
  - name: check_skills_documented
    type: list_regex_match
    params:
      items:
        type: resource_list
        value: skills
      file_path:
        type: string
        value: CLAUDE.md
      pattern: '\b([\w-]+)\s+skill'
      match_mode: all_in
    failure_message: "Skills not mentioned in CLAUDE.md"
    expected_behavior: "All skills should be referenced in documentation"
```

**Failure Messages:**

- Missing params: `ListRegexMatchValidator requires 'items', 'file_path', and 'pattern' params`
- Items not found: `Items not found in file: {missing}. Found: {found}`
- Items found (none_in): `Items found in file but should not be: {found}`

**Failure Details:** None

**Example Output:**

When items are not found in file:
```
Skills not mentioned in CLAUDE.md
```

When items are found but shouldn't be (none_in mode):
```
Skills not mentioned in CLAUDE.md
```

---

## Markdown Validators

### markdown_link

Validate markdown links (local files, external URLs, resource references).

**Computation Type:** Programmatic (no LLM required)

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `check_local_files` | boolean | No | `true` | Validate local file references |
| `check_external_urls` | boolean | No | `true` | Validate external URLs (HTTP/HTTPS) |
| `check_resource_refs` | boolean | No | `false` | Validate resource references (agents, skills, commands) |
| `resource_patterns` | list[string] | No | `[]` | Regex patterns to extract resource names |
| `skip_example_domains` | boolean | No | `true` | Skip example.com and similar placeholder domains |
| `skip_code_blocks` | boolean | No | `true` | Skip links in code blocks |
| `skip_placeholder_paths` | boolean | No | `true` | Skip placeholder paths like `/path/to/file` |
| `custom_skip_patterns` | list[string] | No | `[]` | Custom regex patterns to skip |

**Example:**

```yaml
phases:
  - name: check_links
    type: markdown_link
    params:
      check_local_files: true
      check_external_urls: false
      skip_code_blocks: true
    failure_message: "Found broken links"
    expected_behavior: "All file references should be valid"
```

**Example (with resource checking):**

```yaml
phases:
  - name: check_skill_references
    type: markdown_link
    params:
      check_local_files: true
      check_resource_refs: true
      resource_patterns:
        - '\[([^\]]+)\]\(#skill-(\w+)\)'
    failure_message: "Found broken skill references"
    expected_behavior: "All skill references should be valid"
```

**Failure Messages:**

- Broken local file: `{file_path}: [{link}] - local file not found`
- Broken external URL: `{file_path}: [{link}] - external URL unreachable`
- Broken resource: `{file_path}: [{resource_name}] - {resource_type} reference not found`

**Failure Details:** None

**Example Output:**

When local file references are broken:
```
Found broken links: README.md: [../docs/guide.md] - local file not found; CLAUDE.md: [.claude/agents/missing.md] - local file not found
```

When external URLs are unreachable:
```
Found broken links: README.md: [https://example-broken-url.com] - external URL unreachable
```

When resource references are broken:
```
Found broken links: agent.md: [testing] - skill reference not found
```

---

## Format Validators

### json_schema

Validate JSON files against JSON Schema specifications.

**Computation Type:** Programmatic (no LLM required)

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `file_path` | string | Yes | - | Path to JSON file |
| `schema` | object | No | - | Inline JSON schema |
| `schema_file` | string | No | - | Path to schema file (relative to project) |

**Note:** Must provide either `schema` or `schema_file`.

**Example (inline schema):**

```yaml
phases:
  - name: check_package_json
    type: json_schema
    file_path: package.json
    params:
      schema:
        type: object
        properties:
          name:
            type: string
          version:
            type: string
            pattern: '^\d+\.\d+\.\d+$'
        required:
          - name
          - version
    failure_message: "Invalid package.json structure"
    expected_behavior: "package.json must have name and version"
```

**Example (external schema):**

```yaml
phases:
  - name: check_config
    type: json_schema
    file_path: config.json
    params:
      schema_file: schemas/config-schema.json
    failure_message: "Invalid configuration"
    expected_behavior: "Config must match schema"
```

**Failure Messages:**

- File not found: `File {file_path} does not exist`
- Invalid JSON: `Invalid JSON: {error}`
- Schema not provided: `JsonSchemaValidator requires 'schema' or 'schema_file' in params`
- Schema file not found: `Schema file not found: {schema_file}`
- Validation failed: `Schema validation failed at {path}: {message}`
- Invalid schema: `Invalid schema: {message}`

**Failure Details:** None

**Example Output:**

When JSON schema validation fails:
```
Schema validation failed at /version: '1.0.0' does not match '^\\d+\\.\\d+\\.\\d+$'
```

When required fields are missing:
```
Schema validation failed at root: 'name' is a required property
```

When JSON is invalid:
```
Invalid JSON: Expecting ',' delimiter: line 5 column 3 (char 89)
```

---

### yaml_schema

Validate YAML files against schema specifications (JSON Schema format).

**Computation Type:** Programmatic (no LLM required)

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `file_path` | string | Yes | - | Path to YAML file |
| `schema` | object | No | - | Inline schema (JSON Schema format) |
| `schema_file` | string | No | - | Path to schema file (YAML or JSON) |

**Note:** Must provide either `schema` or `schema_file`.

**Example:**

```yaml
phases:
  - name: check_drift_config
    type: yaml_schema
    file_path: .drift.yaml
    params:
      schema:
        type: object
        properties:
          providers:
            type: object
          models:
            type: object
        required:
          - providers
          - models
    failure_message: "Invalid .drift.yaml structure"
    expected_behavior: "Config must have providers and models"
```

**Failure Messages:**

- File not found: `File {file_path} does not exist`
- Invalid YAML: `Invalid YAML: {error}`
- Schema validation failed: `Schema validation failed at {path}: {message}`

**Failure Details:** None

**Example Output:**

When YAML schema validation fails:
```
Schema validation failed at /model: 'gpt-4' is not one of ['sonnet', 'opus', 'haiku']
```

When YAML is invalid:
```
Invalid YAML: mapping values are not allowed here
```

When file doesn't exist:
```
File .drift.yaml does not exist
```

---

### yaml_frontmatter

Validate YAML frontmatter in Markdown files.

**Computation Type:** Programmatic (no LLM required)

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `file_path` | string | No | - | Specific file (if omitted, validates all bundle files) |
| `required_fields` | list[string] | No | `[]` | List of required frontmatter fields |
| `schema` | object | No | - | JSON Schema for frontmatter validation |

**Example (required fields):**

```yaml
phases:
  - name: check_frontmatter
    type: yaml_frontmatter
    params:
      required_fields:
        - name
        - description
    failure_message: "Missing required frontmatter fields"
    expected_behavior: "All agents must have name and description"
```

**Example (with schema):**

```yaml
phases:
  - name: check_agent_frontmatter
    type: yaml_frontmatter
    params:
      required_fields:
        - name
        - description
        - model
      schema:
        type: object
        properties:
          name:
            type: string
            pattern: '^[a-z][a-z0-9-]*$'
          model:
            type: string
            enum: ['sonnet', 'opus', 'haiku']
        required:
          - name
          - description
    failure_message: "Invalid frontmatter"
    expected_behavior: "Frontmatter must match schema"
```

**Failure Messages:**

- File not found: `File {file_path} does not exist`
- No frontmatter: `No YAML frontmatter found (must start with ---)`
- Not closed: `YAML frontmatter not properly closed (missing closing ---)`
- Empty: `YAML frontmatter is empty`
- Invalid YAML: `Invalid YAML in frontmatter: {error}`
- Missing fields: `Missing required frontmatter fields: {fields}`
- Schema validation failed: `Frontmatter schema validation failed at {path}: {message}`

**Failure Details:** None

**Example Output:**

When required frontmatter fields are missing:
```
Missing required frontmatter fields: description, model
```

When frontmatter is missing:
```
No YAML frontmatter found (must start with ---)
```

When frontmatter schema validation fails:
```
Frontmatter schema validation failed at /name: 'My-Agent' does not match '^[a-z][a-z0-9-]*$'
```

When validating multiple files:
```
.claude/agents/developer.md: Missing required frontmatter fields: description; .claude/agents/qa.md: No YAML frontmatter found (must start with ---)
```

---

## Dependency Validators

These validators analyze dependency graphs to detect structural issues. They work with any `DependencyGraph` implementation and are extensible for different file-based dependency systems.

### dependency_duplicate

Detect redundant transitive dependencies in dependency chains.

**Computation Type:** Programmatic (no LLM required)

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `resource_dirs` | list[string] | Yes | - | Directories containing resources to analyze |

**Example:**

```yaml
phases:
  - name: check_duplicates
    type: dependency_duplicate
    params:
      resource_dirs:
        - .claude/agents
        - .claude/skills
    failure_message: "Found redundant dependency '{duplicate_resource}'"
    expected_behavior: "Only declare direct dependencies"
```

**Failure Messages:**

- Single duplicate: `{failure_message}: '{duplicate_resource}' is redundant (already declared by '{declared_by}')`
- Multiple duplicates: `{failure_message}: {duplicate_count} duplicates detected ({details})`

**Failure Details:**

| Field | Type | Description |
|-------|------|-------------|
| `duplicate_resource` | string | Name of the duplicate resource |
| `declared_by` | string | Resource that already declares this dependency |
| `duplicate_count` | integer | Total number of duplicates found |
| `all_duplicates` | list[object] | Detailed info for each duplicate |

**Example Output:**

```
Found redundant dependency 'skill_b': 'skill_b' is redundant (already declared by 'skill_a')
```

---

### circular_dependencies

Detect circular dependencies in resource graphs.

**Computation Type:** Programmatic (no LLM required)

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `resource_dirs` | list[string] | Yes | - | Directories containing resources to analyze |

**Example:**

```yaml
phases:
  - name: check_cycles
    type: circular_dependencies
    params:
      resource_dirs:
        - .claude/agents
        - .claude/skills
    failure_message: "Circular dependency detected: {circular_path}"
    expected_behavior: "Dependencies must be acyclic"
```

**Failure Messages:**

- Single cycle: `{failure_message}: {circular_path}`
- Multiple cycles: `{failure_message}: {cycle_count} cycles detected ({details})`

**Failure Details:**

| Field | Type | Description |
|-------|------|-------------|
| `circular_path` | string | Dependency cycle path (e.g., "A → B → C → A") |
| `cycle_count` | integer | Total number of cycles found |
| `all_cycles` | list[object] | Detailed info for each cycle |

**Example Output:**

```
Circular dependency detected: agent_a → skill_b → skill_c → agent_a
```

---

### max_dependency_depth

Detect when dependency chains exceed maximum depth.

**Computation Type:** Programmatic (no LLM required)

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `max_depth` | integer | No | `5` | Maximum allowed dependency chain depth |
| `resource_dirs` | list[string] | Yes | - | Directories containing resources to analyze |

**Depth Calculation:**

Depth is the longest path from a resource to any leaf dependency:

- Resource with no dependencies: depth 0
- Resource depending on one resource (which has no dependencies): depth 1
- Chain A → B → C → D: A has depth 3

**Example:**

```yaml
phases:
  - name: check_depth
    type: max_dependency_depth
    params:
      max_depth: 3
      resource_dirs:
        - .claude/agents
        - .claude/skills
    failure_message: "Dependency depth {actual_depth} exceeds max {max_depth}"
    expected_behavior: "Keep dependency chains under 3 levels"
```

**Failure Messages:**

- Single violation: `{failure_message}: Depth {actual_depth} exceeds maximum {max_depth}. Chain: {dependency_chain}`
- Multiple violations: `{failure_message}: {violation_count} violations detected ({details})`

**Failure Details:**

| Field | Type | Description |
|-------|------|-------------|
| `actual_depth` | integer | Actual depth of the dependency chain |
| `max_depth` | integer | Maximum allowed depth |
| `dependency_chain` | string | Full dependency chain path |
| `violation_count` | integer | Total number of violations |
| `all_violations` | list[object] | Detailed info for each violation |

**Example Output:**

```
Dependency depth 5 exceeds max 3. Chain: agent_a → skill_b → skill_c → skill_d → skill_e
```

---

## Claude Code Validators

These validators are specific to Claude Code project structure and configuration. They only run when `client_type` is set to `claude-code`.

### claude_skill_settings

Validate that all skills have permission entries in `.claude/settings.json`.

**Computation Type:** Programmatic (no LLM required)

**Client Support:** Claude Code only

**Parameters:** None

**Example:**

```yaml
rule_definitions:
  claude_skill_permissions:
    description: "All skills must have Skill() permissions in settings.json"
    scope: project_level
    supported_clients:
      - claude-code
    document_bundle:
      bundle_type: project
      file_patterns:
        - .claude/settings.json
      bundle_strategy: collection
    phases:
      - name: check_permissions
        type: claude_skill_settings
        failure_message: "Skills missing from permissions"
        expected_behavior: "All skills need Skill() entries in settings.json"
```

**Failure Messages:**

- Settings not found: `settings.json not found at .claude/settings.json`
- Invalid JSON: `Invalid JSON in settings.json: {error}`
- Missing skills: `Skills missing from permissions.allow: {skills}. Add entries like 'Skill({skill})' to .claude/settings.json`

**Failure Details:** None

**Example Output:**

When skills are missing from permissions:
```
Skills missing from permissions
```

When settings.json is not found:
```
Skills missing from permissions
```

---

### claude_settings_duplicates

Validate that `.claude/settings.json` permissions list has no duplicates.

**Computation Type:** Programmatic (no LLM required)

**Client Support:** Claude Code only

**Parameters:** None

**Example:**

```yaml
phases:
  - name: check_duplicates
    type: claude_settings_duplicates
    failure_message: "Duplicate permissions in settings.json"
    expected_behavior: "Permission entries should be unique"
```

**Failure Messages:**

- Invalid JSON: `Invalid JSON in settings.json: {error}`
- Duplicates found: `Duplicate permission entries found: {duplicates}. Remove duplicates from permissions.allow`

**Failure Details:** None

**Example Output:**

When duplicate permissions are found:
```
Duplicate permissions in settings.json
```

When settings.json has invalid JSON:
```
Duplicate permissions in settings.json
```

---

### claude_mcp_permissions

Validate that all MCP servers have permission entries in `.claude/settings.json`.

**Computation Type:** Programmatic (no LLM required)

**Client Support:** Claude Code only

**Parameters:** None

**Example:**

```yaml
phases:
  - name: check_mcp_permissions
    type: claude_mcp_permissions
    failure_message: "MCP servers missing from permissions"
    expected_behavior: "All MCP servers need mcp__ entries or enableAllProjectMcpServers: true"
```

**Failure Messages:**

- Settings not found: `settings.json not found at .claude/settings.json but .mcp.json exists`
- Invalid JSON: `Invalid JSON in {file}: {error}`
- Missing servers: `MCP servers missing from permissions.allow: {servers}. Add entries like 'mcp__{server}' or set 'enableAllProjectMcpServers: true'`

**Note:** If `enableAllProjectMcpServers: true` is set in settings.json, individual permissions are not required.

**Failure Details:** None

**Example Output:**

When MCP servers are missing from permissions:
```
MCP servers missing from permissions
```

When settings.json is not found but .mcp.json exists:
```
MCP servers missing from permissions
```

---

## LLM-Based Validators

### prompt

Use an LLM to analyze content for semantic validation.

**Computation Type:** LLM (requires API key/provider configuration)

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `prompt` | string | Yes | - | Prompt for the LLM to analyze content |
| `model` | string | Yes | - | Model to use (must be defined in config) |
| `available_resources` | list[string] | No | `[]` | Resources to make available (`skill`, `agent`, `command`, etc.) |

**Example:**

```yaml
phases:
  - name: check_completeness
    type: prompt
    model: haiku
    prompt: |
      Analyze this skill for completeness.

      CRITICAL ISSUES (report these):
      1. Missing "when to use" guidance
      2. No actionable instructions
      3. Missing examples

      ACCEPTABLE (do NOT report):
      - Brief descriptions
      - References to project files
    available_resources:
      - skill
    failure_message: "Skill is incomplete"
    expected_behavior: "Skills should be self-contained with clear guidance"
```

**Failure Messages:**

- Model not configured: `Model '{model}' not found in configuration`
- API error: `LLM API error: {error}`
- Custom message: `{failure_message from rule}` (when LLM reports an issue)

**Failure Details:** Varies based on LLM response

**Example Output:**

When LLM detects issues based on the prompt:
```
Skill is incomplete
```

When model is not configured:
```
Model 'haiku' not found in configuration
```

When there's an API error:
```
LLM API error: Rate limit exceeded
```

---

## Troubleshooting

### Validator Not Found

If you get "Unsupported validation rule type" error:

1. Check validator name matches exactly (case-sensitive)
2. Verify validator is registered in `ValidatorRegistry`
3. For client-specific validators, ensure `supported_clients` is set

### Missing Parameters

If you get "requires 'X' param" error:

1. Check required parameters table in this document
2. Ensure params are nested under `params:` key
3. Verify parameter types match expectations

### Placeholder Not Replaced

If placeholders remain in output (e.g., `{circular_path}`):

1. Verify validator supports `failure_details` (check this doc)
2. Check placeholder name matches `failure_details` key exactly
3. Ensure validator is populating `failure_details` on failure

### Performance Issues

For slow validation:

1. Use `--no-llm` flag to skip LLM-based validators
2. Use `--rules` to run specific rules only
3. Consider splitting large rulesets into separate files
4. Use programmatic validators where possible

---

## Contributing

To add a new validator:

1. Inherit from `BaseValidator`
2. Implement `computation_type` property
3. Implement `validate()` method
4. Populate `failure_details` dictionary for actionable messages
5. Use `_format_message()` helper for template interpolation
6. Register in `ValidatorRegistry`
7. Document in this file

Example validator skeleton:

```python
class MyValidator(BaseValidator):
    @property
    def computation_type(self) -> Literal["programmatic", "llm"]:
        return "programmatic"

    def validate(
        self,
        rule: ValidationRule,
        bundle: DocumentBundle,
        all_bundles: Optional[List[DocumentBundle]] = None,
    ) -> Optional[DocumentRule]:
        # Perform validation logic
        if validation_fails:
            failure_details = {
                "specific_detail": "value",
                "count": 42
            }
            message = self._format_message(
                rule.failure_message,
                failure_details
            )
            return DocumentRule(
                bundle_id=bundle.bundle_id,
                bundle_type=bundle.bundle_type,
                file_paths=affected_files,
                observed_issue=message,
                expected_quality=rule.expected_behavior,
                rule_type="",
                context=f"Validation rule: {rule.description}",
                failure_details=failure_details
            )
        return None
```
