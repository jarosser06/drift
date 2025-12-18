# Drift Project

TDD framework for AI workflows - define agent/skill/command standards in `.drift.yaml`, validate project structure programmatically, iterate to compliance.

## Tech Stack

- **Language**: Python 3.10+
- **Package Manager**: uv
- **Core Dependencies**: pydantic, anthropic, boto3, pyyaml, jsonschema
- **Testing**: pytest with 90%+ coverage requirement
- **Linting**: black, flake8, isort, mypy (see pyproject.toml for configuration)

## Project Structure

```
src/drift/    # Main application code (cli, validation, models)
tests/        # Test suite (unit, integration)
.claude/      # Claude Code configuration (agents, skills, commands)
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
# Primary use - TDD workflow (define → validate → fix → iterate)
drift --no-llm           # Fast programmatic validation
drift --format json      # JSON output for CI/CD
drift --rules <names>    # Validate specific rules only
drift list               # List available rules
drift draft --target-rule <rule_name> [--output file.md]   # Generate AI prompt
drift document --rules <rule_name> [--format html]         # Generate documentation
# Development
./test.sh                # Run tests (90%+ coverage)
./lint.sh [--fix]        # Run linters
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
All code quality standards (linting, formatting, type checking) are defined in `pyproject.toml`. Run `./lint.sh` before committing.

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
