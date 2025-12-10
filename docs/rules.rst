Writing Validation Rules
========================

This guide explains how to write validation rules in Drift. Rules define the standards your project must meet and can validate everything from file existence to semantic code quality.

What Are Rules?
---------------

Rules are validation specifications that check your project against your standards. Rules can be defined in:

- ``.drift.yaml`` - Primary rules file in your project root
- Separate rule files - Organize rules in dedicated ``.yaml`` files and reference them with ``--rules-file``
- Remote URLs - Load shared rule definitions from team repositories

Each rule describes:

- **What to validate** - Files, documentation, dependencies, etc.
- **How to validate** - Using validators (file checks, regex patterns, LLM analysis)
- **What's expected** - Clear standards your project should meet
- **What to report** - Actionable messages when violations occur

Rules follow a test-driven development approach: define standards first, run validation to see failures (red phase), fix issues (green phase), and iterate until all checks pass.

Rule Structure
--------------

Every rule requires these core fields:

.. code-block:: yaml

    rule_definitions:
      my_rule_name:
        description: "What this rule checks"
        scope: project_level  # or conversation_level
        context: "Why this rule exists"
        requires_project_context: true  # Optional: whether rule needs project info
        supported_clients:  # Optional: limit to specific AI clients
          - claude-code
        document_bundle:  # What files to validate
          bundle_type: agent
          file_patterns:
            - .claude/agents/*.md
          bundle_strategy: individual
        phases:  # Validation steps
          - name: check_something
            type: file_exists
            file_path: CLAUDE.md
            failure_message: "File is missing"
            expected_behavior: "File should exist"

Field Descriptions
~~~~~~~~~~~~~~~~~~

**description**
  Human-readable description of what the rule validates. Shows in output when violations are found.

**scope**
  - ``project_level`` - Validates project structure, files, configuration
  - ``conversation_level`` - Analyzes AI agent conversation logs

**context**
  Explains why this rule exists and what problem it solves. Helps users understand the motivation.

**requires_project_context** (optional)
  Set to ``true`` if the rule needs project information to validate correctly. Defaults to ``false``.

**supported_clients** (optional)
  List of AI clients this rule supports (e.g., ``claude-code``, ``cursor``, ``aider``). If specified, rule only runs when client matches.

**document_bundle**
  Defines which files to validate and how to group them. See `Document Bundles`_ section below.

**phases**
  List of validation steps to execute. Each phase uses a validator to check something. See `Writing Phases`_ section below.

Document Bundles
----------------

Document bundles specify which files to validate and how to group them for validation.

Basic Structure
~~~~~~~~~~~~~~~

.. code-block:: yaml

    document_bundle:
      bundle_type: agent           # Type identifier
      file_patterns:               # Glob patterns for files
        - .claude/agents/*.md
      bundle_strategy: individual  # How to group files
      resource_patterns:           # Optional: supporting files
        - "**/*.py"

Bundle Types
~~~~~~~~~~~~

The ``bundle_type`` is a semantic identifier for the type of files being validated:

- ``agent`` - AI agent configuration files
- ``skill`` - Skill definition files
- ``command`` - Command definition files
- ``documentation`` - Documentation files
- ``project`` - Project-wide files
- Custom types - Any string that describes your bundle

Bundle types help organize validation results and provide context in failure messages.

File Patterns
~~~~~~~~~~~~~

Use glob patterns to match files:

.. code-block:: yaml

    file_patterns:
      - "*.md"                    # All markdown in root
      - "docs/**/*.rst"           # All .rst files in docs/ recursively
      - ".claude/agents/*.md"     # All .md files in agents/
      - "src/**/*.py"             # All Python files in src/

Multiple patterns are combined (files matching ANY pattern are included).

Bundle Strategies
~~~~~~~~~~~~~~~~~

The ``bundle_strategy`` determines how files are grouped for validation:

**individual**
  Each file becomes a separate bundle. Use for file-specific validation.

  Example: Checking each agent file for frontmatter issues.

  .. code-block:: yaml

      document_bundle:
        bundle_type: agent
        file_patterns:
          - .claude/agents/*.md
        bundle_strategy: individual

  Creates bundles:

  - Bundle 1: ``developer.md``
  - Bundle 2: ``qa.md``
  - Bundle 3: ``cicd.md``

**collection**
  All files grouped into a single bundle. Use for cross-file validation.

  Example: Checking consistency across all documentation files.

  .. code-block:: yaml

      document_bundle:
        bundle_type: documentation
        file_patterns:
          - "*.md"
          - "docs/**/*.rst"
        bundle_strategy: collection

  Creates bundle:

  - Bundle 1: ``README.md``, ``CLAUDE.md``, ``docs/index.rst``, ``docs/quickstart.rst``, ...

