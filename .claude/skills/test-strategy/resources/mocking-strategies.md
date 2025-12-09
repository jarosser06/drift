# Mocking Strategies

Strategic guidance on when, why, and how to mock in Python tests.

## When to Mock vs Test Real

### Decision Framework

**Mock when testing code that:**
- Depends on external services (APIs, databases, cloud services)
- Has non-deterministic behavior (current time, random values)
- Involves slow operations (network calls, file I/O, large computations)
- Requires isolating the unit under test from its dependencies
- Interacts with paid services (avoid costs during testing)
- Has side effects you want to prevent (sending emails, writing to production DB)

**Test with real dependencies when:**
- Testing simple pure functions with no external dependencies
- The real dependency is fast, reliable, and deterministic
- Testing integration between components (integration tests)
- Over-isolating would make tests meaningless
- The dependency is part of what you're testing

### Cost/Benefit Analysis

**Benefits of Mocking:**
- ✅ Tests run faster (no network/disk I/O)
- ✅ Tests are more reliable (no external service failures)
- ✅ Can test error scenarios easily (simulate failures)
- ✅ No setup/teardown of external services needed
- ✅ Tests can run offline

**Costs of Mocking:**
- ❌ Mocks can fall out of sync with real implementations
- ❌ Over-mocking leads to brittle tests
- ❌ Tests may pass even when code is broken
- ❌ More code to maintain (mock setup)
- ❌ Can miss integration issues

**Rule of thumb:** Mock at system boundaries, test real internally.

### Testing at Boundaries

**System Boundary Pattern:**

```python
# Your code structure
Application Code
├── Business Logic (test with real)
│   ├── Validators
│   ├── Parsers
│   └── Analyzers
└── External Adapters (MOCK HERE)
    ├── API Clients
    ├── Database Access
    └── File System
```

**Good:**
```python
def test_validates_user_data():
    """Test validation logic with real validator."""
    validator = UserValidator()  # Real
    result = validator.validate(user_data)  # Real
    assert result.is_valid

def test_calls_api_correctly(monkeypatch):
    """Test API interaction with mocked client."""
    mock_client = Mock()  # Mock at boundary
    mock_client.create_user.return_value = {"id": 123}

    service = UserService(mock_client)
    result = service.create_user(user_data)

    mock_client.create_user.assert_called_once()
```

**Bad:**
```python
def test_validates_user_data(monkeypatch):
    """Over-mocking internal logic."""
    mock_validator = Mock()  # DON'T mock your own code!
    mock_validator.validate.return_value = True

    # This test is meaningless
    result = mock_validator.validate(user_data)
    assert result is True  # Of course it is!
```

---

## Pytest Monkeypatch vs unittest.mock

### Feature Comparison

| Feature | pytest monkeypatch | unittest.mock |
|---------|-------------------|---------------|
| **Automatic cleanup** | ✅ Yes | ✅ Yes (with patch context) |
| **Call tracking** | ❌ No | ✅ Yes |
| **Return value control** | ⚠️ Manual | ✅ `return_value` |
| **Side effects** | ⚠️ Manual | ✅ `side_effect` |
| **Decorators** | ❌ No | ✅ `@patch` |
| **Method signature validation** | ❌ No | ✅ `autospec=True` |
| **Simple patching** | ✅ Excellent | ⚠️ More verbose |
| **Environment variables** | ✅ Built-in | ⚠️ Manual |
| **Dictionary patching** | ✅ Built-in | ⚠️ Manual |

### When to Use Each

**Use pytest monkeypatch when:**
- Simple attribute or function replacement
- Patching environment variables
- Modifying dictionaries (like `sys.modules`)
- One-line replacements
- No need for call verification

**Use unittest.mock when:**
- Need to verify how mocks are called
- Complex mocking scenarios with multiple returns
- Want to use decorators for cleaner tests
- Need `return_value` or `side_effect`
- Testing call sequences or arguments

### Drift Examples of Both

**Monkeypatch Example: Missing Package**

```python
def test_anthropic_package_missing(monkeypatch):
    """Test handling of missing anthropic package using monkeypatch."""
    # Simple replacement in sys.modules
    monkeypatch.setitem(sys.modules, "anthropic", None)

    with pytest.raises(RuntimeError, match="anthropic package required"):
        provider = AnthropicProvider()
```

**Mock Example: API Call Tracking**

