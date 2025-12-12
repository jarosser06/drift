---
name: test-coverage
description: Minimum coverage thresholds for test files
path: "tests/**/*.py"
---

# Test Coverage Requirements

## Coverage Thresholds

**MUST**: Minimum 90% code coverage for all code.

**MUST**: Target 95%+ coverage for core logic.

## Test Pyramid Ratios

**MUST**: Maintain these test distribution ratios:
- Unit tests: 80-90%
- Integration tests: 10-15%
- End-to-end tests: < 5%

## Validation

**MUST**: Coverage report must be generated before commits.
