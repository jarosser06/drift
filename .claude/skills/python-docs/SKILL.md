---
name: python-docs
description: Expert in writing PEP 257 compliant docstrings using Google-style format with custom parameter separator. Use when writing or updating Python documentation.
---

# Python Documentation Skill

Expert in writing clear, consistent Python documentation for Drift.

## Core Responsibilities

- Write PEP 257 compliant docstrings
- Document all public modules, classes, and functions
- Keep documentation factual and objective
- Maintain consistency across the codebase
- Update docs when code changes

## Docstring Standards

### Format

Use Google-style docstrings with custom parameter separator:

```python
def function_name(param1: str, param2: int = 0) -> bool:
    """Brief one-line description.

    Longer description if needed. Explain what the function does,
    not how it does it. Be objective and factual.

    -- param1: Description of param1
    -- param2: Description of param2 (default: 0)

    Returns description of return value.
    """
```

### Module Docstrings

```python
"""Module for parsing conversation logs.

This module provides functionality to parse and validate
conversation logs from various AI agent tools.
"""
```

### Class Docstrings

```python
class DriftDetector:
    """Detects drift patterns in conversation logs.

    Analyzes conversation logs using LLM-based analysis to identify
    gaps between AI behavior and user intent.

    -- provider: LLM provider to use (bedrock, openai, etc.)
    -- model_id: Specific model identifier
    -- config: Configuration dictionary for drift detection
    """
```

### Function Docstrings

```python
def detect_drift(
    conversation: dict,
    drift_type: str,
    config: dict
) -> list[str]:
    """Detect specific drift type in conversation.

    Performs single-pass analysis for the specified drift type
    using the configured LLM provider.

    -- conversation: Parsed conversation log dictionary
    -- drift_type: Type of drift to detect (incomplete_work, etc.)
    -- config: Drift type configuration with prompt and signals

    Returns list of detected drift instances with descriptions.
    """
```

## Documentation Rules

### DO

- Be concise and factual
- Use present tense ("Returns" not "Will return")
- Document parameters and return values
- Include type information in signatures
- Explain what, not how
- Use examples for complex functionality

### DON'T

- Use subjective language ("amazing", "simply", "just")
- Include TODOs in docstrings (use issue tracker)
- Over-explain obvious functionality
- Include implementation details
- Use future tense

### Examples

```python
# Good
def parse_log(path: str) -> dict:
    """Parse conversation log from JSON file.

    -- path: Path to JSON log file

    Returns parsed conversation as dictionary.
    Raises FileNotFoundError if path doesn't exist.
    """

# Bad
def parse_log(path: str) -> dict:
    """This amazing function simply parses a log file.

    Just pass in a path and it will magically return
    a dict. TODO: Add validation.
    """
```

## CLI Documentation

Document CLI commands with clear help text:

```python
@click.command()
@click.argument('log_path', type=click.Path(exists=True))
@click.option(
    '--drift-type',
    multiple=True,
    help='Drift type to detect (can specify multiple)'
)
def analyze(log_path: str, drift_type: tuple[str, ...]) -> None:
    """Analyze conversation log for drift patterns.

    Performs multi-pass analysis on the conversation log,
    checking for specified drift types.

    Examples:
        drift --types incomplete_work
        drift --days 7 --format json
    """
```

## README and Guides

- Keep README focused on quick start
- Separate detailed guides into docs/
- Include practical examples
- Link to related documentation
- Update when features change

## Resources

See the following resources:
- `pep-257.md` - PEP 257 docstring conventions
- `google-style.md` - Google-style docstring guide
- `examples.md` - Good documentation examples from Drift
