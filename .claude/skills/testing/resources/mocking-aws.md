# Mocking AWS Bedrock

Patterns for mocking AWS Bedrock API calls in tests.

## Using moto for Bedrock Runtime

```python
import boto3
import json
from moto import mock_bedrock_runtime

@mock_bedrock_runtime
def test_llm_analysis():
    """Test LLM analysis with mocked Bedrock."""
    # Create mock client
    client = boto3.client('bedrock-runtime', region_name='us-east-1')

    # Your test code that uses the client
    response = invoke_model(
        client=client,
        model_id="anthropic.claude-v2",
        prompt="Analyze this conversation"
    )

    assert response is not None
```

## Mock Response Structure

```python
from unittest.mock import Mock

def test_with_mock_response():
    """Test with custom mock response."""
    mock_client = Mock()

    # Mock the response structure
    mock_response = {
        'body': type('obj', (), {
            'read': lambda: json.dumps({
                'completion': 'Mocked LLM response',
                'stop_reason': 'end_turn'
            }).encode('utf-8')
        })(),
        'contentType': 'application/json'
    }

    mock_client.invoke_model.return_value = mock_response

    # Test your function
    result = analyze_conversation(mock_client, conversation_log)
    assert 'Mocked LLM response' in result
```

## Fixture for Bedrock Client

```python
import pytest
from unittest.mock import Mock

@pytest.fixture
def mock_bedrock_client():
    """Provide a mocked Bedrock client."""
    client = Mock()
    client.invoke_model.return_value = {
        'body': type('obj', (), {
            'read': lambda: json.dumps({
                'completion': 'Test response'
            }).encode('utf-8')
        })()
    }
    return client

def test_detector_with_fixture(mock_bedrock_client):
    detector = DriftDetector(client=mock_bedrock_client)
    result = detector.detect('incomplete_work', conversation)
    assert len(result) > 0
```

## Testing Rate Limiting

```python
from unittest.mock import Mock, call
from botocore.exceptions import ClientError

def test_retry_on_throttle(mock_bedrock_client):
    """Test that code retries on throttling."""
    # First call fails, second succeeds
    mock_bedrock_client.invoke_model.side_effect = [
        ClientError({'Error': {'Code': 'ThrottlingException'}}, 'invoke_model'),
        {'body': Mock(read=lambda: b'{"completion": "success"}')}
    ]

    result = analyze_with_retry(mock_bedrock_client, prompt)

    assert mock_bedrock_client.invoke_model.call_count == 2
    assert result == "success"
```
