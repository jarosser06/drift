---
name: linting
description: Expert in maintaining code quality standards using flake8, black, isort, and mypy. Use when fixing linting errors or enforcing code style.
---

# Linting Skill

Expert in maintaining code quality standards for Drift.

## Core Responsibilities

- Ensure all code passes linting checks
- Maintain consistent code formatting
- Enforce type hints with mypy
- Fix linting issues efficiently
- Maintain zero linting errors policy

## Linting Tools

### flake8 (Code Quality)
- **Max line length:** 100 characters
- **Ignored rules:** E203 (whitespace before ':'), W503 (line break before binary operator)
- **Config:** Inline or setup.cfg

### black (Formatting)
- **Line length:** 100 characters
- **Style:** Black default (PEP 8 compliant)
- **Auto-fix:** Use `./lint.sh --fix`

### isort (Import Sorting)
- **Profile:** black (compatible with black formatting)
- **Line length:** 100 characters
- **Auto-fix:** Use `./lint.sh --fix`

### mypy (Type Checking)
- **Mode:** Strict where possible
- **Ignore missing imports:** Enabled for third-party libraries
- **Require type hints:** For all public functions

## Running Linters

- Check all: `./lint.sh`
- Auto-fix formatting: `./lint.sh --fix`
- Individual tools:
  - `flake8 drift/ tests/ --max-line-length=100`
  - `black drift/ tests/ --line-length=100 --check`
  - `isort drift/ tests/ --profile=black --check`
  - `mypy drift/`

## Common Issues and Fixes

### Line Too Long (E501)
```python
# Bad
very_long_function_call_with_many_arguments(arg1, arg2, arg3, arg4, arg5, arg6, arg7, arg8)

# Good
very_long_function_call_with_many_arguments(
    arg1, arg2, arg3, arg4,
    arg5, arg6, arg7, arg8
)
```

### Import Order
Use isort profile=black for consistency:
```python
# Standard library
import os
import sys

# Third-party
import boto3
import click

# Local
from drift.parser import parse_conversation
from drift.detector import detect_drift
```

### Type Hints
Add type hints for all public functions:
```python
def analyze_conversation(
    log_path: str,
    drift_types: list[str],
    provider: str = "bedrock"
) -> dict[str, list[str]]:
    """Analyze conversation log for drift."""
    ...
```

## Pre-Commit Standards

All code must pass linting before:
- Creating commits
- Creating PRs
- Merging to main

Zero tolerance for linting errors in main branch.

