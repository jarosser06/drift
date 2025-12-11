---
name: test-organization
description: Test structure and naming conventions
path: "tests/**/*.py"
---

# Test Organization Requirements

## Directory Structure

**MUST**: Organize tests in this structure:
```
tests/
├── unit/
├── integration/
└── fixtures/
```

## Test Naming Convention

**MUST**: Name test functions following the pattern: `test_<module>_<function>_<scenario>`

## Rationale

Consistent test organization makes it easy to find and run specific test types. Clear naming conventions make test purpose obvious without reading implementation. This structure scales well as the project grows.
