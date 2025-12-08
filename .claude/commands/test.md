---
description: Run pytest tests
argument-hint: [--coverage]
---

Run the test suite using the test.sh script.

```bash
./test.sh --embedded $ARGUMENTS
```

Supported arguments:
- `--coverage` - Run with coverage report (requires 90% minimum coverage)

Example usage:
- `/test` - Run all tests
- `/test --coverage` - Run all tests with coverage report
