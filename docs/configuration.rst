Configuration
=============

Drift uses ``.drift.yaml`` for configuration. Place this file in your project root.

Basic Configuration
-------------------

Minimal configuration with custom rules:

.. code-block:: yaml

    # .drift.yaml
    rule_definitions:
      claude_md_missing:
        description: "Project must have CLAUDE.md"
        scope: project_level
        context: "CLAUDE.md provides project instructions"
        phases:
          - name: check_file
            type: file_exists
            file_path: CLAUDE.md
            failure_message: "CLAUDE.md is missing"
            expected_behavior: "Project needs CLAUDE.md"

Validators Reference
--------------------

For complete documentation of all available validators including parameters, examples, and usage, see :doc:`validators`.

Quick reference of validator categories:

**File Validators**
  - ``file_exists`` - Check if files exist
  - ``file_size`` - Validate file size/line count
  - ``file_count`` - Check number of files

**Content Validators**
  - ``regex_match`` - Pattern matching
  - ``yaml_frontmatter`` - Validate frontmatter
  - ``markdown_link`` - Check broken links
  - ``json_schema`` - Validate JSON structure
  - ``yaml_schema`` - Validate YAML structure

**Dependency Validators**
  - ``circular_dependencies`` - Detect cycles (generic)
  - ``max_dependency_depth`` - Detect deep chains (generic)
  - ``dependency_duplicate`` - Detect redundant deps (generic)

**Claude Code Validators**
  - ``claude_circular_dependencies`` - Detect cycles in Claude resources
  - ``claude_max_dependency_depth`` - Detect deep chains in Claude resources
  - ``claude_dependency_duplicate`` - Detect redundant deps in Claude resources
  - ``claude_skill_settings`` - Validate skill permissions
  - ``claude_mcp_permissions`` - Validate MCP permissions

**LLM-Based Validators**
  - ``prompt`` - Use LLM for semantic analysis (requires provider configuration)

Example validator usage:

.. code-block:: yaml

    phases:
      - name: check_file
        type: file_exists
        file_path: CLAUDE.md
        failure_message: "CLAUDE.md is missing"
        expected_behavior: "Project needs CLAUDE.md"

Provider and Model Configuration
---------------------------------

Configure LLM providers and models for conversation analysis rules that use ``type: prompt``.

Anthropic API Provider
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

    # .drift.yaml
    providers:
      anthropic:
        provider: anthropic
        params:
          api_key_env: ANTHROPIC_API_KEY

    models:
      sonnet:
        provider: anthropic
        model_id: claude-sonnet-4-5-20250929
        params:
          max_tokens: 4096
          temperature: 0.0

    default_model: sonnet

AWS Bedrock Provider
~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

    # .drift.yaml
    providers:
      bedrock:
        provider: bedrock
        params:
          region: us-east-1

    models:
      sonnet:
        provider: bedrock
        model_id: us.anthropic.claude-3-5-sonnet-20241022-v2:0
        params:
          max_tokens: 4096
          temperature: 0.0

    default_model: sonnet

Claude Code Provider
~~~~~~~~~~~~~~~~~~~~

Claude Code provider uses your existing Claude Code installation. Requires the ``claude`` CLI to be installed and in your PATH. No API key needed - uses your Claude Code session.

.. code-block:: yaml

    # .drift.yaml
    providers:
      claude-code:
        provider: claude-code
        params: {}

    models:
      sonnet:
        provider: claude-code
        model_id: sonnet  # or 'opus', 'haiku'
        params:
          max_tokens: 4096
          temperature: 0.0
          timeout: 120  # Optional: timeout in seconds (default: 120)

    default_model: sonnet

Multi-Provider Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Example with both Anthropic and Bedrock providers:

