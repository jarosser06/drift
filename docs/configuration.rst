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

Add validation rules in ``.drift.yaml`` under ``rule_definitions``.

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

Core Validators
^^^^^^^^^^^^^^^

These validators are not specific to any particular AI coding assistant.

File Validators
"""""""""""""""

Validators for checking file existence, size, and count.

**file_exists** - Check if a file or files matching a pattern exist:

.. code-block:: yaml

    phases:
      - name: check_file
        type: file_exists
        file_path: CLAUDE.md
        failure_message: "CLAUDE.md is missing"
        expected_behavior: "Project needs CLAUDE.md"

Can also use glob patterns:

.. code-block:: yaml

    phases:
      - name: check_skill_files
        type: file_exists
        file_path: .claude/skills/*/SKILL.md
        failure_message: "Found skill directory without SKILL.md"
        expected_behavior: "All skill directories should contain SKILL.md"

**file_not_exists** - Check that a file or pattern does NOT exist:

.. code-block:: yaml

    phases:
      - name: check_no_secrets
        type: file_not_exists
        file_path: .env
        failure_message: ".env file should not be committed"
        expected_behavior: "Use .env.example instead"

**file_count** - Check number of files matching a pattern:

.. code-block:: yaml

    phases:
      - name: check_agent_count
        type: file_count
        file_path: .claude/agents/*.md
        min_count: 1
        max_count: 10
        failure_message: "Invalid number of agents"
        expected_behavior: "Project should have 1-10 agents"

**file_size** - Check file size or line count:

.. code-block:: yaml

    phases:
      - name: check_claude_md_size
        type: file_size
        file_path: CLAUDE.md
        max_count: 300  # Max lines
        failure_message: "CLAUDE.md exceeds 300 lines"
        expected_behavior: "CLAUDE.md should be concise"

**token_count** - Check token count in files:

.. code-block:: yaml

    phases:
      - name: check_skill_tokens
        type: token_count
        file_path: .claude/skills/*/SKILL.md
        max_count: 4000
        failure_message: "Skill exceeds token limit"
        expected_behavior: "Skills should be under 4000 tokens"


Content Validators
""""""""""""""""""

Validators for checking file content, structure, and format.

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

**regex_not_match** - Check that file content does NOT match a pattern:

.. code-block:: yaml

    phases:
      - name: check_no_hardcoded_secrets
        type: regex_not_match
        description: "Ensure no API keys hardcoded"
        pattern: '(api[_-]?key|secret[_-]?key)\s*=\s*["\'][a-zA-Z0-9]{20,}["\']'
        flags: 10  # re.IGNORECASE | re.MULTILINE
        failure_message: "Found hardcoded API keys"
        expected_behavior: "Use environment variables for secrets"

**json_schema** - Validate JSON files against JSON Schema:

.. code-block:: yaml

    phases:
      - name: check_json_structure
        type: json_schema
        params:
          schema:
            type: object
            properties:
              name:
                type: string
              version:
                type: string
            required:
              - name
              - version
        failure_message: "Invalid JSON structure"
        expected_behavior: "JSON should match schema"

**yaml_schema** - Validate YAML files against JSON Schema:

.. code-block:: yaml

    phases:
      - name: check_yaml_structure
        type: yaml_schema
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
        failure_message: "Invalid YAML structure"
        expected_behavior: "YAML should match schema"

**cross_file_reference** - Validate references between files:

.. code-block:: yaml

    phases:
      - name: check_skill_references
        type: cross_file_reference
        source_pattern: ".claude/commands/*.md"
        reference_pattern: "skills:\\s+-\\s+(\\w+)"
        target_pattern: ".claude/skills/{0}/SKILL.md"
        failure_message: "Command references non-existent skill"
        expected_behavior: "All skill references should be valid"

This validator extracts references from source files using the regex pattern, then checks if corresponding target files exist.

**list_match** - Check if a list in file matches expected values:

.. code-block:: yaml

    phases:
      - name: check_dependencies
        type: list_match
        params:
          expected_items:
            - pytest
            - black
            - mypy
          allow_additional: true
        failure_message: "Missing required dependencies"
        expected_behavior: "All required dependencies should be present"

**list_regex_match** - Check if list items match patterns:

.. code-block:: yaml

    phases:
      - name: check_import_format
        type: list_regex_match
        params:
          pattern: "^from [a-z_]+ import \\w+$"
        failure_message: "Invalid import format"
        expected_behavior: "Imports should follow standard format"


Generic Dependency Validators
""""""""""""""""""""""""""""""

These validators work with any dependency graph system and can be extended for different tools (Claude Code, Cursor, Aider, etc.). For Claude Code projects, use the ``claude_*`` variants below.

**circular_dependencies** - Detect circular dependency cycles (generic, extensible):

This is the generic base validator for detecting circular dependencies in any dependency graph system. For Claude Code projects, use ``claude_circular_dependencies`` instead (see Claude Code Validators section below).

**max_dependency_depth** - Detect excessively deep dependency chains (generic, extensible):

This is the generic base validator for detecting deep dependency chains. For Claude Code projects, use ``claude_max_dependency_depth`` instead (see Claude Code Validators section below).

**dependency_duplicate** - Detect redundant dependencies (generic, extensible):

This is the generic base validator for detecting redundant transitive dependencies. For Claude Code projects, use ``claude_dependency_duplicate`` instead (see Claude Code Validators section below).

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

See ``claude_dependency_duplicate`` below for Claude Code-specific implementation.


LLM-Based Validators
""""""""""""""""""""

These validators use Large Language Models for semantic analysis. They work with any configured provider (Anthropic API, AWS Bedrock, Claude Code CLI). See the `Provider and Model Configuration`_ section above for setup.

**prompt** - Use LLM to analyze content:

.. code-block:: yaml

    phases:
      - name: check_completeness
        type: prompt
        model: sonnet  # References model defined in providers section
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

**How LLM Validators Work:**

1. **Provider Configuration**: The ``model`` parameter references a model defined in your ``.drift.yaml`` providers section (see `Provider and Model Configuration`_ above)
2. **API Calls**: Drift sends the prompt and document content to the configured LLM provider
3. **Response Parsing**: The LLM's response is parsed for validation results
4. **Caching**: Responses are cached (default 30 days) to reduce API costs

**Available Providers:**

- Anthropic API (requires ``ANTHROPIC_API_KEY``)
- AWS Bedrock (requires AWS credentials)
- Claude Code CLI (uses existing Claude Code session, no API key needed)

See the `Provider and Model Configuration`_ section for setup details.


Claude Code Validators
^^^^^^^^^^^^^^^^^^^^^^

These validators are specifically designed for Claude Code project structure and conventions.

Claude-Specific Dependency Validators
""""""""""""""""""""""""""""""""""""""

**claude_circular_dependencies** - Detect circular dependency cycles in Claude Code resources:

.. code-block:: yaml

    phases:
      - name: check_circular_dependencies
        type: claude_circular_dependencies
        description: "Detect circular dependency cycles"
        params:
          resource_dirs:
            - .claude/commands
            - .claude/skills
            - .claude/agents
        failure_message: "Found circular dependencies"
        expected_behavior: "Dependencies should not form cycles"

This validator detects when Claude Code resources (commands, skills, agents) depend on each other in a circular fashion. For example:

- **Self-loop**: skill A depends on skill A
- **Two-node cycle**: skill A → skill B → skill A
- **Multi-node cycle**: command A → skill B → skill C → skill B

Circular dependencies can cause:

- Infinite loops during skill loading
- Unclear dependency resolution order
- Maintenance difficulties

The validator builds a complete dependency graph by reading the ``skills:`` field from YAML frontmatter in all resources, then uses depth-first search to detect cycles.

**claude_max_dependency_depth** - Detect excessively deep dependency chains:

.. code-block:: yaml

    phases:
      - name: check_dependency_depth
        type: claude_max_dependency_depth
        description: "Ensure dependencies don't exceed maximum depth"
        params:
          max_depth: 3
          resource_dirs:
            - .claude/commands
            - .claude/skills
            - .claude/agents
        failure_message: "Dependency chain too deep"
        expected_behavior: "Dependencies should not exceed depth of 3"

This validator detects when dependency chains become too deep. For example, with ``max_depth: 3``:

- ✅ **OK**: command → skill A → skill B → skill C (depth 3)
- ❌ **FAIL**: command → skill A → skill B → skill C → skill D (depth 4)

Deep dependency chains can cause:

- Slow skill loading times
- Complex debugging when issues arise
- Unclear responsibility boundaries
- Difficult maintenance

The validator uses breadth-first search to find the longest path from each resource to its deepest dependency. The ``max_depth`` parameter defaults to 5 if not specified.

**claude_dependency_duplicate** - Detect redundant transitive dependencies:

.. code-block:: yaml

    phases:
      - name: check_dependencies
        type: claude_dependency_duplicate
        description: "Check for redundant transitive dependencies"
        params:
          resource_dirs:
            - .claude/commands
            - .claude/skills
            - .claude/agents
        failure_message: "Found redundant dependencies"
        expected_behavior: "Only declare direct dependencies"

This validator detects when a resource declares a dependency that's already included transitively. For example:

.. code-block:: yaml

    # ❌ BAD: command declares both 'testing' and 'python-basics'
    # .claude/commands/test.md
    ---
    skills:
      - testing
      - python-basics  # Redundant! Already included by 'testing'
    ---

    # .claude/skills/testing/SKILL.md
    ---
    name: testing
    skills:
      - python-basics  # 'testing' already depends on this
    ---

The correct approach:

.. code-block:: yaml

    # ✅ GOOD: only declare direct dependency
    # .claude/commands/test.md
    ---
    skills:
      - testing  # 'python-basics' is automatically included
    ---

Redundant declarations cause:

- Maintenance burden (update in multiple places)
- Confusion about actual dependencies
- Longer frontmatter that's harder to read

The validator builds a complete dependency graph and checks if any declared dependency is already reachable through another declared dependency.


Claude-Specific Configuration Validators
"""""""""""""""""""""""""""""""""""""""""

