Quick Start Guide
=================

This guide walks you through installing Drift, running your first validation, understanding the output, and integrating it into your workflow with detailed, real-world examples.

Installation
------------

Installing from PyPI
~~~~~~~~~~~~~~~~~~~~

Install the latest stable version:

.. code-block:: bash

    uv pip install ai-drift

Verify the installation:

.. code-block:: bash

    drift --version

Expected output::

    drift version 0.1.1

Installing for Development
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Clone the repository and install in editable mode:

.. code-block:: bash

    git clone https://github.com/jarosser06/drift.git
    cd drift
    uv pip install -e ".[dev]"

This installs development dependencies (pytest, black, mypy, etc.) needed for contributing.

First Run: Project Validation
------------------------------

First Run: Create Your Rules
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**IMPORTANT:** Drift requires ``.drift.yaml`` with rule definitions. Without rules, Drift has nothing to check.

Create ``.drift.yaml`` in your project root with starter rules:

.. code-block:: yaml

    # .drift.yaml
    rule_definitions:
      # Check CLAUDE.md exists
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

      # Validate agent configuration exists
      agents_md_exists:
        description: "Project must document available agents"
        scope: project_level
        context: "Agents.md documents which AI agents are available"
        phases:
          - name: check_file
            type: file_exists
            file_path: agents.md
            failure_message: "agents.md is missing"
            expected_behavior: "Create agents.md documenting available agents"

      # Check for broken links
      command_broken_links:
        description: "Commands must reference valid files"
        scope: project_level
        context: "Broken links cause errors"
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

Run Drift
~~~~~~~~~

After creating ``.drift.yaml``, run validation:

.. code-block:: bash

    drift --no-llm

What happens:

1. Detects AI clients you're using (Claude Code, etc.)
2. Loads rules from ``.drift.yaml``
3. Runs all checks on your files
4. Reports violations

Understanding the Output
~~~~~~~~~~~~~~~~~~~~~~~~~

Example output when running ``drift --no-llm`` with the starter rules above:

.. code-block:: text

    # Drift Analysis Results

    ## Summary
    - Total conversations: 0
    - Total rules: 3
    - Total violations: 2
    - Total checks: 8
    - Checks passed: 6
    - Checks failed: 2

    ## Checks Passed ✓

    - **command_broken_links**: No issues found

    ## Failures

    ### claude_md_missing

    *Project must have CLAUDE.md*

    **Observed:** CLAUDE.md is missing
    **Expected:** Project needs CLAUDE.md

    ### agents_md_exists

    *Project must document available agents*

    **Observed:** agents.md is missing
    **Expected:** Create agents.md documenting available agents

Let's break down each section:

**Summary Section**
  - **Total conversations**: AI conversation logs analyzed (0 with ``--no-llm``)
  - **Total rules**: Validation rules that ran (3 from your ``.drift.yaml``)
  - **Total violations**: Issues found (2 problems: missing CLAUDE.md and agents.md)
  - **Total checks**: Files/bundles validated (8 total checks)
  - **Checks passed**: Checks that passed (6 files are valid)
  - **Checks failed**: Checks with issues (2 files have problems)

**Checks Passed Section**
  Lists rules that found no issues:

  - ``command_broken_links`` checked all command files for broken links (none found)

