# Drift Testing Documentation

## Overview

Comprehensive test suite for the drift project, designed to achieve 90%+ code coverage.

## Test Structure

```
tests/
├── conftest.py              # Pytest configuration and shared fixtures
├── fixtures/                # Sample data files
│   ├── sample_conversation.jsonl
│   ├── sample_bedrock_response.json
│   └── sample_config.yaml
├── unit/                    # Unit tests (89% coverage)
│   ├── test_config_models.py      # Pydantic model validation tests
│   ├── test_config_loader.py      # Config loading and merging tests
│   ├── test_providers.py          # AWS Bedrock provider tests (mocked)
│   ├── test_agents.py             # Claude Code loader tests
│   ├── test_analyzer.py           # Core drift analyzer tests
│   ├── test_formatters.py         # Markdown/JSON output formatters
│   └── test_temp.py               # Temporary directory management
└── integration/             # Integration tests
    ├── test_cli.py                # CLI command testing with Typer CliRunner
    └── test_end_to_end.py         # Full workflow tests

```

## Running Tests

### Install Dependencies

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install package with dev dependencies
pip install -e ".[dev]"
```

### Run All Tests

```bash
pytest tests/
```

### Run with Coverage

```bash
# Generate coverage report
pytest tests/ --cov=src/drift --cov-report=term-missing --cov-report=html

# View HTML report
open htmlcov/index.html
```

### Run Specific Test Suites

```bash
# Unit tests only
pytest tests/unit/

# Integration tests only
pytest tests/integration/

# Specific test file
pytest tests/unit/test_config_models.py

# Specific test
pytest tests/unit/test_config_models.py::TestModelConfig::test_valid_model_config
```

## Coverage Summary

### Current Coverage: 89%

**Core Modules (90-100% coverage):**
- `config/models.py` - 100% - Pydantic model validation
- `config/loader.py` - 100% - Configuration loading and merging
- `agents/base.py` - 100% - Base agent loader interface
- `agents/claude_code.py` - 100% - Claude Code conversation loader
- `core/types.py` - 100% - Data models
- `providers/base.py` - 100% - Base provider interface
- `providers/bedrock.py` - 93% - AWS Bedrock integration
- `core/analyzer.py` - 95% - Main drift analysis engine
- `utils/temp.py` - 100% - Temporary file management
- `cli/output/formatter.py` - 100% - Output formatter base
- `cli/output/json.py` - 100% - JSON formatter
- `cli/output/markdown.py` - 97% - Markdown formatter

**Lower Coverage (requires integration testing):**
- `cli/commands/analyze.py` - 13% - CLI command (integration tests needed)
- `cli/main.py` - 64% - CLI entry point

## Test Fixtures

### Shared Fixtures (conftest.py)

- `temp_dir` - Temporary directory for file-based tests
- `sample_model_config` - Model configuration for testing
- `sample_learning_type` - Drift learning type configuration
- `sample_agent_config` - Agent tool configuration
- `sample_drift_config` - Complete drift configuration
- `sample_turn` - Conversation turn
- `sample_conversation` - Complete conversation with turns
- `sample_learning` - Drift learning instance
- `mock_bedrock_response` - Mocked AWS Bedrock API response
- `sample_conversation_jsonl` - Sample JSONL conversation file
- `sample_config_yaml` - Sample YAML configuration file
- `claude_code_project_dir` - Mock Claude Code project structure

### Sample Data Files

- `sample_conversation.jsonl` - Example conversation with drift
- `sample_bedrock_response.json` - Example Bedrock API response
- `sample_config.yaml` - Example configuration file

## Testing Strategy

### Unit Tests

1. **Config Models** (`test_config_models.py`)
   - Pydantic validation (temperature, days, paths)
   - Enum values
   - Field defaults
   - Model methods

2. **Config Loader** (`test_config_loader.py`)
   - YAML file loading
   - Deep merging (default → global → project)
   - Path expansion (~/)
   - Validation errors
   - Config priority testing

3. **Providers** (`test_providers.py`)
   - Bedrock client initialization
   - is_available() checks
   - generate() with mocked boto3
   - Error handling (credentials, API errors, malformed responses)
   - System prompts and additional parameters

4. **Agents** (`test_agents.py`)
   - Conversation file discovery
   - JSONL parsing
   - Time-based filtering
   - Turn extraction
   - Timestamp parsing
   - Error handling (malformed JSON, incomplete turns)

5. **Analyzer** (`test_analyzer.py`)
   - Provider initialization
   - Agent loader initialization
   - Conversation formatting
   - Prompt building
   - LLM response parsing
   - Multi-pass analysis
   - Summary generation
   - Error recovery

6. **Formatters** (`test_formatters.py`)
   - Markdown output formatting
   - JSON output formatting
   - Unicode handling
   - Timestamp serialization
   - Empty results
   - Complex learnings

7. **Temp Manager** (`test_temp.py`)
   - Directory creation
   - Pass result saving/loading
   - Metadata storage
   - Cleanup operations
   - Multiple conversations

### Integration Tests

1. **CLI Tests** (`test_cli.py`)
   - Command-line argument parsing
   - Option validation
   - Error handling
   - Exit codes (0=success, 2=drift found)
   - Format selection (markdown/json)

2. **End-to-End Tests** (`test_end_to_end.py`)
   - Full analysis workflow
   - Config loading with overrides
   - Multiple conversation analysis
   - Output formatting integration
   - Temp directory management
   - Error recovery

## Mocking Strategy

### External Services

- **AWS Bedrock**: Mocked using `unittest.mock.patch` on `boto3.client`
- **File System**: Uses `pytest`'s `temp_dir` fixture for isolated testing
- **Time**: Uses `datetime.now()` with time-shifted test data

### Key Mocking Patterns

```python
# Mock Bedrock provider
@patch("drift.providers.bedrock.boto3")
def test_provider(mock_boto3):
    mock_client = MagicMock()
    mock_client.invoke_model.return_value = {...}
    mock_boto3.client.return_value = mock_client
    # Test code