.. code-block:: yaml

    # .drift.yaml - Complete example with multiple providers
    providers:
      anthropic:
        provider: anthropic
        params:
          api_key_env: ANTHROPIC_API_KEY
      bedrock:
        provider: bedrock
        params:
          region: us-east-1

    models:
      sonnet-anthropic:
        provider: anthropic
        model_id: claude-sonnet-4-5-20250929
        params:
          max_tokens: 4096
          temperature: 0.0
      sonnet-bedrock:
        provider: bedrock
        model_id: us.anthropic.claude-3-5-sonnet-20241022-v2:0
        params:
          max_tokens: 4096
          temperature: 0.0

    default_model: sonnet-anthropic

    rule_definitions:
      # Your custom rules here
      documentation_quality:
        description: "Documentation must be clear and accurate"
        scope: project_level
        context: "Good docs improve developer experience"
        document_bundle:
          bundle_type: documentation
          file_patterns:
            - "*.md"
          bundle_strategy: individual
        phases:
          - name: review_quality
            type: prompt
            model: sonnet-anthropic  # Use specific model
            prompt: "Review this documentation for clarity and accuracy"
            available_resources:
              - document_bundle
            failure_message: "Documentation has quality issues"
            expected_behavior: "Documentation should be clear and accurate"

Environment Variables
---------------------

For Anthropic API provider:

.. code-block:: bash

    export ANTHROPIC_API_KEY=your_api_key_here

For AWS Bedrock provider:

.. code-block:: bash

    # Configure AWS credentials
    aws configure
    # Or set explicit credentials
    export AWS_ACCESS_KEY_ID=your_access_key
    export AWS_SECRET_ACCESS_KEY=your_secret_key
    export AWS_DEFAULT_REGION=us-east-1

Writing Rules
--------------

For complete documentation on writing validation rules, including rule structure, document bundles, validation phases, and examples, see :doc:`rules`.

Quick reference for rule structure:

.. code-block:: yaml

    rule_definitions:
      my_rule:
        description: "What this rule checks"
        scope: project_level
        context: "Why this rule exists"
        document_bundle:
          bundle_type: agent
          file_patterns:
            - .claude/agents/*.md
          bundle_strategy: individual
        phases:
          - name: check_something
            type: file_exists
            file_path: CLAUDE.md

Separate Rules Files
---------------------

Rules can be separated from configuration settings into dedicated rules files. This allows sharing rules across multiple projects, maintaining team-wide rule repositories, and keeping configuration files focused on project-specific settings.

Default Rules File (.drift_rules.yaml)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Drift automatically loads ``.drift_rules.yaml`` from the project root if it exists. This file contains only rule definitions:

.. code-block:: yaml

    # .drift_rules.yaml
    rule_definitions:
      claude_md_missing:
        description: "Project must have CLAUDE.md"
        scope: project_level
        context: "CLAUDE.md provides project instructions"
        phases:
          - name: check_file
            type: file_exists
            file_path: CLAUDE.md
            failure_message: "CLAUDE.md is missing"
            expected_behavior: "Project needs CLAUDE.md"

      readme_exists:
        description: "Project must have README.md"
        scope: project_level
        context: "README.md documents project usage"
        phases:
          - name: check_readme
            type: file_exists
            file_path: README.md
            failure_message: "README.md is missing"
            expected_behavior: "Project needs README.md"

With this approach, ``.drift.yaml`` contains only configuration:

.. code-block:: yaml

    # .drift.yaml
    providers:
      anthropic:
        provider: anthropic
        params:
          api_key_env: ANTHROPIC_API_KEY

    models:
      sonnet:
        provider: anthropic
        model_id: claude-sonnet-4-5-20250929
        params:
          max_tokens: 4096
          temperature: 0.0

    default_model: sonnet

Loading Rules from Files (--rules-file)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``--rules-file`` CLI argument loads rules from local files or remote HTTP(S) URLs. This argument can be specified multiple times to load rules from multiple sources.

**Local file example:**

.. code-block:: bash

    drift --rules-file /path/to/custom-rules.yaml

**Remote URL example:**

.. code-block:: bash

    drift --rules-file https://example.com/team-rules.yaml

**Multiple files example:**

.. code-block:: bash

    drift --rules-file https://example.com/base-rules.yaml \
          --rules-file /local/project-specific.yaml

Remote rules are fetched with a 10-second timeout. Both HTTP and HTTPS URLs are supported.

Rules Loading Behavior
~~~~~~~~~~~~~~~~~~~~~~~

Drift uses different rule loading behavior depending on whether ``--rules-file`` is specified:

**When --rules-file is provided:**

Drift loads ONLY the specified rules files, excluding default rule sources. This allows isolated testing and controlled rule sets.

.. code-block:: bash

    # Load ONLY custom-rules.yaml (ignores .drift.yaml and .drift_rules.yaml)
    drift --rules-file custom-rules.yaml

**When --rules-file is NOT provided:**

Drift loads rules from default locations with this priority order (later sources override earlier ones):

1. ``.drift.yaml`` ``rule_definitions`` (lowest priority)
2. ``.drift_rules.yaml`` in project root (highest priority)

This default behavior maintains backward compatibility and supports the standard workflow of keeping configuration and rules separate.

**Example: Default behavior (no --rules-file):**

.. code-block:: yaml

    # .drift.yaml - Project config and base rules
    providers:
      anthropic:
        provider: anthropic
        params:
          api_key_env: ANTHROPIC_API_KEY

    models:
      sonnet:
        provider: anthropic
        model_id: claude-sonnet-4-5-20250929
        params:
          max_tokens: 4096

    default_model: sonnet

    rule_definitions:
      base_rule:
        description: "Base validation"
        scope: project_level
        phases:
          - name: check
            type: file_exists
            file_path: README.md

.. code-block:: yaml

    # .drift_rules.yaml - Project-specific rules (override base_rule)
    rule_definitions:
      base_rule:
        description: "Enhanced validation"
        scope: project_level
        phases:
          - name: check
            type: file_exists
            file_path: README.md

.. code-block:: bash

    # Run with default behavior - loads both files
    drift
    # Result: Uses base_rule from .drift_rules.yaml (overrides .drift.yaml version)

**Example: Isolated testing with --rules-file:**

.. code-block:: bash

    # Load ONLY team-wide rules (ignores .drift.yaml and .drift_rules.yaml)
    drift --rules-file https://github.com/myorg/drift-rules/main/standard-rules.yaml
    # Result: Uses only rules from remote URL

    # Load ONLY specific local rules file
    drift --rules-file /path/to/test-rules.yaml
    # Result: Uses only rules from test-rules.yaml

Use Cases and Benefits
~~~~~~~~~~~~~~~~~~~~~~~

**Isolated testing with specific rule sets:**

Test rules in isolation without interference from default project rules:

.. code-block:: bash

    # Test only team standards (ignores project-specific rules)
    drift --rules-file https://github.com/myorg/drift-rules/main/python-standards.yaml

    # Test experimental rules without modifying project config
    drift --rules-file experimental-rules.yaml

**Combining multiple rule sources:**

When using ``--rules-file``, you can load multiple files with later files overriding earlier ones:

.. code-block:: bash

    # Load base team rules, then project customizations
    drift --rules-file https://internal.company.com/drift-rules/base.yaml \
          --rules-file custom-overrides.yaml

**Separation of concerns (default behavior):**

Keep configuration separate from rules using the default loading behavior:

- ``.drift.yaml`` - Provider configuration and model settings
- ``.drift_rules.yaml`` - Project validation rules (automatically loaded)

.. code-block:: bash

    # Automatically loads .drift.yaml config + .drift_rules.yaml rules
    drift

Parameter Override Configuration
---------------------------------

Drift provides a flexible parameter override system to control validator behavior at different levels. This allows you to exclude files using ignore patterns, override validation parameters, or skip entire rules.

Validator Parameter Overrides
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Validator-level overrides apply to all rules using a specific validator type. Use this for project-wide parameter overrides like ignore patterns for all file validation rules.

.. code-block:: yaml

    # .drift.yaml
    validator_param_overrides:
      core:file_exists:
        merge:
          ignore_patterns:
            - ".venv/**"
            - "node_modules/**/*"
            - "build/**"
            - "**/*.tmp"
            - "**/__pycache__/**"

      core:markdown_link:
        merge:
          ignore_patterns:
            - "https://example.com/**"
            - "http://localhost:**"

      core:file_size:
        replace:
          max_size_kb: 5000

