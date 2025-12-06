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

Validators Reference
~~~~~~~~~~~~~~~~~~~~

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

Rules Loading Priority System
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When rules are loaded from multiple sources, Drift applies a priority order where later sources override earlier ones:

1. ``.drift.yaml`` ``rule_definitions`` (lowest priority)
2. ``.drift_rules.yaml`` in project root
3. ``--rules-file`` CLI arguments (highest priority, applied in order)

Rules with the same name in higher-priority sources replace rules from lower-priority sources.

**Example workflow:**

.. code-block:: yaml

    # .drift.yaml - Project config only
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

.. code-block:: yaml

    # .drift_rules.yaml - Project-specific rules
    rule_definitions:
      readme_exists:
        description: "Project must have README.md"
        scope: project_level
        context: "README.md documents project"
        phases:
          - name: check
            type: file_exists
            file_path: README.md

.. code-block:: bash

    # Command line - Load team-wide rules (highest priority)
    drift --rules-file https://github.com/myorg/drift-rules/main/standard-rules.yaml

In this example:

1. Project configuration comes from ``.drift.yaml``
2. Project-specific rules come from ``.drift_rules.yaml``
3. Team-wide rules from the remote URL override any conflicting rules

Use Cases and Benefits
~~~~~~~~~~~~~~~~~~~~~~~

**Sharing rules across projects:**

Create a central rules repository and reference it from multiple projects:

.. code-block:: bash

    drift --rules-file https://github.com/myorg/drift-rules/main/python-standards.yaml

**Team-wide defaults with project overrides:**

Teams can maintain standard rules remotely while allowing projects to override specific rules in ``.drift_rules.yaml``:

.. code-block:: bash

    # Load base team rules, then project customizations
    drift --rules-file https://internal.company.com/drift-rules/base.yaml \
          --rules-file .drift_rules.yaml

**Separation of concerns:**

Keep configuration (providers, models) separate from validation logic (rules):

- ``.drift.yaml`` - Provider configuration and model settings
- ``.drift_rules.yaml`` - Validation rules
- Remote rules - Organization standards

**Environment-specific rules:**

Load different rule sets based on environment:

.. code-block:: bash

    # Development
    drift --rules-file rules/dev-rules.yaml

    # Production
    drift --rules-file rules/prod-rules.yaml
