# Drift

Quality assurance for AI-augmented codebases - validates that your project follows best practices for effective AI agent collaboration.

## What It Does

Drift ensures your AI-augmented development environment is optimized for productivity. It validates both the **quality of AI interactions** and the **health of your project configuration**.

**Think of it as:** A comprehensive testing and linting tool for AI-first development - catching issues in conversation patterns, documentation quality, dependency management, and project structure.

### Two-Level Validation

**1. Conversation Quality Analysis**
Analyzes AI agent conversation logs to detect patterns where work diverged from user intent:
- Incomplete work and premature task abandonment
- Missed delegation opportunities to specialized agents
- Ignored skills, commands, or workflow automation
- Deviation from documented project guidelines

**2. Project Structure Validation**
Programmatically validates your AI collaboration setup:
- **Dependency health**: Detects redundant transitive dependencies in commands, skills, and agents
- **Link integrity**: Validates all file references and resource links in documentation
- **Completeness checks**: Ensures skills, commands, and agents have required structure
- **Consistency validation**: Detects contradictions between commands and project guidelines
- **Required files**: Verifies essential configuration files exist (e.g., CLAUDE.md)

### Key Features

- **Multi-layered analysis**: Combines LLM-based conversation analysis with fast programmatic validation
- **Project-aware**: Automatically discovers and validates commands, skills, agents, and MCP servers
- **Flexible execution**: Run all checks, or use `--no-llm` for fast programmatic-only validation
- **Multi-provider**: AWS Bedrock with Claude models (Sonnet, Haiku)
- **Multi-agent support**: Currently supports Claude Code
- **Rich output**: Markdown with colors (for terminals) or structured JSON
- **Configurable rules**: Extensible YAML-based rule system for custom validations

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

# Run full analysis on latest conversation
drift

# Fast programmatic-only validation (no LLM calls)
drift --no-llm

# Analyze last 7 days with JSON output
drift --days 7 --format json

# Check specific rules only
drift --rules command_broken_links,skill_duplicate_dependencies

# Use different model for analysis
drift --model sonnet

# Disable caching for fresh analysis
drift --no-cache

# Use custom cache directory
drift --cache-dir /tmp/my-cache
```

### Response Caching

Drift automatically caches LLM responses to reduce API costs and speed up re-analysis:
- **Smart invalidation**: Cache automatically invalidates when file content changes
- **Content-based**: Uses SHA-256 hashing to detect changes
- **TTL support**: Default 24-hour cache expiration (configurable)
- **Per-file caching**: Each file + rule combination cached separately

Configure in `.drift.yaml`:
```yaml
cache_enabled: true          # Enable/disable caching (default: true)
cache_dir: .drift/cache      # Cache directory (default: .drift/cache)
cache_ttl: 86400             # TTL in seconds (default: 86400 = 24 hours)
```

CLI overrides:
- `--no-cache`: Disable caching for this run
- `--cache-dir <path>`: Use custom cache directory

## Example Output

```markdown
# Drift Analysis Results

## Summary
- Total conversations: 3
- Total rule violations: 5
- Rules checked: 12
- Rules passed: 7
- Rules warned: 2
- Rules failed: 3

## Rules Passed ✓

- **documentation_gap**: No issues found
- **command_broken_links**: All file references valid
- **skill_duplicate_dependencies**: No redundant dependencies
- **claude_md_missing**: CLAUDE.md exists

## Failures

### command_duplicate_dependencies

*Commands should only declare direct dependencies. Transitive dependencies are automatically included.*

**Bundle:** create-pr command
**Files:** .claude/commands/create-pr.md
**Issue:** Command declares both `pr-writing` skill and `github-operations` skill, but `pr-writing` already depends on `github-operations`
**Expected:** Remove `github-operations` from command dependencies

### skill_completeness

*Incomplete skills create confusion and slow development. Skills must be self-contained with clear examples.*

