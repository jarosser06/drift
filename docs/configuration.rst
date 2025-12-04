Configuration
=============

Drift uses ``.drift.yaml`` for configuration. Place this file in your project root.

Basic Configuration
-------------------

**CRITICAL: Drift requires user-defined rules in .drift.yaml**

Without ``rule_definitions`` in ``.drift.yaml``, Drift has nothing to validate. There are NO built-in rules.

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

Writing Custom Rules
---------------------

Add custom validation rules in ``.drift.yaml`` under ``rule_definitions``.

Rule Structure
~~~~~~~~~~~~~~

Every rule requires:

- ``description``: What the rule checks
- ``scope``: ``project_level`` (validate project structure) or ``conversation_level`` (analyze conversations)
- ``context``: Why this rule exists
- ``requires_project_context``: Whether rule needs project information
- ``document_bundle``: What files to validate and how to group them
- ``phases``: Validation steps to execute

Document Bundles
~~~~~~~~~~~~~~~~

Define which files to validate and how to group them:

.. code-block:: yaml

    document_bundle:
      bundle_type: agent           # Type identifier (agent, skill, command, or custom)
      file_patterns:               # Glob patterns for files to include
        - .claude/agents/*.md
      bundle_strategy: individual  # How to group: 'individual' or 'collection'
      resource_patterns:           # Optional: supporting files to include
        - "**/*.py"

**Bundle Strategies:**

- ``individual``: Each file validated separately (for file-specific checks)
- ``collection``: All files validated together (for cross-file checks)

Validation Phase Types
~~~~~~~~~~~~~~~~~~~~~~

Programmatic Validators (No LLM Required)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**regex_match** - Check if file content matches a pattern:

.. code-block:: yaml

    phases:
      - name: check_tools_format
        type: regex_match
        description: "Validate tools field format"
        pattern: '^tools:\s+[A-Z][\w_]+(?:,\s*[A-Z][\w_]+)*\s*$'
        flags: 8  # re.MULTILINE
        failure_message: "Tools field uses wrong format"
        expected_behavior: "Tools should be comma-separated"

**markdown_link** - Validate markdown links:

.. code-block:: yaml

    phases:
      - name: check_links
        type: markdown_link
        description: "Validate all markdown links"
        failure_message: "Found broken links"
        expected_behavior: "All links should be valid"
        params:
          check_local_files: true
          check_external_urls: false

**yaml_frontmatter** - Validate YAML frontmatter:

.. code-block:: yaml

    phases:
      - name: check_frontmatter
        type: yaml_frontmatter
        params:
          required_fields:
            - name
            - description
            - model
          schema:  # JSON Schema validation
            type: object
            properties:
              name:
                type: string
                pattern: "^[a-z][a-z0-9-]*$"
              model:
                type: string
                enum: ["sonnet", "opus", "haiku"]
            required:
              - name
              - description
        failure_message: "Invalid frontmatter"
        expected_behavior: "Frontmatter should have required fields"

**dependency_duplicate** - Find redundant dependencies:

.. code-block:: yaml

    phases:
      - name: check_dependencies
        type: dependency_duplicate
        description: "Check for redundant transitive dependencies"
        params:
          resource_dirs:
            - .claude/commands
            - .claude/skills
        failure_message: "Found redundant dependencies"
        expected_behavior: "Only declare direct dependencies"

LLM-based Validators (Require API Key)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**prompt** - Use LLM to analyze content:

.. code-block:: yaml

    phases:
      - name: check_completeness
        type: prompt
        model: sonnet
        prompt: |
          Analyze this skill for completeness.

          Check for:
          1. Clear "when to use" guidance
          2. Actionable instructions
          3. Working examples

          Only report if there's a structural problem.
        available_resources:
          - skill  # Makes bundle content available to LLM
        failure_message: "Skill is incomplete"
        expected_behavior: "Skills should be self-contained"

Complete Rule Example
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

    rule_definitions:
      agent_tools_format:
        description: "Agent tools must use comma-separated format, not YAML list"
        scope: project_level
        context: "Claude Code requires comma-separated tools format to work properly"
        requires_project_context: true
        supported_clients:
          - claude-code
        document_bundle:
          bundle_type: agent
          file_patterns:
            - .claude/agents/*.md
          bundle_strategy: individual
        phases:
          - name: check_tools_comma_separated
            type: regex_match
            description: "Validate tools field uses comma-separated format"
            pattern: '^tools:\s+[A-Z][\w_]+(?:,\s*[A-Z][\w_]+)*\s*$'
            flags: 8
            failure_message: "Agent tools field uses YAML list format"
            expected_behavior: "Tools should be: 'tools: Read, Write, Edit'"

Multi-Phase Rules
~~~~~~~~~~~~~~~~~

Combine multiple validators for complex validation:

.. code-block:: yaml

    rule_definitions:
      skill_quality:
        description: "Skills must be complete and well-structured"
        scope: project_level
        context: "Complete skills improve AI effectiveness"
        requires_project_context: true
        document_bundle:
          bundle_type: skill
          file_patterns:
            - .claude/skills/*/SKILL.md
          bundle_strategy: individual
        phases:
          - name: check_frontmatter
            type: yaml_frontmatter
            params:
              required_fields:
                - name
                - description
            failure_message: "Missing required frontmatter"
            expected_behavior: "Skills need name and description"
          - name: check_completeness
            type: prompt
            model: sonnet
            prompt: "Verify skill has clear examples and instructions"
            failure_message: "Skill lacks examples"
            expected_behavior: "Skills should have working examples"
