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
