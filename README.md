# Drift

[![PyPI version](https://badge.fury.io/py/ai-drift.svg)](https://pypi.org/project/ai-drift/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Documentation](https://img.shields.io/badge/docs-docs.driftai.dev-blue)](https://docs.driftai.dev)

Quality assurance for AI-augmented codebases - validates that your project follows recommended patterns for effective AI agent collaboration.

## What It Does

Drift validates your AI-augmented development environment using **custom rules you define** in `.drift.yaml`.

**Getting Started:** Check out [`.drift.yaml`](.drift.yaml) in this repository for example rules, or visit the [documentation](https://docs.driftai.dev) for a complete guide to writing your own validation rules.

**Primary Use: Project Structure Validation**

Run `drift --no-llm` to execute your custom programmatic validation rules without API calls. Define rules in `.drift.yaml` to check:
- **Dependency health**: Detect redundant transitive dependencies in commands, skills, and agents
- **Link integrity**: Validate all file references and resource links in documentation
- **Completeness checks**: Ensure skills, commands, and agents have required structure
- **Configuration validation**: Verify agent tools format, frontmatter schema, and MCP permissions
- **Consistency validation**: Detect contradictions between commands and project guidelines
- **Required files**: Verify essential configuration files exist (e.g., CLAUDE.md)

**Optional Feature: Conversation Quality Analysis**

Run `drift` (requires LLM access and rules with `type: prompt`) to analyze AI agent conversation logs. Define custom rules to detect:
- Incomplete work and premature task abandonment
- Missed delegation opportunities to specialized agents
- Ignored skills, commands, or workflow automation
- Deviation from documented project guidelines

**Note:** Most users run `drift --no-llm` as part of their development workflow or CI/CD. Conversation analysis is optional for teams wanting to improve AI collaboration patterns.

## Installation

**[View on PyPI: ai-drift](https://pypi.org/project/ai-drift/)**

```bash
uv pip install ai-drift
```

For development:
```bash
git clone https://github.com/jarosser06/drift.git
cd drift
uv pip install -e ".[dev]"
```

## Quick Start

**Step 1: Create .drift.yaml with rules**

Create `.drift.yaml` in your project root:

```yaml
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
```

**Step 2: Run validation**

```bash
# Validate project structure (no LLM calls)
drift --no-llm

# Check specific rules only
drift --no-llm --rules claude_md_missing

# JSON output for CI/CD
drift --no-llm --format json

# Include conversation analysis (requires LLM access)
export ANTHROPIC_API_KEY=your-key
drift --days 7
```

## Example Output

Example output if you had defined rules like `agent_broken_links`, `command_broken_links`, etc. in `.drift.yaml`:

```markdown
# Drift Analysis Results

## Summary
- Total conversations: 0
- Total rules: 13
- Total violations: 4
- Total checks: 90
- Checks passed: 86
- Checks failed: 4

## Checks Passed ✓

- **agent_duplicate_dependencies**: No issues found
- **agent_frontmatter**: No issues found
- **agent_tools_format**: No issues found
- **claude_mcp_permissions**: No issues found
- **claude_md_missing**: No issues found
- **command_duplicate_dependencies**: No issues found
- **command_frontmatter**: No issues found
- **skill_duplicate_dependencies**: No issues found

## Failures

### agent_broken_links

*Agents must reference valid files and resources. Broken links cause confusion and errors.*

**Session:** document_analysis (drift)
**File:** .claude/agents/documentation.md
**Observed:** Found broken links: .claude/agents/documentation.md: [drift.yaml] - local file not found
**Expected:** All file references and links should be valid

### command_broken_links

*Commands must reference valid files and resources. Broken links cause confusion and errors.*

**Session:** document_analysis (drift)
**File:** .claude/commands/audit-docs.md
**Observed:** Found broken links: .claude/commands/audit-docs.md: [drift.yaml] - local file not found
**Expected:** All file references and links should be valid
```

## Configuration

**REQUIRED:** Create `.drift.yaml` in your project root with `rule_definitions`. Without this file and rules defined, Drift does nothing.

### Provider Configuration (Optional - For Conversation Analysis)

Configure LLM providers for optional conversation analysis:

**Anthropic API:**
```yaml
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
```

**AWS Bedrock:**
```yaml
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
```

### Example Validation Rules

Here are examples of rules you can define in `.drift.yaml`. Drift includes validation phase types you can use, but you must define the actual rules:

**Dependency Management Examples:**
- `command_duplicate_dependencies` - Commands with redundant transitive skill dependencies
- `skill_duplicate_dependencies` - Skills with redundant transitive dependencies
- `agent_duplicate_dependencies` - Agents with redundant transitive dependencies

**Link Validation Examples:**
- `command_broken_links` - Broken file references in command documentation
- `skill_broken_links` - Broken file references in skill documentation
- `agent_broken_links` - Broken file references in agent documentation

**Configuration Validation Examples:**
- `claude_md_missing` - Missing CLAUDE.md configuration file
- `agent_frontmatter` - Invalid or missing agent YAML frontmatter
- `command_frontmatter` - Invalid or missing command YAML frontmatter
- `agent_tools_format` - Agent tools using YAML list instead of comma-separated format

**Conversation Analysis Examples (require LLM):**
- `incomplete_work` - AI stopped before completing full scope
- `skill_ignored` - AI didn't use available skills
- `workflow_bypass` - User manually executed steps that commands automate

See the "Writing Custom Rules" section below for how to define these in `.drift.yaml`.

## Writing Custom Rules

Add custom validation rules in `.drift.yaml` under `rule_definitions`.

### Rule Structure

Every rule has:
- `description`: What the rule checks
- `scope`: `project_level` (validate project structure) or `conversation_level` (analyze conversations)
- `document_bundle`: What files to validate and how to group them
- `phases`: Validation steps to execute

### Document Bundles

Define which files to validate and how to group them:

```yaml
document_bundle:
  bundle_type: agent           # Type identifier (agent, skill, command, or custom)
  file_patterns:                # Glob patterns for files to include
    - .claude/agents/*.md
  bundle_strategy: individual  # How to group: 'individual' or 'collection'
  resource_patterns:           # Optional: supporting files to include
    - "**/*.py"
```

**Bundle Strategies:**
- `individual`: Each file validated separately (for file-specific checks)
- `collection`: All files validated together (for cross-file checks)

### Validation Phase Types

#### Programmatic Validators (No LLM Required)

**`regex_match`** - Check if file content matches a pattern:
```yaml
phases:
  - name: check_tools_format
    type: regex_match
    description: "Validate tools field format"
    pattern: '^tools:\s+[A-Z][\w_]+(?:,\s*[A-Z][\w_]+)*\s*$'
    flags: 8  # re.MULTILINE
    failure_message: "Tools field uses wrong format"
    expected_behavior: "Tools should be comma-separated"
```

**`markdown_link`** - Validate markdown links:
```yaml
phases:
  - name: check_links
    type: markdown_link
    description: "Validate all markdown links"
    failure_message: "Found broken links"
    expected_behavior: "All links should be valid"
    params:
      check_local_files: true
      check_external_urls: false
```

**`yaml_frontmatter`** - Validate YAML frontmatter:
```yaml
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
```

**`dependency_duplicate`** - Find redundant dependencies:
```yaml
phases:
  - name: check_dependencies
    type: dependency_duplicate
    description: "Check for redundant transitive dependencies"
    params:
      dependency_field: skills
      dependency_type: skill
    failure_message: "Found redundant dependencies"
    expected_behavior: "Only declare direct dependencies"
```

#### LLM-based Validators (Require API Key)

**`prompt`** - Use LLM to analyze content:
```yaml
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
```

### Complete Rule Example

```yaml
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
        description: "Validate tools field uses comma-separated format on single line"
        pattern: '^tools:\s+[A-Z][\w_]+(?:,\s*[A-Z][\w_]+)*\s*$'
        flags: 8
        failure_message: "Agent tools field uses YAML list format instead of comma-separated"
        expected_behavior: "Tools should be: 'tools: Read, Write, Edit' not YAML list"
```

### Multi-Phase Rules

Combine multiple validators:

```yaml
rule_definitions:
  skill_quality:
    description: "Skills must be complete and well-structured"
    scope: project_level
    document_bundle:
      bundle_type: skill
      file_patterns:
        - .claude/skills/*/SKILL.md
      bundle_strategy: individual
      resource_patterns:
        - "**/*.py"
        - "**/*.md"
    phases:
      # First validate frontmatter structure
      - name: check_frontmatter
        type: yaml_frontmatter
        params:
          required_fields:
            - description
        failure_message: "Skill missing frontmatter"
        expected_behavior: "Skills need description field"

      # Then check for broken links
      - name: check_links
        type: markdown_link
        failure_message: "Skill has broken links"
        expected_behavior: "All references should be valid"

      # Finally use LLM for semantic validation
      - name: check_completeness
        type: prompt
        model: haiku
        prompt: "Verify this skill has actionable instructions"
        available_resources:
          - skill
        failure_message: "Skill lacks clear instructions"
        expected_behavior: "Skills should have step-by-step guidance"
```

## CLI Options

**Scope Control:**
- `--no-llm`: Skip LLM-based rules, run only programmatic validation (default: run all)
- `--scope`: Analysis scope (`project`, `conversation`, or `all`)
- `--rules`: Comma-separated list of specific rules to check

**Conversation Options** (when not using `--no-llm`):
- `--latest`: Analyze only the latest conversation
- `--days N`: Analyze conversations from last N days
- `--all`: Analyze all conversations
- `--agent-tool`: Specific agent tool to analyze (e.g., `claude-code`)

**Model Configuration:**
- `--model`: Override model for LLM-based analysis (`sonnet`, `haiku`)
- `--no-cache`: Disable LLM response caching
- `--cache-dir`: Custom cache directory

**Output:**
- `--format`: Output format (`markdown` or `json`)
- `--verbose`: Increase verbosity (`-v`, `-vv`, `-vvv`)

**Other:**
- `--project`: Project path (defaults to current directory)
- `--no-parallel`: Disable parallel rule execution

## Use Cases

**Pre-commit Validation:**
```bash
# Add to pre-commit hook
drift --no-llm --format json
```

**CI/CD Pipeline:**
```yaml
# .github/workflows/validate.yml
- name: Validate AI Configuration
  run: |
    pip install ai-drift
    drift --no-llm --format json
```

**Project Setup:**
```bash
# Validate new agent configurations
drift --no-llm --rules agent_frontmatter,agent_tools_format

# Check completeness
drift --no-llm --rules skill_completeness,agent_completeness
```

**Periodic Reviews:**
```bash
# Analyze last week's conversations
export ANTHROPIC_API_KEY=your-key
drift --days 7 --scope all
```

## Development

```bash
# Run tests (requires 90%+ coverage)
./test.sh

# Run linters
./lint.sh

# Auto-fix formatting
./lint.sh --fix
```

## License

MIT
