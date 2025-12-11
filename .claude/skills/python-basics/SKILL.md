---
name: python-basics
description: Expert in Python 3.10+ fundamentals and best practices for the Drift project including import ordering (isort), code organization, and PEP 8 conventions. Use when writing or reviewing Python code.
---

# Python Basics Skill

Learn how to write clean, well-organized Python code following Drift project conventions.

## How to Organize Imports

When writing Python files, place imports immediately after the module docstring and organize them in three groups:

```python
"""Module for analyzing conversation logs."""

# Standard library imports
import json
import os
from pathlib import Path
from typing import Any, Optional

# Third-party imports
import boto3
import click
from botocore.exceptions import ClientError

# Local imports
from drift.core.parser import parse_conversation
from drift.core.detector import DriftDetector
from drift.utils.config import load_config
```

### Within Each Group

Organize imports consistently:
1. `import x` statements first
2. `from x import y` statements second
3. Alphabetically within each subgroup

```python
# Good organization
import json
import os
from pathlib import Path
from typing import Any, Dict

# Poor organization (mixed order)
from typing import Any, Dict
import os
from pathlib import Path
import json
```

## Why No Inline Imports?

Understanding the reasoning helps you make better architectural decisions:

1. **Readability:** Dependencies should be visible at the top of the file
2. **Maintainability:** Easier to track and manage dependencies
3. **Performance:** Module loading happens once, not repeatedly
4. **Static Analysis:** Tools can analyze dependencies properly
5. **PEP 8 Compliance:** Follows Python style guide recommendations

### The Exception: TYPE_CHECKING Blocks

When you need to avoid circular imports for type hints only:

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from drift.core.detector import DriftDetector  # OK: Type checking only

def process(detector: "DriftDetector") -> None:
    """Process using detector."""
    pass
```

This technique allows forward references without runtime circular dependencies.

## How to Fix Import Issues

When your linter flags import problems:

### Using isort

```bash
# Auto-sort all imports
isort .

# Check what would change
isort --check-only .

# Sort a specific file
isort src/drift/core/parser.py
```

### Manual Fixes

**Problem**: Imports mixed with code

```python
# Before
import json

def process():
    pass

import os  # Wrong location!
```

```python
# After
import json
import os

def process():
    pass
```

**Problem**: Wrong grouping

```python
# Before
import json
import click  # Third-party mixed with stdlib
from drift.core import parser
```

```python
# After
import json

import click

from drift.core import parser
```

## How to Structure Python Modules

Follow this organization pattern:

```python
"""Module for drift detection.

This module provides the core drift detection functionality.
"""

# Imports (organized as shown above)
import json
from typing import Any

from drift.core.parser import parse_conversation

# Constants
DEFAULT_MODEL = "anthropic.claude-v2"
MAX_RETRIES = 3

# Classes
class DriftDetector:
    """Detects drift patterns in conversations."""

    def __init__(self, model: str = DEFAULT_MODEL):
        """Initialize detector."""
        self.model = model

# Functions
def detect_drift(conversation: dict) -> list[str]:
    """Detect drift in conversation."""
    detector = DriftDetector()
    return detector.analyze(conversation)

# Main execution
if __name__ == "__main__":
    main()
```

## How to Handle Circular Imports

When you encounter circular import errors, try these solutions in order:

### 1. Refactor to Remove the Circle (Preferred)

Move shared code to a separate module:

```python
# Before: module_a.py imports module_b.py, module_b.py imports module_a.py

# After: Create module_c.py with shared code
# module_a.py imports module_c.py
# module_b.py imports module_c.py
```

### 2. Use Dependency Injection

Pass dependencies as function parameters instead of importing:

```python
# Instead of importing DriftDetector in multiple places
def analyze_file(path: str, detector: DriftDetector) -> dict:
    """Analyze file using provided detector."""
    return detector.analyze(path)
```

### 3. Import at Function Level (Last Resort)

Only when the above solutions don't work:

```python
def process_with_detector():
    """Process using detector."""
    from drift.core.detector import DriftDetector  # Local import
    detector = DriftDetector()
    return detector.analyze()
