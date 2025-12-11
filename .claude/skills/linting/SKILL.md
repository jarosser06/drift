---
name: linting
description: Expert in maintaining code quality standards using flake8, black, isort, and mypy. Use when fixing linting errors or enforcing code style.
---

# Linting Skill

Learn how to maintain code quality using flake8, black, isort, and mypy for the Drift project.

## How to Run Linters

### All Linters at Once

```bash
# Check all linting (recommended before commits)
./lint.sh

# Auto-fix formatting issues
./lint.sh --fix
```

### Individual Linters

```bash
# flake8 (code quality checks)
flake8 src/drift/ tests/ --max-line-length=100

# black (code formatting)
black src/drift/ tests/ --line-length=100 --check
black src/drift/ tests/ --line-length=100  # Apply fixes

# isort (import sorting)
isort src/drift/ tests/ --profile=black --check
isort src/drift/ tests/ --profile=black  # Apply fixes

# mypy (type checking)
mypy src/drift/
```

## How to Fix Common Linting Issues

### Line Too Long (E501)

When flake8 reports lines over 100 characters, break them logically:

```python
# Before - line too long
result = very_long_function_call_with_many_arguments(arg1, arg2, arg3, arg4, arg5, arg6, arg7)

# After - properly formatted
result = very_long_function_call_with_many_arguments(
    arg1, arg2, arg3, arg4,
    arg5, arg6, arg7
)
```

For long strings:

```python
# Before
message = "This is a very long error message that exceeds the 100 character limit and needs to be broken up"

# After
message = (
    "This is a very long error message that exceeds the 100 character "
    "limit and needs to be broken up"
)
```

### Import Order Issues

When isort or flake8 flags import order problems:

```bash
# Auto-fix with isort
isort src/drift/core/parser.py --profile=black

# Or fix all files
isort . --profile=black
```

Expected order:

```python
# Standard library
import json
import os
from pathlib import Path

# Third-party
import boto3
import click
from botocore.exceptions import ClientError

# Local
from drift.core.parser import parse_conversation
from drift.core.detector import detect_drift
```

### Type Hint Issues

When mypy reports missing type hints, add them:

```python
# Before - mypy error: Function is missing a return type annotation
def analyze_conversation(log_path, drift_types):
    return {"results": []}

# After - properly typed
def analyze_conversation(
    log_path: str,
    drift_types: list[str]
) -> dict[str, list[str]]:
    """Analyze conversation log for drift."""
    return {"results": []}
```

For optional parameters:

```python
from typing import Optional

def detect_drift(
    conversation: dict,
    config: Optional[dict] = None
) -> list[str]:
    """Detect drift in conversation."""
    pass
```

### Unused Imports (F401)

When flake8 reports unused imports:

```python
# Before - flake8: 'json' imported but unused
import json
import os

def get_path():
    return os.getcwd()

# After - removed unused import
import os

def get_path():
    return os.getcwd()
```

Automated tools can help:

```bash
# autoflake removes unused imports
autoflake --remove-all-unused-imports --in-place src/drift/core/parser.py
```

### Trailing Whitespace (W291)

```bash
# Auto-fix with black
black src/drift/

# Or manually in your editor (most editors can trim on save)
```

### Missing Blank Lines (E302, E305)

```python
# Before - flake8: expected 2 blank lines, found 1
class DriftDetector:
    pass
class Parser:
    pass

# After - proper spacing
class DriftDetector:
    pass


class Parser:
    pass
```

Black auto-fixes these:

```bash
black src/drift/
```

## Workflow: Fixing Linting Errors

### 1. Run Check Script

```bash
./lint.sh
```

### 2. Auto-Fix What's Possible

```bash
./lint.sh --fix
```

This automatically fixes:
- Import ordering (isort)
- Code formatting (black)
- Line length issues (black wraps lines)
- Trailing whitespace (black)
- Blank line spacing (black)

### 3. Fix Remaining Issues Manually

After auto-fix, check what's left:

```bash
./lint.sh
```

Manually fix:
- Type hints (mypy errors)
- Unused imports (if autoflake not run)
- Logical issues (like undefined names)

### 4. Verify All Pass

```bash
./lint.sh
```

Should see no errors before committing.

## How to Configure Linters in Your Editor

### VS Code

Add to `.vscode/settings.json`:

```json
{
  "python.linting.enabled": true,
  "python.linting.flake8Enabled": true,
  "python.linting.flake8Args": ["--max-line-length=100"],
  "python.formatting.provider": "black",
  "python.formatting.blackArgs": ["--line-length=100"],
  "[python]": {
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.organizeImports": true
    }
  }
}
```

### PyCharm

1. Settings → Tools → File Watchers
2. Add watcher for Black
3. Add watcher for isort
4. Configure mypy as external tool

## How to Interpret Linting Output

### flake8 Output

```
src/drift/core/parser.py:45:80: E501 line too long (103 > 100 characters)
```

Format: `file:line:column: code description`

- E501: Error code (look up in flake8 docs)
- Line 45, column 80: Where the issue is

### mypy Output

```
src/drift/core/parser.py:23: error: Function is missing a return type annotation
```

- Line 23: Where the issue is
- Clear description of what's missing

### black Output

```
would reformat src/drift/core/parser.py
```

- Tells you which files would change
- Use `--diff` to see exact changes before applying

## Common Type Hint Patterns

### Function with Multiple Return Types

```python
from typing import Union

def get_config(as_dict: bool = False) -> Union[Config, dict]:
    """Get configuration."""
    if as_dict:
        return {"key": "value"}
    return Config()
```

### Generator Functions

```python
from typing import Iterator

def iter_messages(log_path: str) -> Iterator[dict]:
    """Iterate messages in log file."""
    with open(log_path) as f:
        for line in f:
            yield json.loads(line)
```

### Type Aliases

```python
from typing import TypeAlias

DriftResults: TypeAlias = dict[str, list[str]]

def analyze(log: str) -> DriftResults:
    """Analyze log for drift."""
    return {"incomplete_work": ["instance1"]}
```

## How to Handle Third-Party Type Issues

When mypy complains about missing stubs for third-party libraries:

### Option 1: Install Type Stubs

```bash
pip install types-boto3 types-click
```

### Option 2: Add to mypy Config

In `pyproject.toml`:

```toml
[tool.mypy]
ignore_missing_imports = true
```

Or per-import:

```python
import some_untyped_library  # type: ignore
```

## Pre-Commit Checklist

Before creating a commit:

1. Run `./lint.sh --fix` to auto-fix what's possible
2. Run `./lint.sh` to check for remaining issues
3. Fix any remaining manual issues
4. Verify clean: `./lint.sh` should show no errors

This ensures code quality and prevents failed CI checks.

## Troubleshooting

### Black and flake8 Disagree

Some conflicts (like E203) are configured to be ignored in flake8 config. Check `pyproject.toml` for ignored rules.

### isort Breaks Import Groups

Use `--profile=black` to ensure isort is compatible with black:

```bash
isort . --profile=black
```

### mypy False Positives

Sometimes mypy gets confused. Use `# type: ignore` sparingly:

```python
result = complex_function()  # type: ignore[return-value]
```

Better: Fix the type hint to be accurate.

### Linters Run Slow

Run on specific files during development:

```bash
black src/drift/core/parser.py
flake8 src/drift/core/parser.py
mypy src/drift/core/parser.py
```

Run full suite before committing.
