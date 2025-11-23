# Drift

AI agent conversation drift analyzer - identifies gaps between what AI agents did and what users actually wanted.

## Overview

Drift analyzes AI agent conversation logs to identify patterns where the AI's actions diverged from user intent. It outputs actionable insights for improving project documentation, workflow definitions, and context.

## Features

- **Multi-pass analysis**: One conversation analyzed multiple times, one drift learning type per pass
- **Configurable drift types**: Define custom learning types with detection prompts and signals
- **Multiple providers**: AWS Bedrock support (OpenAI coming soon)
- **Multiple agent tools**: Claude Code support (Cursor, Aider, Windsurf coming soon)
- **Flexible configuration**: Global and project-specific configs with merge support
- **Multiple output formats**: Markdown and JSON
- **Linter-style operation**: Run analysis, get results to stdout, check exit codes

## Installation

### Using uv (recommended)

```bash
# Clone the repository
git clone <repository-url>
cd drift

# Install with uv
uv pip install -e ".[dev]"
```

### Using pip

```bash
pip install -e ".[dev]"
```

## Quick Start

1. **Configure AWS credentials** (for Bedrock):
   ```bash
   aws configure
   # or set environment variables
   export AWS_ACCESS_KEY_ID=your_key
   export AWS_SECRET_ACCESS_KEY=your_secret
   export AWS_DEFAULT_REGION=us-east-1
   ```

2. **Run analysis**:
   ```bash
   drift analyze
   ```

On first run, drift will auto-generate a default config at `~/.config/drift/config.yaml`.

## CLI Usage

### Basic Analysis

```bash
# Analyze latest conversation with markdown output
drift analyze

# Analyze last 7 days
drift analyze --days 7

# Analyze all conversations
drift analyze --all

# Output as JSON
drift analyze --format json
```

### Filtering

```bash
# Analyze specific agent tool
drift analyze --agent-tool claude-code

# Analyze specific drift learning types
drift analyze --types incomplete_work,documentation_gap

# Use specific model
drift analyze --model sonnet
```

## Development

### Testing

```bash
# Run all tests
./test.sh

# Run with coverage (requires 90%+)
./test.sh --coverage
```

### Linting

```bash
# Check all linters
./lint.sh

# Auto-fix issues
./lint.sh --fix
```

## Project Status

✅ **MVP Complete** - Fully built to specification with:
- 90% test coverage achieved
- All linters passing (flake8, black, isort, mypy)
- Modular architecture for easy extension
- AWS Bedrock provider working
- Claude Code conversation loading functional
- Markdown and JSON output formats
- Multi-pass analysis implemented

See [MVP.md](MVP.md) for full specification.

## License

MIT