When to Use Each Strategy
~~~~~~~~~~~~~~~~~~~~~~~~~~

**Use individual when:**

- Validating file-specific properties (frontmatter, structure)
- Checking each file independently (broken links, regex patterns)
- Reporting violations per file

**Use collection when:**

- Validating relationships between files (cross-references)
- Checking project-wide consistency
- Analyzing multiple files together (duplicate detection)

Resource Patterns (Optional)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``resource_patterns`` field includes supporting files that validators can reference but don't directly validate:

.. code-block:: yaml

    document_bundle:
      bundle_type: command
      file_patterns:
        - .claude/commands/*.md
      bundle_strategy: individual
      resource_patterns:
        - .claude/skills/*/SKILL.md
        - CLAUDE.md

This makes skill files and CLAUDE.md available to validators (e.g., for checking cross-references) without directly validating them.

Writing Phases
--------------

Phases are validation steps that execute sequentially. Each phase uses a validator to check something specific.

Basic Phase Structure
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

    phases:
      - name: check_file
        type: file_exists
        file_path: CLAUDE.md
        failure_message: "CLAUDE.md is missing"
        expected_behavior: "Project needs CLAUDE.md"

Phase Fields
~~~~~~~~~~~~

**name**
  Identifier for this phase. Used in logging and debugging.

**type**
  Validator type to use. See :doc:`validators` for complete list of available validators.

**failure_message**
  Message shown when validation fails. Can include template placeholders like ``{circular_path}`` that validators populate.

**expected_behavior**
  Describes what should be present/correct. Helps users fix violations.

**Additional fields**
  Each validator type accepts different parameters. See :doc:`validators` for validator-specific parameters.

Single-Phase Rules
~~~~~~~~~~~~~~~~~~

Most rules use a single phase:

.. code-block:: yaml

    rule_definitions:
      readme_exists:
        description: "Project must have README.md"
        scope: project_level
        context: "README.md documents project for users"
        phases:
          - name: check_readme
            type: file_exists
            file_path: README.md
            failure_message: "README.md is missing"
            expected_behavior: "Create README.md in project root"

Multi-Phase Rules
~~~~~~~~~~~~~~~~~

Rules can chain multiple phases for comprehensive validation. All phases must pass for the rule to pass:

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
          # Phase 1: Fast programmatic check
          - name: check_frontmatter
            type: yaml_frontmatter
            params:
              required_fields:
                - name
                - description
            failure_message: "Missing required frontmatter"
            expected_behavior: "Skills need name and description"

          # Phase 2: Dependency validation
          - name: check_dependencies
            type: claude_circular_dependencies
            params:
              resource_dirs:
                - .claude/skills
            failure_message: "Skill has circular dependencies"
            expected_behavior: "Skills should not depend on themselves"

          # Phase 3: Semantic analysis (expensive)
          - name: check_completeness
            type: prompt
            model: sonnet
            prompt: "Verify skill has clear examples and instructions"
            available_resources:
              - skill
            failure_message: "Skill lacks examples"
            expected_behavior: "Skills should have working examples"

Execution Order
^^^^^^^^^^^^^^^

Phases execute sequentially in the order defined. If any phase fails, subsequent phases are skipped.

Typical ordering:

1. Programmatic checks (file existence, regex patterns)
2. Structural checks (dependencies, schemas)
3. LLM-based semantic checks (API calls)

This ordering runs cheaper checks first, minimizing API costs.

Validator Types
^^^^^^^^^^^^^^^

You can mix any validator types in phases:

- **Core validators** - File checks, regex, schemas, etc.
- **Claude Code validators** - Dependency graphs, settings validation
- **LLM-based validators** - Semantic analysis using language models

See :doc:`validators` for complete documentation of all available validators.

Example Rules
-------------

File Existence Check
~~~~~~~~~~~~~~~~~~~~

Check if a required file exists:

.. code-block:: yaml

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

Pattern Matching
~~~~~~~~~~~~~~~~

Validate file content matches a pattern:

.. code-block:: yaml

    rule_definitions:
      agent_tools_format:
        description: "Agent tools must use comma-separated format"
        scope: project_level
        context: "Claude Code requires comma-separated tools format"
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
            flags: 8  # re.MULTILINE
            failure_message: "Agent tools field uses YAML list format"
            expected_behavior: "Tools should be: 'tools: Read, Write, Edit'"