```python
from unittest.mock import Mock, patch

@patch("drift.providers.anthropic.Anthropic", autospec=True)
def test_counts_tokens_correctly(mock_anthropic):
    """Test token counting with mock to verify calls."""
    # Setup mock behavior
    mock_client = Mock()
    mock_client.count_tokens.return_value = 500
    mock_anthropic.return_value = mock_client

    # Execute
    provider = AnthropicProvider()
    result = provider.count_tokens("test content")

    # Verify behavior
    assert result == 500
    mock_client.count_tokens.assert_called_once_with("test content")
```

---

## Mocking Strategies

### External APIs

**Pattern: Mock the client, not the library**

```python
from unittest.mock import Mock, patch

@patch("drift.providers.bedrock.boto3.client", autospec=True)
def test_bedrock_api_call(mock_boto_client):
    """Test AWS Bedrock API interaction."""
    # Setup mock client
    mock_bedrock = Mock()
    mock_bedrock.invoke_model.return_value = {
        "body": json.dumps({"completion": "test response"})
    }
    mock_boto_client.return_value = mock_bedrock

    # Test
    provider = BedrockProvider()
    result = provider.generate("test prompt")

    # Verify
    assert "test response" in result
    mock_bedrock.invoke_model.assert_called_once()
```

**Drift Example: Mock Provider Pattern**

From `tests/mock_provider.py`:

```python
class MockProvider(Provider):
    """Reusable mock provider for LLM testing."""

    def __init__(self, provider_config=None, model_config=None):
        self.call_count = 0
        self.calls = []
        self.response = "[]"

    def set_response(self, response: str):
        """Configure what the mock returns."""
        self.response = response

    def generate(self, prompt: str) -> str:
        """Track calls and return configured response."""
        self.call_count += 1
        self.calls.append(prompt)
        return self.response

    def reset(self):
        """Reset call tracking."""
        self.call_count = 0
        self.calls = []

# Usage in tests
def test_with_mock_provider():
    provider = MockProvider()
    provider.set_response('[{"type": "drift", "message": "test"}]')

    result = analyze_with_provider(provider, conversation)

    assert provider.call_count == 1
    assert "drift" in result
```

### File System Operations

**Strategy: Use tmp_path for real files, monkeypatch for errors**

```python
# Good: Use tmp_path for real file testing
def test_reads_config_file(tmp_path):
    """Test reading real file with tmp_path."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text("provider: bedrock")

    config = load_config(config_file)
    assert config.provider == "bedrock"

# Good: Use monkeypatch to simulate errors
def test_handles_file_read_error(monkeypatch):
    """Test handling of file read errors."""
    def mock_read_text():
        raise IOError("Permission denied")

    monkeypatch.setattr(Path, "read_text", mock_read_text)

    with pytest.raises(IOError, match="Permission denied"):
        load_config("config.yaml")
```

### Import Mocking

**Pattern: Use monkeypatch.setitem for sys.modules**

```python
import sys

def test_optional_package_missing(monkeypatch):
    """Test handling of missing optional dependency."""
    # Make import fail
    monkeypatch.setitem(sys.modules, "tiktoken", None)

    # This will trigger ImportError handling
    with pytest.raises(RuntimeError, match="tiktoken package required"):
        tokenizer = create_tokenizer("openai")

def test_optional_package_present():
    """Test with package present (no mocking)."""
    # Test with real package if available
    try:
        tokenizer = create_tokenizer("openai")
        assert tokenizer is not None
    except ImportError:
        pytest.skip("tiktoken not installed")
```

### Time and Randomness

**Pattern: Mock time-dependent functions**

```python
from unittest.mock import patch
import time

@patch("time.time")
def test_rate_limiting(mock_time):
    """Test rate limiting with mocked time."""
    # Control time progression
    mock_time.side_effect = [0, 0.5, 1.0, 1.5]

    limiter = RateLimiter(calls_per_second=1)

    assert limiter.allow()  # t=0
    assert limiter.allow()  # t=0.5
    assert not limiter.allow()  # t=1.0 (too fast)
    assert limiter.allow()  # t=1.5

@patch("random.random")
def test_sampling(mock_random):
    """Test random sampling with controlled values."""
    mock_random.side_effect = [0.1, 0.5, 0.9]

    samples = [sample_with_probability(0.5) for _ in range(3)]

    assert samples == [True, True, False]  # 0.1 < 0.5, 0.5 == 0.5, 0.9 > 0.5
```

---

