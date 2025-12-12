---
name: python-imports
description: Import location, ordering, and style requirements for Python files
path: "**/*.py"
---

# Python Import Standards

## Import Location

**MUST**: All imports at the top of the file, immediately after module docstring.

**MUST NOT**: Use inline imports except within `if TYPE_CHECKING:` blocks.

## Import Order

**MUST**: Follow this order with blank lines between groups:
1. Standard library imports
2. Third-party imports
3. Local application imports

**MUST**: Within each group, organize as follows:
1. `import x` statements first
2. `from x import y` statements second
3. Alphabetically within each subgroup

## Import Style

**MUST**: Prefer absolute imports over relative imports.

**MUST NOT**: Use wildcard imports (`from module import *`).

**MUST NOT**: Keep unused imports in the code.
