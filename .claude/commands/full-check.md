---
description: Run full validation (tests + linting)
---

Run comprehensive validation by executing both test and lint checks.

```bash
./lint.sh --embedded
./test.sh --embedded --coverage
```

This command:
1. Runs all linters (flake8, black, isort, mypy)
2. Runs all tests with coverage check (90% minimum)

Use this before creating PRs to ensure code quality.
