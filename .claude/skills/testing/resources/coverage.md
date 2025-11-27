# Coverage Requirements

Guidelines for measuring and achieving test coverage in Drift.

## Coverage Standards

- **Minimum:** 90% code coverage
- **Target:** 95%+ for core logic (detector, parser, formatter)
- **Acceptable:** 85%+ for CLI and utility code

## Running Coverage

```bash
# Run tests with coverage
./test.sh --coverage

# Or directly with pytest
pytest --cov=drift --cov-report=term-missing --cov-report=html

# View HTML report
open htmlcov/index.html
```

## Coverage Report Output

```
Name                        Stmts   Miss  Cover   Missing
---------------------------------------------------------
drift/__init__.py               2      0   100%
drift/cli.py                   45      3    93%   67-69
drift/core/detector.py        120      8    93%   45, 89-95
drift/core/parser.py           67      2    97%   34, 56
drift/utils/config.py          34      5    85%   12-16
---------------------------------------------------------
TOTAL                         268     18    93%
```

## What to Cover

### Must Cover (100%)
- Core business logic (drift detection algorithms)
- Data parsing and validation
- Error handling paths
- Output formatting

### Should Cover (90%+)
- CLI argument parsing
- Configuration loading
- Utility functions
- API client interactions (with mocks)

### Can Skip
- `if __name__ == "__main__"` blocks
- Defensive assertions that can't be triggered
- Logger setup code

## Improving Coverage

### Find Uncovered Code

```bash
# Show line numbers of uncovered code
pytest --cov=drift --cov-report=term-missing
```

### Add Missing Tests

```python
# Example: covering error path
def test_parser_handles_invalid_json():
    """Cover error handling for malformed JSON."""
    with pytest.raises(ValueError, match="Invalid JSON"):
        parse_conversation("not valid json")
```

### Use Branch Coverage

```bash
# Check branch coverage (if/else both paths)
pytest --cov=drift --cov-branch --cov-report=term-missing
```

## Coverage Best Practices

1. **Write tests for behavior, not coverage**
   - Don't just hit lines to reach 90%
   - Test actual functionality and edge cases
   - Coverage is a metric, not the goal

2. **Focus on critical paths first**
   - Drift detection logic
   - Parsing and validation
   - Error handling

3. **Use coverage to find gaps**
   - Look for missing edge cases
   - Identify untested error paths
   - Find dead code to remove

4. **Don't chase 100%**
   - 90% is the standard
   - Some code doesn't need tests (boilerplate, obvious)
   - Focus effort on high-value tests

## Coverage in CI/CD

The coverage requirement is enforced in CI:

```bash
# Test script checks minimum coverage
./test.sh --coverage
# Fails if coverage < 90%
```