**Failures Section**
  Shows detailed information about each violation:

  - **Rule name**: ``claude_md_missing`` and ``agents_md_exists`` (which rules detected issues)
  - **Context**: Why this matters (documentation helps AI understand the project)
  - **Observed**: What Drift found (CLAUDE.md and agents.md files don't exist)
  - **Expected**: What should be there (both files should exist)

Fixing Your First Issue
~~~~~~~~~~~~~~~~~~~~~~~~

The output shows 2 missing files. Let's fix them:

**Step 1: Create CLAUDE.md**

.. code-block:: bash

    cat > CLAUDE.md << 'EOF'
    # My Project

    This project does X, Y, and Z.

    ## Tech Stack
    - Python 3.10+
    - FastAPI
    - PostgreSQL

    ## Key Commands
    - `pytest` - Run tests
    - `uvicorn main:app` - Start server
    EOF

**Step 2: Create agents.md**

.. code-block:: bash

    cat > agents.md << 'EOF'
    # Available Agents

    ## Developer Agent
    Handles feature implementation and bug fixes.

    ## QA Agent
    Writes tests and validates coverage.
    EOF

**Step 3: Verify the fix**

.. code-block:: bash

    drift --no-llm --rules claude_md_missing,agents_md_exists

Expected output::

    # Drift Analysis Results

    ## Summary
    - Total rules: 2
    - Total violations: 0
    - Total checks: 2
    - Checks passed: 2

    ## Checks Passed ✓

    - **claude_md_missing**: No issues found
    - **agents_md_exists**: No issues found

Both issues are now resolved!

How Drift Works
---------------

Drift validates your project by executing rules defined in ``.drift.yaml``. Each rule uses a **validation phase type** to perform checks:

**Available Validation Phase Types:**

- ``file_exists`` - Check if files exist
- ``regex_match`` - Pattern matching in file content
- ``yaml_frontmatter`` - Validate YAML frontmatter structure
- ``markdown_link`` - Check for broken links
- ``dependency_duplicate`` - Detect redundant dependencies
- ``prompt`` - Use LLM for semantic analysis (requires API access)

See :doc:`configuration` for complete list and examples.

**How Rules Execute:**

1. Drift reads ``rule_definitions`` from ``.drift.yaml``
2. For each rule, it gathers files matching ``file_patterns``
3. Each rule **phase** executes using its validation type
4. Results are aggregated into checks and violations

**Example Flow:**

.. code-block:: yaml

    rule_definitions:
      agents_md_exists:
        phases:
          - type: file_exists        # Validation phase type
            file_path: agents.md     # What to check

Drift executes the ``file_exists`` validator → Checks if ``agents.md`` exists → Reports violation if missing

Rules, Checks, and Violations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Drift uses a three-level model:

**Rule** → **Check** → **Violation**

- **Rule**: A validation definition in ``.drift.yaml`` (e.g., ``claude_md_missing``, ``command_broken_links``)
- **Check**: One execution of a rule (on a file, bundle, or conversation)
- **Violation**: A failed check

**Example:**

The ``command_broken_links`` rule with 4 command files runs 4 checks:

- ``.claude/commands/test.md`` → Check passes
- ``.claude/commands/lint.md`` → **Check fails** (broken link) → **Violation**
- ``.claude/commands/create-pr.md`` → Check passes
- ``.claude/commands/audit-docs.md`` → Check passes

Result: 1 rule, 4 checks, 1 violation

Document Bundles and Strategies
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Drift groups files into bundles for validation. Each rule defines how files are bundled:

**Individual Strategy** - Validate each file separately:

.. code-block:: yaml

    document_bundle:
      bundle_type: agent
      file_patterns:
        - .claude/agents/*.md
      bundle_strategy: individual

This creates one bundle per file:

- Bundle 1: ``developer.md``
- Bundle 2: ``qa.md``
- Bundle 3: ``cicd.md``
- Bundle 4: ``documentation.md``

**Collection Strategy** - Validate all files together:

.. code-block:: yaml

    document_bundle:
      bundle_type: mixed
      file_patterns:
        - .claude/commands/*.md
        - CLAUDE.md
      bundle_strategy: collection

This creates one bundle containing all files:

- Bundle 1: ``test.md``, ``lint.md``, ``create-pr.md``, ``CLAUDE.md``

**When to use each:**

- Use **individual** for file-specific checks (broken links, frontmatter validation)
- Use **collection** for cross-file checks (consistency validation, duplicate detection)

Real-World Examples
-------------------

Example 1: Detecting Redundant Dependencies
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Problem:** Your command declares both ``testing`` and ``python-basics`` skills, but ``testing`` already depends on ``python-basics``.

**Configuration:**

.. code-block:: yaml

    # .claude/commands/test.md frontmatter
    ---
    description: Run pytest test suite
    skills:
      - testing
      - python-basics  # Redundant!
    ---

**Running the check:**

.. code-block:: bash

    drift --no-llm --rules command_duplicate_dependencies

**Output:**

.. code-block:: text

    ## Failures

    ### command_duplicate_dependencies

    *Commands should only declare direct skill dependencies. Transitive dependencies are automatically included.*

    **Session:** test_command (drift)
    **File:** .claude/commands/test.md
    **Observed:** Found redundant skill dependencies in commands: .claude/commands/test.md: 'python-basics' is redundant (already declared by 'testing')
    **Expected:** Commands should only declare direct dependencies, not transitive ones

**How to fix:**

Remove ``python-basics`` from the command's frontmatter:

.. code-block:: yaml

    ---
    description: Run pytest test suite
    skills:
      - testing
    ---

Claude Code will automatically include ``python-basics`` because ``testing`` depends on it.

**How this works:**

1. Drift builds a dependency graph from all skills in ``.claude/skills/*/SKILL.md``
2. For each command, it traces the full dependency tree
3. If a command declares skill B, and skill A (also declared) already depends on B, that's redundant
4. The validator reports B as redundant because A includes it transitively

Example 2: Fixing Agent Tools Format
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Problem:** Agent tools written as YAML list instead of comma-separated format.

**Configuration:**

.. code-block:: yaml

    # .claude/agents/developer.md frontmatter (WRONG)
    ---
    name: developer
    description: Feature implementation specialist
    model: sonnet
    tools:
      - Read
      - Write
      - Edit
      - Bash
    ---

**Running the check:**

.. code-block:: bash

    drift --no-llm --rules agent_tools_format

**Output:**

.. code-block:: text

    ## Failures

    ### agent_tools_format

    *Claude Code requires agent tools to be comma-separated on one line, not YAML list format.*

    **Session:** developer (drift)
    **File:** .claude/agents/developer.md
    **Observed:** Agent tools field uses YAML list format (- Read) instead of comma-separated format
    **Expected:** Tools should be comma-separated on one line: 'tools: Read, Write, Edit, Grep, Glob'

**How to fix:**

Change from YAML list to comma-separated:

.. code-block:: yaml

    ---
    name: developer
    description: Feature implementation specialist
    model: sonnet
    tools: Read, Write, Edit, Bash
    ---

**Why this matters:**

Claude Code's parser expects comma-separated tools. YAML list format causes tools to not load correctly, breaking the agent's functionality.

Example 3: Validating CLAUDE.md Exists
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Problem:** Project missing the essential ``CLAUDE.md`` configuration file.

**Running the check:**

.. code-block:: bash

    drift --no-llm --rules claude_md_missing

**Output if missing:**

.. code-block:: text

    ## Failures

    ### claude_md_missing

    *CLAUDE.md provides essential context for Claude Code about project structure and conventions.*

    **Observed:** CLAUDE.md file is missing from project root
    **Expected:** Project should have CLAUDE.md file documenting structure and conventions

**How to fix:**

Create a ``CLAUDE.md`` file in your project root:

.. code-block:: bash

    touch CLAUDE.md

Then populate it with essential project information:

.. code-block:: markdown

    # My Project

    AI-augmented web application built with Django.

    ## Tech Stack

    - **Language**: Python 3.11
    - **Framework**: Django 4.2
    - **Database**: PostgreSQL
    - **Testing**: pytest

    ## Project Structure

    ```
    src/           # Application code
    tests/         # Test suite
    .claude/       # AI agent configuration
    ```

    ## Key Commands

    ```bash
    ./manage.py runserver  # Start development server
    ./test.sh             # Run tests
    ./lint.sh             # Run linters
    ```

    ## Development Guidelines

    - Follow Django conventions
    - 90%+ test coverage required
    - Use type hints for all functions
    - See pyproject.toml for linting rules

**Verify the fix:**

.. code-block:: bash

    drift --no-llm --rules claude_md_missing

Expected output::

    ## Checks Passed ✓

    - **claude_md_missing**: No issues found

Example 4: AI-Assisted Documentation Quality Review
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Problem:** Want to ensure documentation is clear, accurate, and helpful - something only an LLM can judge semantically.

**Configuration:**

.. code-block:: yaml

    # .drift.yaml - Add this prompt-based rule
    rule_definitions:
      documentation_quality:
        description: "Documentation should be clear, accurate, and helpful"
        scope: project_level
        context: "Good documentation improves developer experience"
        document_bundle:
          bundle_type: documentation
          file_patterns:
            - "*.md"
            - "docs/**/*.rst"
          bundle_strategy: individual
        phases:
          - name: review_quality
            type: prompt
            model: sonnet
            prompt: |
              Review this documentation for quality issues:

              1. **Clarity**: Is the content clear and easy to understand?
              2. **Accuracy**: Are code examples correct and runnable?
              3. **Completeness**: Are important details missing?
              4. **Tone**: Is the language professional and objective?

              Only report significant issues that would confuse users.
              Provide specific examples of problems found.
            available_resources:
              - document_bundle
            failure_message: "Documentation quality issues found"
            expected_behavior: "Documentation should be clear, accurate, and complete"

**Running the check:**

.. code-block:: bash

    drift --rules documentation_quality

**Output:**

.. code-block:: text

    ## Failures

    ### documentation_quality

    *Documentation should be clear, accurate, and helpful*

    **File:** docs/quickstart.rst
    **Observed:** Found clarity and accuracy issues:
                  1. Installation section references 'pip install' but project uses uv
                  2. Example output shows fake data that doesn't match actual CLI output
                  3. Claims "built-in rules" exist but rules must be defined in .drift.yaml
    **Expected:** Documentation should be clear, accurate, and complete
    **Context:** Good documentation improves developer experience

**How to fix:**

1. Update installation commands to use ``uv pip install ai-drift``
2. Run actual Drift commands and copy real output
3. Remove references to "built-in rules" - clarify rules come from ``.drift.yaml``

**Why this matters:**

LLM-based validation can catch semantic issues that regex patterns miss: misleading examples, inconsistent terminology, confusing explanations. This is especially valuable for documentation, API design, and user-facing content.

Example 5: Checking Specific Rules Only
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Run validation for only the rules you care about:

.. code-block:: bash

    # Check agent configuration only
    drift --no-llm --rules agent_frontmatter,agent_tools_format,agent_broken_links

    # Check dependency health across all resource types
    drift --no-llm --rules command_duplicate_dependencies,skill_duplicate_dependencies,agent_duplicate_dependencies

    # Check link integrity only
    drift --no-llm --rules command_broken_links,skill_broken_links,agent_broken_links

Conversation Analysis
---------------------

First, add conversation analysis rules to ``.drift.yaml``:

.. code-block:: yaml

    # .drift.yaml - Add these conversation analysis rules
    rule_definitions:
      workflow_bypass:
        description: "User manually executed steps that commands automate"
        scope: conversation_level
        context: "Slash commands automate common workflows"
        phases:
          - name: check_manual_workflows
            type: prompt
            model: sonnet
            prompt: |
              Analyze this conversation for manual workflows that could use commands.

              Look for:
              1. User manually running multiple commands (git add/commit/push, pytest, linting)
              2. Repetitive tasks done by hand that commands automate
              3. User doing steps documented in slash commands

              Only report if automation was clearly available but not used.
            available_resources:
              - conversation
            failure_message: "Found manual workflows"
            expected_behavior: "Use slash commands for automated workflows"

      skill_ignored:
        description: "AI didn't use available skills"
        scope: conversation_level
        context: "Skills provide specialized capabilities"
        phases:
          - name: check_skill_usage
            type: prompt
            model: sonnet
            prompt: |
              Analyze if AI agent ignored available skills.

              Check if AI manually did work that skills automate:
              1. Wrote tests manually instead of using testing skill
              2. Fixed linting issues manually instead of using linting skill
              3. Performed code review manually instead of using code-review skill

              Only report clear misses, not judgment calls.
            available_resources:
              - conversation
            failure_message: "AI didn't use available skills"
            expected_behavior: "Use skills for specialized tasks"

Then analyze conversations:

.. code-block:: bash

    # Analyze latest conversation (requires LLM access)
    drift --latest --scope conversation

    # Or analyze multiple conversations (e.g., end of week review)
    drift --days 7 --scope conversation

Example output::

    # Drift Analysis Results

    ## Summary
    - Total conversations: 3
    - Total rules: 2
    - Total violations: 2
    - Total checks: 3
    - Checks passed: 1
    - Checks failed: 2
    - By rule: workflow_bypass (1), skill_ignored (1)

    ## Checks Passed ✓

    - **workflow_bypass**: No issues found (2 conversations checked)

    ## Failures

    ### workflow_bypass

    *User manually executed steps that commands automate*

    **Session:** feature-implementation
    **Agent Tool:** claude-code
    **File:** feature-implementation_2024-12-02.json
    **Source:** conversation_analysis
    **Observed:** User manually ran: git add ., git commit -m "...", git push
                  Available command: /create-pr automates git workflow
    **Expected:** Use /create-pr command for automated git + PR creation
    **Context:** Slash commands automate common workflows

    ### skill_ignored

    *AI didn't use available skills*

    **Session:** bugfix-session
    **Agent Tool:** claude-code
    **File:** bugfix-session_2024-12-01.json
    **Source:** conversation_analysis
    **Observed:** AI manually ran black, flake8, isort, mypy separately
                  Available skill: linting skill automates all code quality checks
    **Expected:** Use linting skill for comprehensive code quality automation
    **Context:** Skills provide specialized capabilities

Next Steps
----------

Now that you understand the basics:

1. **Read the Configuration Guide** - :doc:`configuration` - Learn how to write custom validation rules and see all available validators
2. **Check the API Reference** - :doc:`api` - Programmatic usage and validator documentation
3. **Integrate with CI/CD** - Add Drift to your automated workflows
4. **Try Conversation Analysis** - Set up LLM access to analyze AI interaction patterns

**Common next actions:**

- Run ``drift --no-llm`` regularly to catch configuration issues
- Add pre-commit hooks to enforce validation
- Create custom rules for project-specific conventions
- Analyze AI conversations from last 7 days with ``drift --days 7``

**Get help:**

- File issues: https://github.com/jarosser06/drift/issues
- View examples: https://github.com/jarosser06/drift/tree/main/examples
- Read the docs: https://drift.readthedocs.io
