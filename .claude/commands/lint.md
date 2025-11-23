---
description: Run linters and formatters
---

Run code quality checks using the lint.sh script.

```bash
./lint.sh --embedded $ARGUMENTS
```

Supported arguments:
- `--fix` - Automatically fix issues where possible (black, isort)

Linters run:
- flake8 (code quality)
- black (formatting)
- isort (import sorting)
- mypy (type checking)

Example usage:
- `/lint` - Check code quality
- `/lint --fix` - Auto-fix formatting issues