**Bundle:** testing skill
**Files:** .claude/skills/testing/SKILL.md
**Issue:** Skill references `./examples/test_example.py` which doesn't exist
**Expected:** Include referenced examples or remove broken references

## Warnings

### incomplete_work

*AI stopping before completing full scope wastes user time and breaks workflow momentum.*

**Session:** abc-123
**Agent Tool:** claude-code
**Turn:** 3
**Observed:** Implemented login form without validation
**Expected:** Complete login system with validation and error handling
**Context:** User had to explicitly request validation in next turn
```

## Configuration

Default config auto-generates at `~/.config/drift/config.yaml`. Override per-project with `.drift.yaml`.

### Validation Categories

#### Conversation Analysis Rules (LLM-based)
Analyze AI agent conversation patterns:
- `incomplete_work` - AI stopped before completing full scope
- `agent_delegation_miss` - AI did work manually instead of using agents
- `skill_ignored` - AI didn't use available skills
- `workflow_bypass` - User manually executed steps that commands automate
- `prescriptive_deviation` - AI ignored explicit workflow documentation
- `no_agents_configured` - Project lacks agent definitions

#### Project Validation Rules (Programmatic)
Fast validation without LLM calls:
- `command_duplicate_dependencies` - Redundant transitive skill dependencies in commands
- `skill_duplicate_dependencies` - Redundant transitive dependencies in skills
- `agent_duplicate_dependencies` - Redundant transitive dependencies in agents
- `command_broken_links` - Broken file references in command documentation
- `skill_broken_links` - Broken file references in skill documentation
- `agent_broken_links` - Broken file references in agent documentation
- `claude_md_missing` - Missing CLAUDE.md configuration file
- `skill_completeness` - Skills missing essential structure or examples
- `agent_completeness` - Agents missing scope definition or dependencies
- `command_completeness` - Commands missing execution steps or prerequisites
- `command_consistency` - Commands contradicting project guidelines

### Custom Rule Example

Add custom rules to `.drift.yaml`:

```yaml
rule_definitions:
  command_broken_links:
    description: "Commands contain broken file references"
    scope: project_level
    document_bundle:
      bundle_type: command
      file_patterns:
        - .claude/commands/*.md
      bundle_strategy: individual
    phases:
      - name: check_links
        type: markdown_link
        description: "Validate all markdown links and file paths"
        failure_message: "Found broken links"
        expected_behavior: "All file references should be valid"
        params:
          check_local_files: true
          check_external_urls: false
```

## CLI Options

- `--format` (`-f`): Output format (markdown or json)
- `--scope` (`-s`): Analysis scope (conversation, project, or all)
- `--agent-tool` (`-a`): Specific agent tool to analyze (e.g., claude-code)
- `--rules` (`-r`): Comma-separated list of specific rules to check
- `--latest`: Analyze only the latest conversation
- `--days` (`-d`): Analyze conversations from last N days
- `--all`: Analyze all conversations
- `--model` (`-m`): Override model for analysis (sonnet, haiku)
- `--no-llm`: Skip LLM-based rules, run only programmatic validation (fast)
- `--project` (`-p`): Project path (defaults to current directory)
- `--verbose` (`-v`): Increase verbosity (-v, -vv, -vvv)

## Development

```bash
# Run tests (requires 90%+ coverage)
./test.sh

# Run linters
./lint.sh

# Auto-fix formatting
./lint.sh --fix
```

## Use Cases

**During Development:**
- Run `drift --no-llm` before commits to catch broken links and dependency issues
- Validate skill/command documentation is complete and consistent

**In CI/CD:**
- Enforce documentation quality standards
- Prevent broken resource references from merging

**Periodic Reviews:**
- Analyze conversation patterns to identify workflow improvements
- Find opportunities to better leverage agents, skills, and commands
- Ensure project customizations are being utilized

**Project Setup:**
- Validate new AI agent configurations
- Ensure documentation follows best practices
- Catch structural issues before they impact productivity

## License

MIT
