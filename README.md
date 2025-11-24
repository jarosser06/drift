# Drift

AI agent conversation analyzer that identifies gaps between AI actions and user intent.

## What It Does

Drift analyzes AI agent conversations to find patterns where the AI diverged from what the user wanted. It detects issues like incomplete work, missed workflow opportunities, and ignored project features - helping you improve documentation, prompts, and agent configuration.

**Key capabilities:**
- **Project-aware analysis**: Scans your project for available commands, skills, and MCP servers
- **6 learning types**: Detects incomplete work, delegation misses, skill ignorance, workflow bypasses, and more
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
drift analyze

# Analyze last 7 days with JSON output
drift analyze --days 7 --format json
```

## Example Output

```markdown
## Turn-Level Issues

### incomplete_work

**Session:** abc-123 (my-project)
**Agent Tool:** claude-code
**Turn:** 3
**Observed:** Implemented login form without validation
**Expected:** Complete login system with validation and error handling
**Frequency:** one-time
**Context:** User had to explicitly request validation in next turn

### agent_delegation_miss

**Session:** def-456 (api-service)
**Agent Tool:** claude-code
**Turn:** 5
**Observed:** AI manually wrote test boilerplate
**Expected:** AI should have spawned test-runner agent
**Frequency:** repeated
**Context:** Project has test-runner agent configured in .claude/agents/

## Conversation-Level Issues

### workflow_bypass

**Session:** ghi-789 (web-app)
**Agent Tool:** claude-code
**Turn:** 2
**Observed:** User manually described PR creation steps
**Expected:** User should have used /create-pr command
**Frequency:** one-time
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

**Supported learning types:**
- `incomplete_work` - AI stopped before completing full scope
- `agent_delegation_miss` - AI did work manually instead of using agents (Claude Code only)
- `skill_ignored` - AI didn't use available skills (Claude Code only)
- `workflow_bypass` - User manually executed steps that commands automate
- `prescriptive_deviation` - AI ignored explicit workflow documentation
- `no_agents_configured` - Project lacks agent definitions (Claude Code only)

## License

MIT