Frontmatter Validation
~~~~~~~~~~~~~~~~~~~~~~

Validate YAML frontmatter in markdown files:

.. code-block:: yaml

    rule_definitions:
      agent_frontmatter:
        description: "Agents must have valid frontmatter"
        scope: project_level
        context: "Frontmatter defines agent configuration"
        requires_project_context: true
        document_bundle:
          bundle_type: agent
          file_patterns:
            - .claude/agents/*.md
          bundle_strategy: individual
        phases:
          - name: check_frontmatter
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
            expected_behavior: "Frontmatter must have name, description, model"

Link Validation
~~~~~~~~~~~~~~~

Check for broken links in markdown files:

.. code-block:: yaml

    rule_definitions:
      command_broken_links:
        description: "Commands must reference valid files"
        scope: project_level
        context: "Broken links cause errors"
        requires_project_context: true
        document_bundle:
          bundle_type: command
          file_patterns:
            - .claude/commands/*.md
          bundle_strategy: individual
        phases:
          - name: check_links
            type: markdown_link
            failure_message: "Found broken links"
            expected_behavior: "All references valid"
            params:
              check_local_files: true
              check_external_urls: false

Dependency Validation
~~~~~~~~~~~~~~~~~~~~~

Detect circular dependencies in Claude Code resources:

.. code-block:: yaml

    rule_definitions:
      command_circular_dependencies:
        description: "Commands must not have circular skill dependencies"
        scope: project_level
        context: "Circular dependencies cause loading failures"
        requires_project_context: true
        supported_clients:
          - claude-code
        document_bundle:
          bundle_type: command
          file_patterns:
            - .claude/commands/*.md
          bundle_strategy: collection
        phases:
          - name: check_circular_dependencies
            type: claude_circular_dependencies
            params:
              resource_dirs:
                - .claude/commands
                - .claude/skills
            failure_message: "Circular dependency detected: {circular_path}"
            expected_behavior: "Dependencies must be acyclic"

Detect redundant dependencies:

.. code-block:: yaml

    rule_definitions:
      command_duplicate_dependencies:
        description: "Commands should only declare direct dependencies"
        scope: project_level
        context: "Transitive dependencies are automatically included"
        requires_project_context: true
        supported_clients:
          - claude-code
        document_bundle:
          bundle_type: command
          file_patterns:
            - .claude/commands/*.md
          bundle_strategy: individual
        phases:
          - name: check_dependencies
            type: claude_dependency_duplicate
            params:
              resource_dirs:
                - .claude/commands
                - .claude/skills
            failure_message: "Found redundant dependency '{duplicate_resource}'"
            expected_behavior: "Only declare direct dependencies"

Detect excessive dependency depth:

.. code-block:: yaml

    rule_definitions:
      command_dependency_depth:
        description: "Command dependency chains must not be too deep"
        scope: project_level
        context: "Deep chains slow loading and complicate debugging"
        requires_project_context: true
        supported_clients:
          - claude-code
        document_bundle:
          bundle_type: command
          file_patterns:
            - .claude/commands/*.md
          bundle_strategy: collection
        phases:
          - name: check_depth
            type: claude_max_dependency_depth
            params:
              max_depth: 3
              resource_dirs:
                - .claude/commands
                - .claude/skills
            failure_message: "Dependency depth {actual_depth} exceeds max {max_depth}"
            expected_behavior: "Keep dependency chains under 3 levels"

LLM-Based Validation
~~~~~~~~~~~~~~~~~~~~

Use language models for semantic validation:

.. code-block:: yaml

    rule_definitions:
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
            model: sonnet
            prompt: |
              Review this documentation for clarity and accuracy.

              Check for:
              1. Clear explanations
              2. Working code examples
              3. Accurate technical details

              Only report significant issues.
            available_resources:
              - document_bundle
            failure_message: "Documentation has quality issues"
            expected_behavior: "Documentation should be clear and accurate"

Configuration Validation
~~~~~~~~~~~~~~~~~~~~~~~~

Validate Claude Code settings configuration:

.. code-block:: yaml

    rule_definitions:
      claude_skill_permissions:
        description: "Skills must have permissions in settings.json"
        scope: project_level
        context: "Skills need permissions to be used"
        requires_project_context: true
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
            expected_behavior: "All skills need Skill() entries"

Multi-Phase Complete Example
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Comprehensive rule combining multiple validation types:

.. code-block:: yaml

    rule_definitions:
      agent_complete_validation:
        description: "Agents must be complete, valid, and high-quality"
        scope: project_level
        context: "Complete agents improve AI effectiveness"
        requires_project_context: true
        supported_clients:
          - claude-code
        document_bundle:
          bundle_type: agent
          file_patterns:
            - .claude/agents/*.md
          bundle_strategy: individual
        phases:
          # Phase 1: Check file structure (fast)
          - name: check_frontmatter
            type: yaml_frontmatter
            params:
              required_fields:
                - name
                - description
                - model
                - tools
            failure_message: "Missing required frontmatter fields"
            expected_behavior: "Agents need name, description, model, tools"

          # Phase 2: Validate tools format (fast)
          - name: check_tools_format
            type: regex_match
            pattern: '^tools:\s+[A-Z][\w_]+(?:,\s*[A-Z][\w_]+)*\s*$'
            flags: 8
            failure_message: "Tools must be comma-separated"
            expected_behavior: "Use format: 'tools: Read, Write, Edit'"

          # Phase 3: Check for broken links (moderate)
          - name: check_links
            type: markdown_link
            params:
              check_local_files: true
              check_external_urls: false
            failure_message: "Agent has broken file references"
            expected_behavior: "All file references must be valid"

          # Phase 4: Semantic quality check (expensive)
          - name: check_quality
            type: prompt
            model: sonnet
            prompt: |
              Analyze this agent for completeness and clarity.

              Check for:
              1. Clear role definition
              2. Specific responsibilities
              3. Working examples

              Only report significant issues.
            available_resources:
              - agent
            failure_message: "Agent needs improvement"
            expected_behavior: "Agent should be self-documenting"

Generating Prompts from Rules
------------------------------

Rules can include custom ``draft_instructions`` templates to generate AI prompts for scaffolding files. Use the ``drift draft`` command to generate prompts from rules.

The ``draft_instructions`` Field
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``draft_instructions`` field is an optional attribute you can add to any rule definition. It contains a template that Drift uses to generate AI prompts for creating files that satisfy your validation requirements.

Basic example:

.. code-block:: yaml

    rule_definitions:
      skill_validation:
        description: "Validate skill documentation"
        scope: project_level
        draft_instructions: |
          # Create Skill File: {file_path}

          Generate a skill file with:
          - Clear title and description in YAML frontmatter
          - Usage section with examples
          - References to relevant tools

          Files to create: {file_paths}
        document_bundle:
          bundle_type: skill
          file_patterns:
            - .claude/skills/*/SKILL.md
          bundle_strategy: individual
        phases:
          - name: check_frontmatter
            type: yaml_frontmatter
            params:
              required_fields: [title, description]

