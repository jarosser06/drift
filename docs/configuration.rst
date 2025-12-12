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

**Environment-specific validation:**

Use different rule sets for different environments:

.. code-block:: bash

    # Development environment (relaxed rules)
    drift --rules-file rules/dev-rules.yaml

    # Production environment (strict rules)
    drift --rules-file rules/prod-rules.yaml

    # CI/CD environment (subset of checks)
    drift --rules-file rules/ci-rules.yaml