## Mock Verification

### Call Tracking

**Basic verification:**

```python
from unittest.mock import Mock

def test_calls_method_once():
    """Test that method is called exactly once."""
    mock = Mock()

    process_data(mock)

    mock.process.assert_called_once()

def test_calls_with_correct_args():
    """Test that method is called with specific arguments."""
    mock = Mock()

    process_data(mock, "test", count=5)

    mock.process.assert_called_once_with("test", count=5)
```

### Argument Verification

**Complex argument checking:**

```python
from unittest.mock import Mock, call, ANY

def test_multiple_calls():
    """Test sequence of calls."""
    mock = Mock()

    service = DataService(mock)
    service.process_batch(["a", "b", "c"])

    # Verify call sequence
    mock.save.assert_has_calls([
        call("a"),
        call("b"),
        call("c"),
    ])

def test_with_any_matcher():
    """Test with partial argument matching."""
    mock = Mock()

    service.send_notification(user_id=123, timestamp=ANY)

    mock.send.assert_called_with(user_id=123, timestamp=ANY)
```

### Call Count Assertions

```python
def test_retries_on_failure():
    """Test retry logic."""
    mock = Mock()
    mock.send.side_effect = [
        Exception("Fail"),
        Exception("Fail"),
        {"status": "success"}
    ]

    service = RetryService(mock, max_retries=3)
    result = service.send_with_retry("data")

    assert result["status"] == "success"
    assert mock.send.call_count == 3  # Failed twice, succeeded third
```

### Mock Reset Strategies

```python
from unittest.mock import Mock

class TestDataProcessor:
    @pytest.fixture
    def mock_client(self):
        """Shared mock that resets between tests."""
        mock = Mock()
        yield mock
        mock.reset_mock()  # Reset for next test

    def test_first_scenario(self, mock_client):
        """First test."""
        processor = DataProcessor(mock_client)
        processor.process("data1")

        mock_client.send.assert_called_once()

    def test_second_scenario(self, mock_client):
        """Second test with fresh mock."""
        processor = DataProcessor(mock_client)
        processor.process("data2")

        # Mock was reset, so count is 1, not 2
        mock_client.send.assert_called_once()
```

---

## Common Anti-Patterns

### 1. Over-Mocking

**Anti-pattern:**
```python
def test_validate_user_with_too_many_mocks(monkeypatch):
    """BAD: Mocking everything."""
    mock_parser = Mock()
    mock_validator = Mock()
    mock_formatter = Mock()
    mock_logger = Mock()

    # Test becomes meaningless
    result = process_user(
        data,
        parser=mock_parser,
        validator=mock_validator,
        formatter=mock_formatter,
        logger=mock_logger
    )
```

**Better:**
```python
def test_validate_user(monkeypatch):
    """GOOD: Only mock external dependency."""
    mock_api_client = Mock()  # Only mock the API
    mock_api_client.fetch_user.return_value = user_data

    # Test real validation logic
    validator = UserValidator(api_client=mock_api_client)
    result = validator.validate(user_id=123)

    assert result.is_valid
```

### 2. Not Using autospec

**Anti-pattern:**
```python
@patch("mymodule.SomeClass")  # No autospec!
def test_without_autospec(mock_class):
    """BAD: Can call methods that don't exist."""
    mock = Mock()
    mock.nonexistent_method.return_value = "works"  # Silently passes!
    mock_class.return_value = mock

    # Test passes even though method doesn't exist
    result = use_some_class()
    assert result == "works"
```

**Better:**
```python
@patch("mymodule.SomeClass", autospec=True)  # With autospec!
def test_with_autospec(mock_class):
    """GOOD: Validates method signatures."""
    mock = Mock(spec=SomeClass)
    # mock.nonexistent_method()  # Would raise AttributeError!
    mock.real_method.return_value = "works"
    mock_class.return_value = mock

    result = use_some_class()
    assert result == "works"
```

### 3. Mocking Implementation Instead of Interface

**Anti-pattern:**
```python
def test_mocks_private_method():
    """BAD: Mocking internal implementation."""
    service = UserService()

    # Mocking private method couples test to implementation
    service._internal_validation = Mock(return_value=True)

    result = service.create_user(user_data)
    assert result.success
```

**Better:**
```python
def test_mocks_external_dependency():
    """GOOD: Mock external dependency, test public interface."""
    mock_api = Mock()
    mock_api.validate_email.return_value = True

    service = UserService(email_validator=mock_api)
    result = service.create_user(user_data)

    assert result.success
    mock_api.validate_email.assert_called_once()
```