Template Placeholders
~~~~~~~~~~~~~~~~~~~~~

Your ``draft_instructions`` templates can use these placeholders:

- ``{rule_name}`` - Name of the rule
- ``{description}`` - Rule description
- ``{context}`` - Rule context
- ``{bundle_type}`` - Bundle type (skill, agent, command)
- ``{file_path}`` - First target file path
- ``{file_paths}`` - All target files (comma-separated)

Using the Draft Command
~~~~~~~~~~~~~~~~~~~~~~~~

Generate a prompt from a rule:

.. code-block:: bash

    drift draft --target-rule skill_validation

This outputs a formatted prompt to stdout. You can save it to a file:

.. code-block:: bash

    drift draft --target-rule skill_validation --output prompt.md

Auto-Generated Prompts
~~~~~~~~~~~~~~~~~~~~~~~

If no custom ``draft_instructions`` is defined, Drift auto-generates a prompt by analyzing the rule's validation phases. This infers requirements from validators and creates a structured prompt automatically.

Draft Requirements
~~~~~~~~~~~~~~~~~~

For a rule to support the ``draft`` command, it must meet these criteria:

- Rule must have ``document_bundle.file_patterns`` defined
- Rule must use ``bundle_strategy: individual`` (not ``collection``)
- Rule must have ``scope: project_level`` (not ``conversation_level``)

The draft command works on ONE file at a time. If your rule pattern contains wildcards (e.g., ``.claude/skills/*/SKILL.md``), you must specify which file to draft using ``--target-file``.

See :doc:`quickstart` for complete draft workflow examples.

Next Steps
----------

Next Steps
~~~~~~~~~~

- **Validators** - See :doc:`validators` for complete documentation of all available validators
- **Configuration** - See :doc:`configuration` for LLM provider setup (required for ``type: prompt`` validators)

