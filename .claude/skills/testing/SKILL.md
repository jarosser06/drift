---
name: testing
description: Expert in creating comprehensive pytest test suites for Drift with 90%+ coverage. Use when writing tests, test fixtures, or validating test coverage.
---

# Testing Skill

Expert in creating comprehensive test suites for the Drift CLI tool.

## Core Responsibilities

- Write pytest tests with 90% minimum coverage
- Create unit tests for all core functionality
- Mock AWS Bedrock API calls appropriately
- Test CLI argument parsing and validation
- Test conversation log parsing logic
- Test drift detection algorithms
- Ensure edge cases are covered

## Testing Standards

### Coverage Requirements
- **Minimum:** 90% code coverage
- **Target:** 95%+ for core logic
- Run with: `./test.sh --coverage`

### Test Organization
```
tests/
├── unit/           # Unit tests for individual modules
├── integration/    # Integration tests for workflows
└── fixtures/       # Test data (sample conversation logs, configs)
```

### Mocking AWS Bedrock

Use `boto3` mocking for AWS Bedrock API calls:

```python
import boto3
from moto import mock_bedrock_runtime

@mock_bedrock_runtime
def test_llm_analysis():
    # Setup mock
    client = boto3.client('bedrock-runtime', region_name='us-east-1')
    # Test your code
    ...
```

### CLI Testing

Test CLI using `click.testing.CliRunner`:

```python
from click.testing import CliRunner
from drift.cli import main

def test_cli_basic():
    runner = CliRunner()
    result = runner.invoke(main, ['analyze', 'test.json'])
    assert result.exit_code == 0
```

### Test Fixtures

Create reusable fixtures for:
- Sample conversation logs
- Mock LLM responses
- Configuration files
- Expected drift detection outputs

## Key Testing Areas for Drift

1. **Conversation Log Parsing**
   - Valid JSON parsing
   - Handle malformed logs
   - Extract messages correctly
   - Handle different log formats

2. **Drift Detection**
   - Each drift type detection logic
   - Multi-pass analysis workflow
   - Signal extraction
   - Output formatting

3. **LLM Integration**
   - API call construction
   - Response parsing
   - Error handling
   - Rate limiting

4. **Output Generation**
   - Linter-style output format
   - Summary statistics
   - Actionable recommendations
   - JSON output mode

## Test Naming Convention

```python
def test_<module>_<function>_<scenario>():
    """Test that <function> <expected behavior> when <scenario>."""
```

Example:
```python
def test_parser_parse_conversation_with_invalid_json():
    """Test that parse_conversation raises ValueError when given invalid JSON."""
```

## Running Tests

- All tests: `./test.sh`
- With coverage: `./test.sh --coverage`
- Specific file: `pytest tests/unit/test_parser.py -v`
- Specific test: `pytest tests/unit/test_parser.py::test_parse_conversation -v`

## Resources

### 📖 [Pytest Basics](resources/pytest-basics.md)
Quick reference for pytest fundamentals including fixtures, parametrize, and mocking.

**Use when:** Writing new tests or looking up pytest syntax.

### 📖 [Mocking AWS Bedrock](resources/mocking-aws.md)
Patterns for mocking AWS Bedrock API calls in tests.

**Use when:** Testing LLM integration code or API interactions.

### 📖 [Coverage Requirements](resources/coverage.md)
Guidelines for measuring and achieving 90%+ test coverage.

**Use when:** Checking coverage reports or improving test coverage.