### 4. Mocks Falling Out of Sync

**Problem:**
```python
# Real API changed signature
class RealAPI:
    def send(self, data, timeout=30, retry=True):  # Added timeout, retry
        ...

# Mock hasn't been updated
def test_with_outdated_mock():
    """Test uses old signature."""
    mock = Mock()
    mock.send.return_value = "success"

    # This passes but doesn't match real API!
    result = service.send("data")  # Missing timeout, retry
```

**Solution: Use autospec**
```python
@patch("mymodule.RealAPI", autospec=True)
def test_with_autospec(mock_api):
    """autospec ensures mock matches real signature."""
    mock_instance = Mock(spec=RealAPI)
    mock_instance.send.return_value = "success"
    mock_api.return_value = mock_instance

    # Will fail if signature doesn't match
    service = MyService(mock_instance)
    result = service.send_data("data")
```

### 5. Brittle Tests from Tight Coupling

**Anti-pattern:**
```python
def test_tightly_coupled_to_implementation():
    """BAD: Test knows too much about implementation."""
    mock = Mock()

    service = DataService(mock)
    service.process("data")

    # Coupled to exact implementation details
    mock.transform.assert_called_once()
    mock.validate.assert_called_once()
    mock.save.assert_called_once()
    # If implementation changes order, test breaks
```

**Better:**
```python
def test_focuses_on_behavior():
    """GOOD: Test focuses on behavior, not implementation."""
    mock = Mock()

    service = DataService(mock)
    result = service.process("data")

    # Only verify the outcome
    assert result.success
    mock.save.assert_called()  # Called at some point
```

---

## Best Practices

### 1. Always Use autospec=True

```python
# GOOD
@patch("mymodule.ExternalService", autospec=True)
def test_with_autospec(mock_service):
    """Mock respects real method signatures."""
    ...

# BAD
@patch("mymodule.ExternalService")
def test_without_autospec(mock_service):
    """Can create invalid method calls."""
    ...
```

### 2. Mock at System Boundaries

```python
# GOOD: Mock external API
def test_mocks_at_boundary(monkeypatch):
    """Mock the external dependency."""
    mock_api_client = Mock()
    service = MyService(api_client=mock_api_client)
    ...

# BAD: Mock internal logic
def test_mocks_internal(monkeypatch):
    """Don't mock your own code."""
    service = MyService()
    monkeypatch.setattr(service, "_internal_method", Mock())
    ...
```

### 3. Use spec Keyword for Safety

```python
from mymodule import RealClass

# GOOD: Mock with spec
def test_with_spec():
    """Mock can only access real attributes."""
    mock = Mock(spec=RealClass)
    mock.real_method.return_value = "value"
    # mock.fake_method()  # AttributeError!

# BAD: Mock without spec
def test_without_spec():
    """Mock accepts any attribute."""
    mock = Mock()
    mock.anything.works()  # Silently passes
```

### 4. Keep Mocks Simple

```python
# GOOD: Simple, focused mock
def test_simple_mock():
    """One mock, one purpose."""
    mock_api = Mock()
    mock_api.get_user.return_value = {"id": 123}

    result = service.fetch_user(123)
    assert result["id"] == 123

# BAD: Complex mock setup
def test_complex_mock():
    """Too much mock configuration."""
    mock = Mock()
    mock.method.return_value.attribute.value.getter.return_value = "data"
    # This is too complex!
```

### 5. Verify Mock Behavior

```python
# GOOD: Verify the mock was used correctly
def test_verifies_mock():
    """Verify mock behavior."""
    mock = Mock()

    service.process(mock, "data")

    mock.save.assert_called_once_with("data")

# BAD: Mock without verification
def test_no_verification():
    """Doesn't verify mock was used."""
    mock = Mock()

    service.process(mock, "data")
    # No assertions about mock behavior!
```

### 6. Document Why Mocking Is Needed

```python
def test_aws_bedrock_with_mock(monkeypatch):
    """Test AWS Bedrock integration.

    Mocking rationale:
    - Bedrock API calls cost money
    - Network calls are slow
    - Need to test error scenarios
    - Want tests to run offline
    """
    mock_client = Mock(spec=BedrockClient)
    ...
```

---

## Drift-Specific Patterns

### Pattern 1: Mock Provider (from tests/mock_provider.py)

