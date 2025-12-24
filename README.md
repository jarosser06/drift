# Drift

[![PyPI version](https://badge.fury.io/py/ai-drift.svg)](https://pypi.org/project/ai-drift/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

Test-driven development for AI workflows - define your standards, validate your project, iterate to compliance.

## What It Does

Drift validates your AI agent projects against custom rules you define. No built-in opinions - you write the rules in `.drift.yaml`, Drift validates against them.

## Quick Example

**1. Create `.drift.yaml` with your rules:**

```yaml
rule_definitions:
  claude_md_exists:
    description: "Project must have CLAUDE.md"
    scope: project_level
    phases:
      - name: check_file
        type: file_exists
        file_path: CLAUDE.md
        failure_message: "CLAUDE.md is missing"
```

**2. Run validation:**

```bash
uvx --from ai-drift drift
```

**3. Fix issues, re-run until green.**

That's it. Define standards → validate → fix → iterate.

## Installation

Run directly with `uv` (no installation needed):

```bash
uvx --from ai-drift drift
```

Or install with `uv`:

```bash
uv pip install ai-drift
```

## Common Workflow

```bash
# 1. Define your standards in .drift.yaml
# 2. Run validation
uvx --from ai-drift drift

# 3. Generate AI prompts to create missing files
uvx --from ai-drift drift draft --target-rule skill_validation > prompt.md

# 4. Fix issues manually or with AI
# 5. Re-validate until green
uvx --from ai-drift drift
```

## What You Can Validate

Define rules to check:
- Required files exist (CLAUDE.md, README.md, etc.)
- Link integrity (no broken file references)
- YAML frontmatter structure
- Dependency health (no redundant transitive dependencies)
- File format compliance (regex patterns)
- Content quality (with optional LLM-based rules)

**Examples:** See [`.drift.yaml`](.drift.yaml) in this repo.

## Configuration Options

### Parameter Overrides

Override validator parameters at different levels using parameter override configuration:

```yaml
# Validator-level overrides - apply to all rules using a validator
validator_param_overrides:
  core:file_exists:
    merge:
      ignore_patterns:
        - ".venv/**"
        - "node_modules/**/*"
        - "**/*.tmp"

  core:markdown_link:
    merge:
      ignore_patterns:
        - "https://example.com/**"
        - "http://localhost:**"

# Rule-level overrides - apply to specific rules
rule_param_overrides:
  Python::documentation:
    merge:
      ignore_patterns:
        - "tests/**"

  # Phase-specific override
  General::skill_validation::check_links:
    replace:
      check_external_urls: false

# Skip entire rules or phases
ignore_validation_rules:
  - "Claude Code::skill_validation::check_description_quality"
  - "Python::formatting"
```

**Override Strategies:**
- **merge**: Extends lists/dicts (for `ignore_patterns`, etc.)
- **replace**: Completely replaces parameter value

**Pattern Types:**
- **Glob patterns**: `*.md`, `**/*.py`, `src/**/*`
- **Regex patterns**: Auto-detected by metacharacters (`^`, `$`, `\(`, etc.)
- **Literal paths**: Exact path matching

**Precedence:** validator overrides → rule overrides → phase overrides

See **[Configuration Guide](docs/configuration.rst)** for complete details.

## Documentation

- **[Writing Rules](docs/rules.md)** - Define custom validation rules
- **[Validators Reference](docs/validators.md)** - Available validation types
- **[Draft Command](docs/draft.md)** - Generate AI prompts from rules
- **[CLI Options](docs/cli.md)** - Command-line reference
- **[Configuration](docs/configuration.rst)** - Provider setup and ignore patterns

## Development

```bash
./test.sh          # Run tests (90%+ coverage required)
./lint.sh          # Run linters
./lint.sh --fix    # Auto-fix formatting
```

## License

MIT