# Mock file timestamps
import os
import time
old_timestamp = time.time() - (10 * 24 * 60 * 60)  # 10 days ago
os.utime(file_path, (old_timestamp, old_timestamp))
```

## Test Data

### Conversation Format (JSONL)

```json
{"type": "user", "content": "...", "timestamp": "2024-01-01T10:00:00Z"}
{"type": "assistant", "content": "...", "timestamp": "2024-01-01T10:01:00Z", "id": "turn-1"}
```

### Expected Bedrock Response

```json
{
  "content": [{
    "text": "[{\"turn_number\": 1, \"ai_action\": \"...\", \"user_intent\": \"...\", \"resolved\": true, \"still_needs_action\": true, \"context\": \"...\"}]"
  }]
}
```

## Common Test Patterns

### Testing Configuration Merging

```python
def test_config_priority():
    # Test: project > global > default
    # Verify specific fields from each level
```

### Testing Error Cases

```python
def test_invalid_input():
    with pytest.raises(ValueError) as exc_info:
        # Code that should raise
    assert "expected message" in str(exc_info.value)
```

### Testing Async/Temp Resources

```python
def test_with_cleanup(temp_dir):
    # Test code using temp_dir
    # Cleanup happens automatically
```

## Running Tests in CI/CD

```bash
# Run tests with strict coverage requirement
pytest tests/ --cov=src/drift --cov-fail-under=90

# Generate multiple report formats
pytest tests/ --cov=src/drift \
    --cov-report=term-missing \
    --cov-report=html \
    --cov-report=xml
```

## Troubleshooting

### Import Errors

Ensure the package is installed in editable mode:
```bash
pip install -e .
```

### Coverage Not Updating

Delete coverage data and regenerate:
```bash
rm -rf .coverage htmlcov/
pytest tests/ --cov=src/drift
```

### Mocking Issues

Verify the patch path matches the import path in the code being tested, not where the class is defined.

## Future Improvements

1. **CLI Integration Tests**: Add full CLI tests with actual command invocation
2. **Performance Tests**: Add benchmarks for large conversation analysis
3. **Parallel Testing**: Enable pytest-xdist for faster test execution
4. **Property-Based Testing**: Use Hypothesis for edge case discovery
5. **Contract Tests**: Verify AWS Bedrock API contract assumptions

## Contributing

When adding new features:

1. Write tests first (TDD)
2. Ensure new code has 90%+ coverage
3. Add fixtures for reusable test data
4. Document complex test scenarios
5. Run full test suite before submitting PR

```bash
# Before committing
pytest tests/ --cov=src/drift --cov-fail-under=90
black src/ tests/
isort src/ tests/
flake8 src/ tests/
mypy src/
```