**Override strategies**:

- ``merge``: Extends lists (like ``ignore_patterns``) or combines dicts
- ``replace``: Completely replaces the parameter value

Rule Parameter Overrides
~~~~~~~~~~~~~~~~~~~~~~~~~

Rule-level overrides apply to specific rules. This is useful when you need rule-specific configuration that differs from the validator defaults.

.. code-block:: yaml

    # .drift.yaml
    rule_param_overrides:
      # Rule-level override
      Python::documentation:
        merge:
          ignore_patterns:
            - "tests/**"

      # Group-qualified rule
      General::skill_validation:
        replace:
          check_external_urls: false

      # Phase-specific override (most specific)
      General::skill_validation::check_links:
        merge:
          ignore_patterns:
            - "examples/**"

**Rule identifier formats**:

- ``rule_name`` - Applies to all rules with this name (any group)
- ``group::rule_name`` - Applies to specific group and rule
- ``group::rule_name::phase_name`` - Applies to specific phase (most specific)

Skip Validation Rules
~~~~~~~~~~~~~~~~~~~~~~

Skip entire rules or specific phases during validation. This prevents rules from executing at all.

.. code-block:: yaml

    # .drift.yaml
    ignore_validation_rules:
      - "Claude Code::skill_validation::check_description_quality"
      - "Python::formatting::check_line_length"
      - "Documentation::links"

**Rule identifier formats**:

- ``rule_name`` - Matches any rule with this name (any group)
- ``group::rule_name`` - Matches specific group and rule
- ``group::rule_name::phase_name`` - Matches specific phase within a rule

Pattern Matching Types
~~~~~~~~~~~~~~~~~~~~~~~

Drift supports three types of patterns for file matching:

**Glob patterns** (recommended for most use cases):

.. code-block:: yaml

    patterns:
      - "*.md"              # All .md files in root
      - "**/*.py"           # All .py files recursively
      - "src/**"            # Everything under src/
      - "test_*.py"         # Files starting with test_
      - "*.{yml,yaml}"      # Multiple extensions

**Regex patterns** (auto-detected by metacharacters):

.. code-block:: yaml

    patterns:
      - "^https://example\\.com/.*"     # URLs starting with example.com
      - ".*\\.test\\.js$"                # Files ending with .test.js
      - "^/tmp/.*"                       # Absolute paths in /tmp

Regex patterns are detected when the pattern contains metacharacters like ``\(``, ``\)``, ``\^``, ``\$``, ``\+``, ``\.``, ``\|``.

**Literal paths** (exact matching):

.. code-block:: yaml

    patterns:
      - "README.md"         # Exact file name
      - "docs/guide.md"     # Exact relative path

Literal paths are matched exactly after path normalization.

Precedence and Merging
~~~~~~~~~~~~~~~~~~~~~~~

Parameter overrides are applied in this order of precedence:

1. **Base parameters** from rule definition
2. **Validator overrides** applied to all rules using that validator
3. **Rule overrides** applied to matching rule identifiers
4. **Phase overrides** applied to specific phases (most specific)

With **merge strategy**:

- Lists are extended (e.g., ``ignore_patterns``)
- Dicts are combined (later values win on conflicts)

With **replace strategy**:

- Parameter value is completely replaced

Example:

.. code-block:: yaml

    # .drift.yaml
    validator_param_overrides:
      core:file_exists:
        merge:
          ignore_patterns:
            - "**/*.tmp"
            - ".venv/**"

    rule_param_overrides:
      Python::documentation:
        merge:
          ignore_patterns:
            - "tests/**"

When ``Python::documentation`` rule runs with ``core:file_exists`` validator:

- Final ``ignore_patterns``: ``["**/*.tmp", ".venv/**", "tests/**"]``
- All three patterns are applied (merged from validator + rule levels)

When ``General::readme_check`` rule runs with ``core:file_exists`` validator:

- Final ``ignore_patterns``: ``["**/*.tmp", ".venv/**"]``
- Only validator-level patterns apply (no rule-specific overrides)

Use Cases and Examples
~~~~~~~~~~~~~~~~~~~~~~~

**Exclude build artifacts for all validators:**

.. code-block:: yaml

    validator_param_overrides:
      core:file_exists:
        merge:
          ignore_patterns:
            - "dist/**"
            - "build/**"
            - "*.egg-info/**"
            - "**/__pycache__/**"
            - ".pytest_cache/**"

**Skip link checking for development URLs:**

.. code-block:: yaml

    validator_param_overrides:
      core:markdown_link:
        merge:
          ignore_patterns:
            - "http://localhost:**"
            - "https://127.0.0.1:**"
            - "http://0.0.0.0:**"

**Ignore size checks for binary files:**

.. code-block:: yaml

    validator_param_overrides:
      core:file_size:
        merge:
          ignore_patterns:
            - "**/*.png"
            - "**/*.jpg"
            - "**/*.gif"
            - "**/*.pdf"

**Override max file size for specific rule:**

.. code-block:: yaml

    rule_param_overrides:
      Documentation::assets:
        replace:
          max_size_kb: 10000

**Skip frontmatter validation in templates (rule-specific):**

.. code-block:: yaml

    rule_param_overrides:
      Documentation::frontmatter_check:
        merge:
          ignore_patterns:
            - "templates/**/*.md"
            - "examples/**/*.md"

**Disable specific rules during development:**

.. code-block:: yaml

    ignore_validation_rules:
      - "Documentation::completeness"
      - "Code Style::line_length"

**Disable LLM-based quality checks:**

.. code-block:: yaml

    ignore_validation_rules:
      - "Claude Code::skill_validation::check_description_quality"
      - "Claude Code::agent_validation::analyze_completeness"

Configuration Validation
~~~~~~~~~~~~~~~~~~~~~~~~~

Drift validates parameter override configuration at load time:

**Validator type validation:**

.. code-block:: text

    Invalid validator type 'file_exists' in validator_param_overrides.
    Must be in format 'namespace:type' (e.g., 'core:file_exists')

Validator types must follow the namespaced format: ``namespace:type``

**Override strategy validation:**

.. code-block:: text

    Invalid strategy 'append' in validator_param_overrides.
    Must be 'merge' or 'replace'

Only ``merge`` and ``replace`` strategies are supported.

**Rule identifier validation:**

.. code-block:: text

    Invalid rule identifier 'group::' in rule_param_overrides.
    Format must be 'rule', 'group::rule', or 'group::rule::phase'

Rule identifiers cannot have empty parts or more than three segments.

**Pattern validation:**

Invalid regex patterns are caught when patterns are applied:

.. code-block:: text

    Invalid regex pattern '^(unclosed': missing ), unterminated subpattern

Use glob patterns when possible to avoid regex syntax issues.

Environment-Specific Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Different environments may need different parameter overrides. Use separate configuration files with ``--rules-file`` to maintain environment-specific settings.

**Development environment:**

.. code-block:: yaml

    # .drift.dev.yaml
    validator_param_overrides:
      core:file_exists:
        merge:
          ignore_patterns:
            - "**/*.tmp"
            - ".venv/**"

    # Relaxed validation during development
    ignore_validation_rules:
      - "Documentation::completeness"

.. code-block:: bash

    drift --rules-file .drift.dev.yaml

**CI/CD environment:**

.. code-block:: yaml

    # .drift.ci.yaml
    validator_param_overrides:
      core:file_exists:
        merge:
          ignore_patterns:
      - "**/*.tmp"
      - ".venv/**"

    # Strict validation in CI - no rules ignored

.. code-block:: bash

    drift --rules-file .drift.ci.yaml

**Production environment:**

.. code-block:: yaml

    # .drift.prod.yaml
    global_ignore:
      - "**/*.tmp"
      - ".venv/**"

    # Skip expensive LLM checks in production
    ignore_validation_rules:
      - "Code Quality::llm_review"

.. code-block:: bash

    drift --rules-file .drift.prod.yaml
