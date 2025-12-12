---
name: python-formatting
description: Line length, naming conventions, spacing, and module structure standards for Python files
path: "**/*.py"
---

# Python Formatting Standards

## Line Length

**MUST**: Maximum line length of 100 characters.

## Naming Conventions

**MUST**: Use `snake_case` for functions and variables.

**MUST**: Use `PascalCase` for classes.

**MUST**: Use `UPPER_CASE` for constants.

**MUST**: Use `_leading_underscore` for private/internal identifiers.

## Spacing

**MUST**: Use 2 blank lines between top-level definitions (classes, functions).

**MUST**: Use 1 blank line between method definitions within a class.

**MUST NOT**: Leave trailing whitespace at the end of lines.

## Module Structure Order

**MUST**: Organize Python modules in this order:
1. Module docstring
2. Imports (standard → third-party → local)
3. Constants and configuration
4. Class definitions
5. Function definitions
6. `if __name__ == "__main__":` block

## Formatting Tooling

**MUST**: Use black for code formatting.

**MUST**: Use isort for import sorting.