**claude_skill_settings** - Verify skills have corresponding permissions in settings:

.. code-block:: yaml

    phases:
      - name: check_skill_permissions
        type: claude_skill_settings
        failure_message: "Skills missing from .claude/settings.json permissions"
        expected_behavior: "Every skill directory should have a Skill(name) entry in settings"

This validator checks that all skills in ``.claude/skills/`` have corresponding ``Skill(name)`` permission entries in ``.claude/settings.json``. Without these permissions, skills cannot be used.

**claude_settings_duplicates** - Detect duplicate permission entries:

.. code-block:: yaml

    phases:
      - name: check_duplicate_permissions
        type: claude_settings_duplicates
        failure_message: "Duplicate permission entries in .claude/settings.json"
        expected_behavior: "All permission entries should be unique"

This validator ensures the ``.claude/settings.json`` permissions.allow array does not contain duplicate entries. Duplicates are unnecessary and can cause confusion.

**claude_mcp_permissions** - Verify MCP servers have permissions:

.. code-block:: yaml

    phases:
      - name: check_mcp_permissions
        type: claude_mcp_permissions
        failure_message: "MCP servers missing from .claude/settings.json permissions"
        expected_behavior: "Every MCP server should have a MCP(server-name) entry"

This validator checks that all MCP servers defined in ``.mcp.json`` have corresponding ``MCP(server-name)`` permission entries in ``.claude/settings.json``. Without these permissions, MCP servers cannot be accessed.


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

