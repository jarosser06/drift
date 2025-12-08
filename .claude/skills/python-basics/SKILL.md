---
name: python-basics
description: Expert in Python 3.10+ fundamentals and best practices for the Drift project including import ordering (isort), code organization, and PEP 8 conventions. Use when writing or reviewing Python code.
---

# Python Basics Skill

Expert in Python fundamentals, best practices, and code organization for the Drift project.

## Core Responsibilities

- Enforce Python best practices
- Ensure proper import organization
- Maintain PEP 8 compliance
- Guide proper code structure
- Prevent common Python pitfalls

## Import Standards

### CRITICAL RULE: ALL IMPORTS MUST BE AT THE TOP OF THE FILE

**NEVER use inline imports.** All imports must be placed at the top of the file, immediately after the module docstring.

### Import Order

Imports must follow this strict order:

1. **Standard library imports**
2. **Related third-party imports**
3. **Local application/library imports**

Each group should be separated by a blank line.

### Example: Correct Import Structure

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

### Example: INCORRECT Import Structure

```python
"""Module for analyzing conversation logs."""

import json
import click  # Third-party mixed with stdlib

def analyze_file(path: str):
    from drift.core.parser import parse_conversation  # WRONG: Inline import
    return parse_conversation(path)

import os  # WRONG: Import not at top
```

## Why No Inline Imports?

**Inline imports are prohibited because:**

1. **Readability:** Dependencies should be visible at the top of the file
2. **Maintainability:** Easier to track and manage dependencies
3. **Performance:** Module loading happens once, not repeatedly
4. **Static Analysis:** Tools can analyze dependencies properly
5. **PEP 8 Compliance:** Follows Python style guide recommendations

### The ONLY Exception

Inline imports are acceptable ONLY for:
- Avoiding circular import issues (very rare)
- Type checking imports within `TYPE_CHECKING` blocks

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from drift.core.detector import DriftDetector  # OK: Type checking only
```

## Import Organization

### Grouping Imports

Within each section, organize imports:

1. `import x` statements first
2. `from x import y` statements second
3. Alphabetically within each group

```python
# Good
import json
import os
from pathlib import Path
from typing import Any, Dict

# Bad
from typing import Any, Dict
import os
from pathlib import Path
import json
```

### Relative vs Absolute Imports

**Prefer absolute imports:**

```python
# Good
from drift.core.parser import parse_conversation
from drift.utils.config import load_config

# Avoid relative imports unless necessary
from ..core.parser import parse_conversation  # Only when needed
```

## Code Organization

### Module Structure

1. Module docstring
2. Imports (standard → third-party → local)
3. Constants and configuration
4. Class definitions
5. Function definitions
6. `if __name__ == "__main__":` block (if applicable)

```python
"""Module for drift detection."""

# Imports
import json
from typing import Any

from drift.core.parser import parse_conversation

# Constants
DEFAULT_MODEL = "anthropic.claude-v2"
MAX_RETRIES = 3

# Classes
class DriftDetector:
    """Detects drift patterns."""
    pass

# Functions
def detect_drift(conversation: dict) -> list[str]:
    """Detect drift in conversation."""
    pass

# Main execution
if __name__ == "__main__":
    main()
```

## PEP 8 Essentials

### Line Length
- Maximum 100 characters (project standard)
- Break long lines logically

### Naming Conventions
- `snake_case` for functions and variables
- `PascalCase` for classes
- `UPPER_CASE` for constants
- `_leading_underscore` for private/internal

### Spacing
- 2 blank lines between top-level definitions
- 1 blank line between method definitions
- No trailing whitespace

## Common Anti-Patterns to Avoid

### 1. Inline Imports (CRITICAL)

```python
# WRONG
def process_data(data):
    import json  # NO! Import at top
    return json.loads(data)

# RIGHT
import json

def process_data(data):
    return json.loads(data)
```

### 2. Wildcard Imports

```python
# WRONG
from drift.core import *  # Don't use *

# RIGHT
from drift.core import DriftDetector, parse_conversation
```

### 3. Unused Imports

```python
# WRONG
import json
import os
from typing import Any  # Unused imports

def hello():
    print("hello")

# RIGHT
def hello():
    print("hello")
```

### 4. Circular Imports

If you encounter circular imports, refactor:
- Move shared code to a separate module
- Use dependency injection
- Import at function level ONLY as last resort

## Type Hints

Use type hints on all public functions:

```python
from typing import Optional

def detect_drift(
    conversation: dict,
    drift_type: str,
    config: Optional[dict] = None
) -> list[str]:
    """Detect drift in conversation."""
    pass
```

## Error Handling

Be specific with exceptions:

```python
# Good
try:
    data = json.load(f)
except json.JSONDecodeError as e:
    raise ValueError(f"Invalid JSON: {e}")
except FileNotFoundError:
    raise FileNotFoundError(f"File not found: {path}")

# Bad
try:
    data = json.load(f)
except Exception as e:  # Too broad
    raise
```

## String Formatting

Prefer f-strings:

```python
# Good
message = f"Found {count} drift instances in {file_path}"

# Avoid
message = "Found {} drift instances in {}".format(count, file_path)
message = "Found " + str(count) + " drift instances"
```

## Review Checklist

When reviewing or writing Python code:

- [ ] All imports at the top of the file
- [ ] Imports organized in correct order (stdlib → third-party → local)
- [ ] No inline imports (except TYPE_CHECKING)
- [ ] No wildcard imports
- [ ] No unused imports
- [ ] Type hints on public functions
- [ ] PEP 8 naming conventions followed
- [ ] Line length ≤ 100 characters
- [ ] Proper spacing and blank lines
- [ ] Specific exception handling

