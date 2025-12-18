# Quality & Development

## Testing
- **Command**: Always use `./test.sh` to run tests.
- **Requirement**: Maintain 90% coverage (enforced by pytest).
- **Strategy**: Write tests first (TDD), use fixtures, mock external calls.

## Linting
- **Command**: Always use `./lint.sh` for linting.
- **Auto-fix**: Use `./lint.sh --fix` to auto-format.
- **Standards**: Defined in `pyproject.toml` (black, flake8, isort, mypy).
