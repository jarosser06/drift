# Drift Project

Quality assurance for AI-augmented codebases - validates that your project follows best practices for effective AI agent collaboration.

## Tech Stack

- **Language**: Python 3.10+
- **Package Manager**: uv
- **Core Dependencies**: pydantic, anthropic, boto3, pyyaml, jsonschema
- **Testing**: pytest with 90%+ coverage requirement
- **Linting**: black, flake8, isort, mypy (see pyproject.toml for configuration)

## Project Structure

```
src/drift/          # Main application code
  cli/              # CLI commands and entrypoint
  agent_tools/      # Agent-specific tools (Claude Code, etc.)
  validation/       # Validation rules and engines
  models/           # Pydantic data models
tests/              # Test suite (unit, integration)
  unit/             # Unit tests
  integration/      # Integration tests
.claude/            # Claude Code configuration
  agents/           # Specialized agents (cicd, developer, qa)
  skills/           # Reusable skills (testing, linting, etc.)
  commands/         # Slash commands (/test, /lint, etc.)
```

## Claude Code Setup

The `.claude/` directory contains specialized configurations for AI agents:

**Agents** (`.claude/agents/`):
- `cicd.md` - CI/CD automation and release management
- `developer.md` - Feature implementation
- `qa.md` - Test writing and coverage

**Skills** (`.claude/skills/`):
- `testing` - pytest test suite creation (90%+ coverage)
- `linting` - Code quality (black, flake8, isort, mypy)
- `python-docs` - PEP 257 docstrings
- `code-review` - Quality assurance
- `github-operations` - GitHub automation via MCP

**Commands** (`.claude/commands/`):
- `/test` - Run pytest tests
- `/lint` - Run linters
- `/full-check` - Run tests + linting
- `/code-review` - Comprehensive code review
- `/create-pr` - Create PR with quality validation
- `/create-issue` - Create well-structured GitHub issue

## Key Commands

```bash
# Run Drift analysis
drift                     # Analyze latest conversation
drift --no-llm           # Fast programmatic validation only
drift --days 7           # Analyze last 7 days
drift --format json      # JSON output

# Development
./test.sh                # Run tests with 90%+ coverage requirement
./lint.sh                # Run all linters (flake8, black, isort, mypy)
./lint.sh --fix          # Auto-fix formatting issues

# Installation
uv pip install -e ".[dev]"
```

## Development Guidelines

### Testing Requirements
- Minimum 90% coverage (enforced by pytest)
- Comprehensive test coverage for all new features
- Use pytest fixtures for common test setup
- Mock external API calls (Anthropic, AWS Bedrock, Claude Code CLI)

### Code Quality
- All code must pass linters before commit
- Use type hints (mypy enforces strict typing)
- Follow PEP 8 conventions
- Configuration in `pyproject.toml` - DO NOT duplicate rules here

### Documentation
- PEP 257 compliant docstrings
- Google-style format with custom parameter separator
- Update README.md for user-facing changes
- Keep CLAUDE.md concise (< 1500 tokens)

## Provider Support

Drift supports multiple LLM providers:
- **Anthropic API**: Set `ANTHROPIC_API_KEY`
- **AWS Bedrock**: Configure with `aws configure`
- **Claude Code**: Use existing Claude Code CLI (no API key needed)

Configuration in `.drift.yaml` (see README.md for details).

## Validation Rules

Two categories of validation:
1. **Conversation Analysis** (LLM-based): Analyzes AI agent conversations for quality issues
2. **Project Validation** (Programmatic): Fast checks for documentation, dependencies, links

See `.drift.yaml` for full rule definitions and README.md for descriptions.