Rules can combine multiple validation phases of ANY type (core validators, Claude validators, or LLM-based). Each phase runs sequentially, and all phases must pass for the rule to pass.

Common use cases:

- Combine programmatic checks with semantic analysis
- Chain validators to build complex validation logic
- Run fast checks first, expensive checks last

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
          # Phase 1: Core validator (fast, programmatic)
          - name: check_frontmatter
            type: yaml_frontmatter
            params:
              required_fields:
                - name
                - description
            failure_message: "Missing required frontmatter"
            expected_behavior: "Skills need name and description"

          # Phase 2: Claude validator (programmatic)
          - name: check_dependencies
            type: claude_circular_dependencies
            params:
              resource_dirs:
                - .claude/skills
            failure_message: "Skill has circular dependencies"
            expected_behavior: "Skills should not depend on themselves"

          # Phase 3: LLM validator (semantic, expensive)
          - name: check_completeness
            type: prompt
            model: sonnet
            prompt: "Verify skill has clear examples and instructions"
            available_resources:
              - skill
            failure_message: "Skill lacks examples"
            expected_behavior: "Skills should have working examples"

**Execution Order:**

Phases execute sequentially in the order defined. If any phase fails, subsequent phases are skipped. This allows you to:

1. Run fast programmatic checks first (yaml_frontmatter, regex_match)
2. Run more expensive checks next (dependency analysis)
3. Run LLM-based checks last (prompt)

This minimizes API costs by only running expensive LLM checks when cheaper checks pass.

**Validator Type Mixing:**

You can mix any validator types in phases:

- Core validators (file_exists, regex_match, etc.)
- Claude Code validators (claude_circular_dependencies, etc.)
- LLM-based validators (prompt)

Each phase is independent and can use any validator type.

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
