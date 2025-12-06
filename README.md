# Drift

[![PyPI version](https://badge.fury.io/py/ai-drift.svg)](https://pypi.org/project/ai-drift/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Documentation](https://img.shields.io/badge/docs-docs.driftai.dev-blue)](https://docs.driftai.dev)

Test-driven development for AI workflows - define your AI agent standards, validate your project structure, and iterate to compliance.

## What It Does

Drift is a **test-driven development framework for AI workflows**. Define your standards first, validate against them, fix issues, and iterate - just like TDD for code.

### TDD Workflow for AI Agent Projects

1. **Define standards** - Write validation rules in `.drift.yaml` for your expected project structure
2. **Run validation** - Execute `drift --no-llm` to see what's missing or broken (red phase)
3. **Fix issues** - Create files, fix links, update configurations manually or with AI assistance (green phase)
4. **Iterate** - Re-run validation until all checks pass (refactor phase)

**No built-in opinions** - Drift has zero default rules. You define your team's standards in `.drift.yaml`, then validate against them. Perfect for bootstrapping new projects or enforcing consistency across teams.

### Project Structure Validation (Primary Use)

Run `drift --no-llm` for instant feedback without API calls. Define custom rules to check:
- **Dependency health**: Detect redundant transitive dependencies
- **Link integrity**: Validate file references and resource links
- **Completeness checks**: Ensure required structure exists
- **Configuration validation**: Verify formats, frontmatter, permissions
- **Consistency validation**: Detect contradictions in documentation
- **Required files**: Verify essential files exist

**Getting Started:** Check out [`.drift.yaml`](.drift.yaml) in this repository for example rules, or visit the [documentation](https://docs.driftai.dev) for a complete guide.

### Conversation Quality Analysis (Optional)

For teams wanting deeper insights, run `drift` with LLM-based rules to analyze AI agent conversations:
- Incomplete work and premature task abandonment
- Missed delegation opportunities to specialized agents
- Ignored skills, commands, or workflow automation
- Deviation from documented project guidelines

Requires LLM access and rules with `type: prompt`.

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

**Claude Code (CLI):**
```yaml
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
```

Claude Code provider uses your existing Claude Code installation. Requires the `claude` CLI to be installed and in your PATH. No API key needed - uses your Claude Code session.

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
- `agent_frontmatter` - Invalid or missing agent YAML frontmatter (includes model validation)
- `command_frontmatter` - Invalid or missing command YAML frontmatter (includes parameter hints, skill references)
- `agent_tools_format` - Agent tools using YAML list instead of comma-separated format
- `skill_filename_consistency` - Skill directories must contain SKILL.md (uppercase)
- `skill_frontmatter_name_match` - Skill frontmatter name must match directory name

**Quality Validation Examples (require LLM):**
- `agent_description_quality` - Agent descriptions must be action-oriented for effective delegation
- `skill_description_quality` - Skill descriptions must include specific trigger terms for discovery
- `command_description_quality` - Command descriptions must be meaningful in /help output
- `claude_md_documentation_sync` - CLAUDE.md should mention all agents, key skills, and slash commands
- `claude_md_quality` - CLAUDE.md file quality (line count, code blocks, imports, anti-patterns)

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

### Detailed Failure Messages

Many validators support **failure details** with template placeholders for actionable error messages. Use `{placeholder}` syntax in `failure_message` to reference specific values:

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

**Example output:**
```
Dependency depth 5 exceeds max 3. Chain: agent_a → skill_b → skill_c → skill_d → skill_e
```

**Before (generic message):**
```yaml
failure_message: "Dependency validation failed"
# Output: "Dependency validation failed"
```

**After (with placeholders):**
```yaml
failure_message: "Circular dependency: {circular_path}"
# Output: "Circular dependency: agent_a → skill_b → agent_a"
```

Validators that support `failure_details`:
- `dependency_duplicate` - `{duplicate_resource}`, `{declared_by}`, `{duplicate_count}`
- `circular_dependencies` - `{circular_path}`, `{cycle_count}`
- `max_dependency_depth` - `{actual_depth}`, `{max_depth}`, `{dependency_chain}`

See [docs/validators.md](docs/validators.md) for complete validator documentation and all available placeholders.

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

**Bootstrapping New AI Projects (TDD Approach):**
```bash
# 1. Define your standards in .drift.yaml first
# 2. Run validation - watch it fail (red)
drift --no-llm

# 3. Create the required structure (manually or with AI help)
# Example output guides you:
# "CLAUDE.md is missing - expected: Project needs CLAUDE.md"

# 4. Re-run until green
drift --no-llm
```

**Enforcing Team Standards:**
```bash
# Define your team's conventions in .drift.yaml
# Run in CI/CD to block non-compliant PRs
drift --no-llm --format json
```

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
# Validate specific rule categories
drift --no-llm --rules agent_frontmatter,agent_tools_format

# Check completeness across all components
drift --no-llm --rules skill_completeness,agent_completeness
```

**Optional: Conversation Analysis:**
```bash
# Analyze last week's AI collaboration patterns
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
