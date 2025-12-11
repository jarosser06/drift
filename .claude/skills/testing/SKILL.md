---
name: testing
description: Expert in creating comprehensive pytest test suites for Drift project with strict 90%+ coverage requirements. Specializes in unit tests, integration tests, mocking external APIs (Anthropic, AWS Bedrock), and coverage validation using pytest-cov. Use when writing tests, test fixtures, validating test coverage, or implementing mocking strategies for external dependencies.
---

# Testing Skill

Learn how to create comprehensive test suites for the Drift CLI tool.

## How to Mock AWS Bedrock

Use `boto3` mocking for AWS Bedrock API calls:

```python
import boto3
import json
from moto import mock_aws

@mock_aws
def test_llm_analysis():
    """Test LLM analysis with mocked Bedrock."""
    # Setup mock Bedrock client
    client = boto3.client('bedrock-runtime', region_name='us-east-1')

    # Your test code that calls Bedrock
    from drift.core.detector import DriftDetector
    detector = DriftDetector(provider='bedrock')
    result = detector.analyze(conversation)

    assert result is not None
```

### Mocking Bedrock Responses

```python
from unittest.mock import patch, MagicMock

def test_drift_detection_with_mock_response():
    """Test drift detection with mocked LLM response."""
    mock_response = {
        'body': MagicMock(read=lambda: json.dumps({
            'completion': 'Detected incomplete work in lines 45-60'
        }).encode())
    }

    with patch('boto3.client') as mock_client:
        mock_client.return_value.invoke_model.return_value = mock_response

        detector = DriftDetector(provider='bedrock')
        result = detector.detect_incomplete_work(conversation)

        assert 'incomplete work' in result[0].lower()
```

## How to Test CLI Commands

Test CLI using `click.testing.CliRunner`:

```python
from click.testing import CliRunner
from drift.cli import cli

def test_cli_analyze_command():
    """Test analyze command with valid log file."""
    runner = CliRunner()

    with runner.isolated_filesystem():
        # Create test file
        with open('test.json', 'w') as f:
            f.write('{"messages": []}')

        result = runner.invoke(cli, ['analyze', 'test.json'])

        assert result.exit_code == 0
        assert 'Analyzing' in result.output
```

### Testing CLI Options

```python
def test_cli_with_drift_type_option():
    """Test CLI with --drift-type option."""
    runner = CliRunner()

    result = runner.invoke(cli, [
        'analyze',
        'test.json',
        '--drift-type', 'incomplete_work'
    ])

    assert result.exit_code == 0
```

### Testing CLI Error Handling

```python
def test_cli_with_nonexistent_file():
    """Test CLI error handling for missing file."""
    runner = CliRunner()

    result = runner.invoke(cli, ['analyze', 'nonexistent.json'])

    assert result.exit_code != 0
    assert 'not found' in result.output.lower()
```

## How to Create Test Fixtures

Create reusable fixtures in `conftest.py`:

```python
import pytest
import json

@pytest.fixture
def sample_conversation():
    """Sample conversation log for testing."""
    return {
        'messages': [
            {'role': 'user', 'content': 'Hello'},
            {'role': 'assistant', 'content': 'Hi there'}
        ],
        'metadata': {'session_id': '123'}
    }

@pytest.fixture
def conversation_with_drift():
    """Conversation log containing drift patterns."""
    return {
        'messages': [
            {'role': 'user', 'content': 'Build a login system'},
            {'role': 'assistant', 'content': 'Starting with authentication...'},
            {'role': 'user', 'content': 'Is it done?'},
            {'role': 'assistant', 'content': 'Here are my recommendations for future work'}
        ]
    }

@pytest.fixture
def mock_bedrock_response():
    """Mock Bedrock API response."""
    return {
        'body': MagicMock(read=lambda: json.dumps({
            'completion': 'Analysis complete'
        }).encode())
    }
```

### File-based Fixtures

```python
@pytest.fixture
def temp_log_file(tmp_path):
    """Create temporary conversation log file."""
    log_file = tmp_path / "test_conversation.json"
    log_file.write_text(json.dumps({
        'messages': [{'role': 'user', 'content': 'test'}]
    }))
    return log_file
```

## Key Testing Areas for Drift

### 1. Conversation Log Parsing

```python
def test_parse_valid_json_log(sample_conversation, tmp_path):
    """Test parsing valid JSON conversation log."""
    log_file = tmp_path / "log.json"
    log_file.write_text(json.dumps(sample_conversation))

    from drift.core.parser import parse_conversation
    result = parse_conversation(str(log_file))

    assert result['messages'] == sample_conversation['messages']
    assert 'metadata' in result

def test_parse_malformed_json_raises_error(tmp_path):
    """Test that malformed JSON raises appropriate error."""
    log_file = tmp_path / "bad.json"
    log_file.write_text('{invalid json')

    from drift.core.parser import parse_conversation

    with pytest.raises(ValueError, match='Invalid JSON'):
        parse_conversation(str(log_file))
```

### 2. Drift Detection

```python
def test_detect_incomplete_work(conversation_with_drift):
    """Test detection of incomplete work pattern."""
    from drift.core.detector import DriftDetector

    detector = DriftDetector()
    results = detector.detect_drift(
        conversation_with_drift,
        drift_type='incomplete_work'
    )

    assert len(results) > 0
    assert any('incomplete' in r.lower() for r in results)

def test_multi_pass_analysis(sample_conversation):
    """Test multi-pass analysis for all drift types."""
    from drift.core.detector import DriftDetector

    detector = DriftDetector()
    results = detector.analyze_all_types(sample_conversation)

    assert isinstance(results, dict)
    assert 'drift_types' in results
    assert 'instances' in results
```

