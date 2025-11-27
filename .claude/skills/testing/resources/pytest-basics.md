# Pytest Basics

Quick reference for pytest fundamentals and patterns used in Drift.

## Test Structure

```python
def test_function_name_scenario():
    """Test that function_name does X when Y."""
    # Arrange
    input_data = {"key": "value"}

    # Act
    result = function_under_test(input_data)

    # Assert
    assert result == expected_value
```

## Common Pytest Features

### Fixtures

```python
import pytest

@pytest.fixture
def sample_conversation():
    """Provide a sample conversation log for tests."""
    return {
        "messages": [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"}
        ]
    }

def test_parser_with_fixture(sample_conversation):
    result = parse_conversation(sample_conversation)
    assert len(result["messages"]) == 2
```

### Parametrize

```python
@pytest.mark.parametrize("input,expected", [
    ("test.json", True),
    ("test.yaml", False),
    ("test.txt", False),
])
def test_is_json_file(input, expected):
    assert is_json_file(input) == expected
```

### Mocking

```python
from unittest.mock import Mock, patch

def test_with_mock():
    mock_client = Mock()
    mock_client.invoke_model.return_value = {"body": "response"}

    result = analyze_with_llm(mock_client, "prompt")
    assert result == "response"
```

### Exception Testing

```python
def test_raises_error():
    with pytest.raises(ValueError, match="Invalid input"):
        parse_invalid_data("bad data")
```

## Running Tests

```bash
# All tests
pytest

# Specific file
pytest tests/unit/test_parser.py

# Specific test
pytest tests/unit/test_parser.py::test_parse_valid_json

# With verbose output
pytest -v

# With coverage
pytest --cov=drift --cov-report=term-missing
```