```

## How to Add Type Hints

Use this pattern for function signatures:

```python
from typing import Optional

def detect_drift(
    conversation: dict,
    drift_type: str,
    config: Optional[dict] = None
) -> list[str]:
    """Detect drift in conversation.

    -- conversation: Conversation data
    -- drift_type: Type of drift to detect
    -- config: Optional configuration

    Returns list of detected drift patterns.
    """
    pass
```

For optional parameters:

```python
from typing import Optional

def fetch_user(user_id: str, cache: Optional[Cache] = None) -> User:
    """Fetch user by ID with optional caching."""
    if cache:
        return cache.get(user_id)
    return database.fetch(user_id)
```

## How to Handle Errors Effectively

Be specific with exception types:

```python
# Good - specific exceptions
try:
    data = json.load(f)
except json.JSONDecodeError as e:
    logger.error(f"Invalid JSON in {path}: {e}")
    raise ValueError(f"Cannot parse {path}") from e
except FileNotFoundError:
    logger.error(f"File not found: {path}")
    raise

# Avoid - too broad
try:
    data = json.load(f)
except Exception as e:  # Catches too much!
    raise
```

When to catch broad exceptions:
- At application boundaries (CLI entry points)
- When you need to clean up resources regardless of error type
- When logging all errors for debugging

## How to Format Strings

Use f-strings for readability and performance:

```python
# Recommended
message = f"Found {count} drift instances in {file_path}"
details = f"Status: {status}, Time: {elapsed:.2f}s"

# Avoid (harder to read)
message = "Found {} drift instances in {}".format(count, file_path)
message = "Found " + str(count) + " drift instances"
```

## How to Use Black for Formatting

```bash
# Format all files
black .

# Check what would change without modifying
black --check .

# Format specific file
black src/drift/core/parser.py

# See what would change
black --diff src/drift/core/parser.py
```

## Code Review Workflow

When reviewing or writing Python code, work through these steps:

### 1. Check Imports
- Are all imports at the top?
- Are they grouped correctly (stdlib → third-party → local)?
- Any inline imports that should be moved?
- Any wildcard or unused imports?

### 2. Check Type Hints
- Do public functions have type hints?
- Are Optional types used correctly?

### 3. Check Naming
- Functions/variables: snake_case?
- Classes: PascalCase?
- Constants: UPPER_CASE?
- Private identifiers: _leading_underscore?

### 4. Check Formatting
- Lines under 100 characters?
- Proper spacing (2 lines between classes/functions, 1 line between methods)?
- No trailing whitespace?

### 5. Run Auto-formatters
```bash
# Fix all formatting automatically
black .
isort .

# Verify
black --check .
isort --check-only .
```

## Anti-Pattern Examples

### Inline Imports

```python
# Avoid this pattern
def process_data(data):
    import json  # Import should be at top
    return json.loads(data)

# Use this instead
import json

def process_data(data):
    return json.loads(data)
```

### Wildcard Imports

```python
# Avoid - unclear what's being imported
from drift.core import *

# Use explicit imports
from drift.core import DriftDetector, parse_conversation
```

### Unused Imports

```python
# Avoid - these imports aren't used
import json
import os
from typing import Any

def hello():
    print("hello")

# Keep it clean
def hello():
    print("hello")
```

Run `isort` and your linter will catch these automatically.

## Common Patterns

### Optional Configuration

```python
from typing import Optional

def analyze(
    data: dict,
    config: Optional[dict] = None
) -> dict:
    """Analyze data with optional configuration."""
    if config is None:
        config = get_default_config()
    return _analyze_impl(data, config)
```

### Path Handling

```python
from pathlib import Path

def read_config(config_path: str | Path) -> dict:
    """Read configuration from file."""
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config not found: {path}")
    return json.loads(path.read_text())
```

### Context Managers

```python
def process_file(path: str) -> dict:
    """Process file with automatic cleanup."""
    with open(path) as f:
        data = json.load(f)
    # File automatically closed here
    return data
```