### 3. LLM Integration

```python
@mock_aws
def test_llm_api_call_construction():
    """Test LLM API call is constructed correctly."""
    from drift.providers.bedrock import BedrockProvider

    provider = BedrockProvider(model_id='anthropic.claude-v2')

    # Mock the client
    with patch.object(provider.client, 'invoke_model') as mock_invoke:
        mock_invoke.return_value = {'body': MagicMock()}

        provider.analyze('test prompt')

        # Verify API call
        mock_invoke.assert_called_once()
        call_args = mock_invoke.call_args
        assert 'modelId' in call_args.kwargs
        assert call_args.kwargs['modelId'] == 'anthropic.claude-v2'

def test_llm_response_parsing(mock_bedrock_response):
    """Test parsing of LLM API response."""
    from drift.providers.bedrock import BedrockProvider

    provider = BedrockProvider()
    result = provider.parse_response(mock_bedrock_response)

    assert result == 'Analysis complete'
```

### 4. Output Generation

```python
def test_linter_style_output_format():
    """Test output formatted like a linter."""
    from drift.cli import format_output

    results = [{
        'file': 'conversation.json',
        'line': 45,
        'type': 'incomplete_work',
        'message': 'Task left incomplete'
    }]

    output = format_output(results, style='linter')

    assert 'conversation.json:45' in output
    assert 'incomplete_work' in output

def test_json_output_mode():
    """Test JSON output format."""
    from drift.cli import format_output

    results = [{'type': 'incomplete_work', 'count': 3}]
    output = format_output(results, format='json')

    parsed = json.loads(output)
    assert parsed[0]['type'] == 'incomplete_work'
```

## How to Run Tests

```bash
# Run all tests
./test.sh

# Run with coverage report
./test.sh --coverage

# Run specific test file
pytest tests/unit/test_parser.py -v

# Run specific test function
pytest tests/unit/test_parser.py::test_parse_conversation -v

# Run tests matching pattern
pytest -k "test_parse" -v

# Run with output (don't capture stdout)
pytest -s tests/unit/test_parser.py

# Run with debugger on failure
pytest --pdb tests/unit/test_parser.py
```

## How to Check Coverage

```bash
# Generate coverage report
pytest --cov=src/drift --cov-report=html tests/

# View HTML report
open htmlcov/index.html

# Show missing lines
pytest --cov=src/drift --cov-report=term-missing tests/
```

### Analyzing Coverage Gaps

```python
# Check which lines aren't covered
pytest --cov=src/drift --cov-report=term-missing tests/

# Output shows:
# Name                Stmts   Miss  Cover   Missing
# src/drift/parser.py    45      3    93%   67-69
```

Then write tests for the missing lines (67-69 in this example).

## How to Use Parametrize for Multiple Test Cases

Test the same logic with different inputs:

```python
import pytest

@pytest.mark.parametrize('input,expected', [
    ('valid.json', True),
    ('invalid.json', False),
    ('missing.json', False),
])
def test_validate_log_file(input, expected):
    """Test log file validation with various inputs."""
    from drift.validators import validate_log_file

    result = validate_log_file(input)
    assert result == expected

@pytest.mark.parametrize('drift_type,expected_count', [
    ('incomplete_work', 2),
    ('specification_adherence', 1),
    ('context_loss', 0),
])
def test_drift_detection_counts(drift_type, expected_count, conversation_with_drift):
    """Test drift detection counts for different types."""
    from drift.core.detector import DriftDetector

    detector = DriftDetector()
    results = detector.detect_drift(conversation_with_drift, drift_type)

    assert len(results) == expected_count
```

## How to Test Error Handling

```python
def test_parser_handles_missing_messages_key():
    """Test parser handles logs missing 'messages' key."""
    from drift.core.parser import parse_conversation

    invalid_log = {'metadata': {}}  # Missing 'messages'

    with pytest.raises(ValueError, match='missing.*messages'):
        parse_conversation(invalid_log)

def test_detector_handles_api_timeout():
    """Test detector handles LLM API timeouts gracefully."""
    from drift.core.detector import DriftDetector
    from botocore.exceptions import ReadTimeoutError

    detector = DriftDetector()

    with patch.object(detector.client, 'invoke_model') as mock:
        mock.side_effect = ReadTimeoutError(endpoint_url='test')

        with pytest.raises(RuntimeError, match='timeout'):
            detector.analyze(conversation)
```

## Common Patterns

### Testing with Temporary Files

```python
def test_write_output_to_file(tmp_path):
    """Test writing analysis output to file."""
    from drift.cli import write_output

    output_file = tmp_path / "output.txt"
    write_output("test content", str(output_file))

    assert output_file.exists()
    assert output_file.read_text() == "test content"
```

### Testing Configuration Loading

```python
def test_load_config_from_yaml(tmp_path):
    """Test loading configuration from YAML file."""
    config_file = tmp_path / ".drift.yaml"
    config_file.write_text("""
    drift_types:
      - incomplete_work
      - specification_adherence
    """)

    from drift.config import load_config
    config = load_config(str(config_file))

    assert 'drift_types' in config
    assert len(config['drift_types']) == 2
```

### Testing with Environment Variables

```python
def test_uses_api_key_from_env(monkeypatch):
    """Test that API key is read from environment variable."""
    monkeypatch.setenv('ANTHROPIC_API_KEY', 'test-key-123')

    from drift.providers.anthropic import AnthropicProvider
    provider = AnthropicProvider()

    assert provider.api_key == 'test-key-123'
```

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