```python
from tests.mock_provider import MockProvider

def test_analyzer_with_mock_provider():
    """Test analyzer with mock LLM provider."""
    # Create and configure mock
    mock_provider = MockProvider()
    mock_provider.set_response('[{"type": "incomplete_work"}]')

    # Run test
    analyzer = DriftAnalyzer(provider=mock_provider)
    result = analyzer.analyze(conversation)

    # Verify
    assert mock_provider.call_count == 1
    assert "incomplete_work" in result
```

### Pattern 2: Import Error Mocking

```python
import sys

def test_missing_anthropic_package(monkeypatch):
    """Test handling of missing anthropic package."""
    monkeypatch.setitem(sys.modules, "anthropic", None)

    with pytest.raises(RuntimeError, match="anthropic package required"):
        provider = AnthropicProvider()

def test_missing_tiktoken_package(monkeypatch):
    """Test handling of missing tiktoken package."""
    monkeypatch.setitem(sys.modules, "tiktoken", None)

    with pytest.raises(RuntimeError, match="tiktoken package required"):
        tokenizer = create_tokenizer("openai")
```

### Pattern 3: File Operation Mocking

```python
# Use tmp_path for happy path
def test_reads_frontmatter(tmp_path):
    """Test reading YAML frontmatter from real file."""
    file = tmp_path / "test.md"
    file.write_text("---\ntitle: Test\n---\nContent")

    result = parse_frontmatter(file)
    assert result["title"] == "Test"

# Use monkeypatch for error cases
def test_handles_file_read_error(monkeypatch):
    """Test handling of file read errors."""
    def mock_read_text():
        raise IOError("Permission denied")

    monkeypatch.setattr(Path, "read_text", mock_read_text)

    with pytest.raises(IOError):
        parse_frontmatter("file.md")
```

### Pattern 4: AWS Bedrock Mocking

```python
from unittest.mock import Mock, patch

@patch("drift.providers.bedrock.boto3.client", autospec=True)
def test_bedrock_token_counting(mock_boto_client):
    """Test Bedrock token counting."""
    # Setup mock client
    mock_bedrock = Mock()
    mock_bedrock.invoke_model.return_value = {
        "body": json.dumps({"usage": {"input_tokens": 150}})
    }
    mock_boto_client.return_value = mock_bedrock

    # Test
    provider = BedrockProvider()
    count = provider.count_tokens("test content")

    # Verify
    assert count == 150
    mock_bedrock.invoke_model.assert_called_once()
```

---

## Mocking Checklist

Before using a mock in your test:

- [ ] **Necessary?** Is mocking required or can I test with real dependency?
- [ ] **Boundary?** Am I mocking at a system boundary, not internal logic?
- [ ] **Tool choice?** Using appropriate tool (monkeypatch vs mock)?
- [ ] **autospec?** Using `autospec=True` if using unittest.mock?
- [ ] **Spec?** Using `spec` parameter for type safety?
- [ ] **Behavior?** Does mock mimic real behavior accurately?
- [ ] **Verification?** Am I verifying the mock was called correctly?
- [ ] **Meaningful?** Is the test still meaningful with mocks?
- [ ] **Documented?** Is it clear why mocking is necessary?
- [ ] **Simple?** Is the mock setup as simple as possible?

---

## Quick Reference

### Monkeypatch Examples

```python
# Set attribute
monkeypatch.setattr(obj, "attribute", value)

# Set item in dict
monkeypatch.setitem(sys.modules, "package", None)

# Set environment variable
monkeypatch.setenv("API_KEY", "test_key")

# Delete attribute
monkeypatch.delattr(obj, "attribute")

# Change directory
monkeypatch.chdir(path)
```

### Mock Examples

```python
# Basic mock
mock = Mock()
mock.method.return_value = "value"

# Mock with spec
mock = Mock(spec=RealClass)

# Patch decorator
@patch("module.Class", autospec=True)
def test_func(mock_class):
    ...

# Patch context manager
with patch("module.function") as mock_func:
    mock_func.return_value = "value"

# Side effects (sequence of returns)
mock.method.side_effect = [1, 2, 3]

# Side effects (exception)
mock.method.side_effect = Exception("Error")

# Verify calls
mock.method.assert_called_once()
mock.method.assert_called_with(arg1, arg2)
mock.method.assert_not_called()
```

### Remember

**Mock at boundaries, test real internally.**
