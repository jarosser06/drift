# Drift

AI agent conversation analyzer that identifies gaps between AI actions and user intent.

## What It Does

Drift analyzes AI agent conversations to find patterns where the AI diverged from what the user wanted. It detects issues like incomplete work, missed workflow opportunities, and ignored project features - helping you improve documentation, prompts, and agent configuration.

**Key capabilities:**
- **Project-aware analysis**: Scans your project for available commands, skills, and MCP servers
- **6 rules**: Detects incomplete work, delegation misses, skill ignorance, workflow bypasses, and more
- **Multi-provider**: AWS Bedrock (Claude models)
- **Multi-agent**: Claude Code support
- **Structured output**: Markdown or JSON, grouped by issue type

## Installation

```bash
# Clone and install with uv (recommended)
git clone <repository-url>
cd drift
uv pip install -e ".[dev]"
```

## Quick Start

```bash
# Configure AWS credentials for Bedrock
aws configure

# Run analysis on latest conversation
drift

# Analyze last 7 days with JSON output
drift --days 7 --format json

# Analyze specific rules only
drift --rules incomplete_work,documentation_gap

# Use different model
drift --model sonnet
```

## Example Output

```markdown
# Drift Analysis Results

## Summary
- Total conversations: 3
- Total rule violations: 3
- Rules checked: 6
- Rules passed: 3
- Rules warned: 2
- Rules failed: 1
- By type: incomplete_work (1), agent_delegation_miss (1), workflow_bypass (1)
- By agent tool: claude-code (3)

## Rules Passed ✓

- **documentation_gap**: No issues found
- **prescriptive_deviation**: No issues found
- **no_agents_configured**: No issues found

## Failures

### agent_delegation_miss

*When agents are available to handle specialized work, using them reduces errors and maintains consistent workflow patterns.*

**Session:** def-456
**Agent Tool:** claude-code
**Turn:** 5
**Observed:** AI manually wrote test boilerplate
**Expected:** AI should have spawned test-runner agent
**Frequency:** repeated
**Workflow element:** agent_task_delegation
**Context:** Project has test-runner agent configured in .claude/agents/

## Warnings

### incomplete_work

*AI stopping before completing full scope wastes user time and breaks workflow momentum. Clear completion expectations improve efficiency.*

**Session:** abc-123
**Agent Tool:** claude-code
**Turn:** 3
**Observed:** Implemented login form without validation
**Expected:** Complete login system with validation and error handling
**Frequency:** one-time
**Workflow element:** task_completion
**Context:** User had to explicitly request validation in next turn

### workflow_bypass

*Defined workflows and commands exist to streamline common operations. Using them improves consistency and reduces user effort.*

**Session:** ghi-789
**Agent Tool:** claude-code
**Turn:** 2
**Observed:** User manually described PR creation steps
**Expected:** User should have used /create-pr command
**Frequency:** one-time
**Workflow element:** slash_command
**Context:** Project has /create-pr slash command available
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

## Configuration

Default config auto-generates at `~/.config/drift/config.yaml`. Override per-project with `.drift.yaml`.

### Conversation Analysis Rules

These rules analyze AI agent conversations:
- `incomplete_work` - AI stopped before completing full scope
- `agent_delegation_miss` - AI did work manually instead of using agents (Claude Code only)
- `skill_ignored` - AI didn't use available skills (Claude Code only)
- `workflow_bypass` - User manually executed steps that commands automate
- `prescriptive_deviation` - AI ignored explicit workflow documentation
- `no_agents_configured` - Project lacks agent definitions (Claude Code only)

### Programmatic Validation Rules

Drift also includes programmatic validators that analyze your project files directly:

#### Dependency Duplicate Validator

Detects redundant transitive dependencies in Claude Code resources (commands, skills, agents). If Command A depends on Skill X, and Skill X depends on Skill Y, then Command A should not also list Skill Y as a direct dependency.

**Usage in .drift.yaml:**
```yaml
rule_definitions:
  command_duplicate_dependencies:
    description: "Commands have redundant transitive skill dependencies"
    scope: project_level
    document_bundle:
      bundle_type: mixed
      file_patterns:
        - .claude/commands/*.md
        - .claude/skills/*/SKILL.md
      bundle_strategy: individual
    phases:
      - name: check_duplicates
        type: dependency_duplicate
        description: "Check for redundant transitive dependencies"
        failure_message: "Found redundant skill dependencies"
        expected_behavior: "Only declare direct dependencies"
        params:
          resource_dirs:
            - .claude/commands
            - .claude/skills
```

#### Markdown Link Validator

Validates all file references and links in markdown files. Detects:
- Broken local file references (both markdown links and plain paths like `./test.sh`)
- Broken external URLs (optional)
- Missing resource references (skills, commands, agents)

**Usage in .drift.yaml:**
```yaml
rule_definitions:
  command_broken_links:
    description: "Commands contain broken file references or links"
    scope: project_level
    document_bundle:
      bundle_type: command
      file_patterns:
        - .claude/commands/*.md
      bundle_strategy: individual
    phases:
      - name: check_links
        type: markdown_link
        description: "Check for broken links"
        failure_message: "Found broken links"
        expected_behavior: "All file references should be valid"
        params:
          check_local_files: true      # Check local file paths
          check_external_urls: false   # Skip external URL validation
```

**What it validates:**
- Markdown links: `[text](path/to/file.md)`
- Relative paths: `./script.sh`, `../docs/guide.md`
- Absolute paths: `/path/to/file`
- Path references: `path/to/file.ext`

**Examples of detected issues:**
- `[Guide](missing.md)` - file doesn't exist
- `See ./test.sh for details` - script not found
- `docs/api.md` - broken reference in text

## License

MIT
