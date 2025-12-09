# Test Organization Patterns

How to organize tests in Drift for maintainability and clarity.

## Directory Structure

### Standard Layout

```
tests/
├── __init__.py              # Makes tests a package
├── conftest.py              # Shared fixtures and configuration
├── test_utils.py            # Testing utilities (CliRunner, etc.)
├── mock_provider.py         # Mock implementations
├── fixtures/                # Static test data
│   ├── sample_bedrock_response.json
│   ├── sample_config.yaml
│   └── sample_conversation.jsonl
├── unit/                    # Unit tests (80-90% of tests)
│   ├── __init__.py
│   ├── test_validators/
│   │   ├── test_yaml_frontmatter_validator.py
│   │   ├── test_block_line_count_validator.py
│   │   └── ...
│   ├── test_analyzer.py
│   ├── test_config_loader.py
│   └── ...
└── integration/             # Integration tests (10-15%)
    ├── __init__.py
    ├── test_analyzer_workflows.py
    ├── test_plugin_system.py
    └── ...
```

### Directory Purpose

**`tests/`** - Root test directory
- Contains shared test utilities
- conftest.py with project-wide fixtures
- Static test data in fixtures/

**`tests/unit/`** - Unit tests
- Test individual components in isolation
- Mock external dependencies
- Fast execution (< 100ms per test)
- 70-80 test files in Drift

**`tests/integration/`** - Integration tests
- Test component interactions
- May use real file system (tmp_path)
- Slower execution (< 1s per test)
- 10-15 test files in Drift

**`tests/e2e/`** - End-to-end tests (if needed)
- Full user workflows
- Real configurations
- Slowest execution (< 5s per test)

### File Naming

**Pattern:** `test_<module>_<feature>.py`

**Examples:**
```
test_yaml_frontmatter_validator.py
test_block_line_count_validator.py
test_circular_dependencies_validator.py
test_analyzer_multi_phase.py
test_config_loader.py
```

**Rules:**
- Start with `test_` (pytest requirement)
- Descriptive of what's being tested
- One test file per major component
- Group related tests together

---

## Test Class Organization

### Standard Pattern

```python
class Test<Component>:
    """Tests for <Component>.

    <Brief description of what the component does>
    """

    # Fixtures first (setup methods)
    @pytest.fixture
    def component(self):
        """Create component instance.

        Returns:
            Component: Configured instance for testing
        """
        return Component()

    @pytest.fixture
    def test_data(self, tmp_path):
        """Create test data.

        Args:
            tmp_path: Pytest fixture for temporary directory

        Returns:
            TestData: Sample data for tests
        """
        return create_test_data(tmp_path)

    # Happy path tests (success cases)
    def test_succeeds_when_valid_input(self, component, test_data):
        """Test that component succeeds with valid input."""
        result = component.process(test_data)
        assert result.success is True

    # Failure tests (expected failures)
    def test_fails_when_invalid_input(self, component):
        """Test that component fails with invalid input."""
        result = component.process(invalid_data)
        assert result.success is False
        assert "invalid" in result.error

    # Edge case tests
    def test_handles_empty_input(self, component):
        """Test that component handles empty input gracefully."""
        result = component.process("")
        assert result is not None

    # Error handling tests
    def test_raises_error_when_required_missing(self, component):
        """Test that component raises error when required param missing."""
        with pytest.raises(ValueError, match="required"):
            component.process(None)
```

### Grouping Within Class

**Group tests by:**
1. Test type (happy/failure/edge/error)
2. Feature area
3. Specific method being tested

**Example from YamlFrontmatterValidator:**
```python
class TestYamlFrontmatterValidator:
    """Tests for YamlFrontmatterValidator."""

    @pytest.fixture
    def validator(self):
        """Create validator instance."""
        return YamlFrontmatterValidator()

    # === Valid frontmatter tests ===
    def test_passes_with_valid_frontmatter(self):
        """Test validation passes with valid YAML frontmatter."""

    def test_passes_with_empty_frontmatter(self):
        """Test validation passes with empty frontmatter."""

    # === Invalid frontmatter tests ===
    def test_fails_with_invalid_yaml(self):
        """Test validation fails with malformed YAML."""

    def test_fails_with_unclosed_frontmatter(self):
        """Test validation fails with unclosed frontmatter."""

    # === Schema validation tests ===
    def test_passes_when_matches_schema(self):
        """Test validation passes when YAML matches schema."""

    def test_fails_when_missing_required_field(self):
        """Test validation fails when required field missing."""

    # === Error handling tests ===
    def test_handles_file_not_found(self):
        """Test validator handles missing file gracefully."""
```

---

## Test Method Naming

### Convention

**Pattern:** `test_<component>_<behavior>_<condition>`

**Or shorter:** `test_<behavior>_<condition>`

**Parts:**
- `test_` - Required prefix
- `<component>` - Optional, what is being tested
- `<behavior>` - What happens (passes, fails, raises, returns, etc.)
- `<condition>` - When/why (when valid, when missing, with empty, etc.)

### Good Names

```python
def test_validator_passes_when_within_limit()
def test_parser_raises_error_on_invalid_json()
def test_analyzer_skips_disabled_rules()
def test_formatter_includes_file_paths()
def test_loader_merges_project_over_global_config()
```

**Why they're good:**
- Clear what's being tested
- Clear what the expected behavior is
- Clear under what conditions
- Self-documenting

### Bad Names

```python
def test_validator()                  # Too vague
def test_case_1()                     # No context
def test_validator_test()             # Redundant
def test_this_should_work()           # Unclear
def test_function()                   # What function? What about it?
```

**Why they're bad:**
- Don't explain what's being tested
- Don't explain expected behavior
- Hard to understand when they fail
- Not maintainable

### Drift Examples

**From test_yaml_frontmatter_validator.py:**
```python
def test_validation_type(self)
def test_passes_with_valid_frontmatter(self)
def test_fails_with_invalid_yaml(self)
def test_fails_with_missing_required_field(self)
def test_handles_unclosed_frontmatter(self)
```

**From test_circular_dependencies_validator.py:**
```python
def test_detects_self_loop(self)
def test_detects_two_node_cycle(self)
def test_passes_with_no_cycles(self)
def test_reports_cycle_participants(self)
```

---

## Fixture Management

### Fixture Hierarchy

**Three levels:**

1. **Project-level** (conftest.py at root)
2. **Module-level** (test_*.py file)
3. **Class-level** (within test class)

```python
# tests/conftest.py - PROJECT LEVEL
@pytest.fixture
def temp_dir():
    """Temporary directory for all tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)

@pytest.fixture
def sample_drift_config():
    """Standard Drift configuration for testing."""
    return DriftConfig(...)

# tests/unit/test_validators.py - MODULE LEVEL
@pytest.fixture
def sample_bundle(tmp_path):
    """Standard DocumentBundle for validator tests."""
    return DocumentBundle(...)

# Within test class - CLASS LEVEL
class TestMyValidator:
    @pytest.fixture
    def validator(self):
        """Validator instance for this test class."""
        return MyValidator()

    @pytest.fixture
    def rule(self):
        """Validation rule for this test class."""
        return ValidationRule(max_count=100)
```

### Fixture Composition

**Build complex fixtures from simpler ones:**

```python
# Simple fixtures
@pytest.fixture
def sample_provider_config():
    return ProviderConfig(provider="bedrock", ...)

@pytest.fixture
def sample_model_config():
    return ModelConfig(model_id="haiku", ...)

@pytest.fixture
def sample_rule_definition():
    return RuleDefinition(rule_id="test", ...)

# Composed fixture
@pytest.fixture
def sample_drift_config(
    sample_provider_config,
    sample_model_config,
    sample_rule_definition
):
    """Complete Drift config from component fixtures."""
    return DriftConfig(
        providers={"bedrock": sample_provider_config},
        models={"haiku": sample_model_config},
        rule_definitions={"rule": sample_rule_definition},
    )
```

**Benefits:**
- Reusable components
- Easy to customize
- Clear dependencies
- Maintainable

### Fixture Scopes

**Choose appropriately:**

```python
@pytest.fixture(scope="session")
def expensive_setup():
    """Created once per test session.

    Use for:
    - Database connections
    - External service setup
    - Expensive computations
    """
    setup = ExpensiveSetup()
    yield setup
    setup.teardown()

@pytest.fixture(scope="module")
def shared_resource():
    """Created once per test module.

    Use for:
    - Shared test data
    - Module-level mocks
    - Common configuration
    """
    return SharedResource()

@pytest.fixture(scope="function")  # Default
def isolated_data():
    """Created for each test function.

    Use for:
    - Test-specific data
    - Mutable objects
    - Anything that needs isolation
    """
    return IsolatedData()
```

**Drift examples:**
```python
@pytest.fixture  # function scope (default)
def validator(self):
    """New instance for each test - ensures isolation."""
    return BlockLineCountValidator()

@pytest.fixture  # function scope
def bundle(self, tmp_path):
    """New bundle for each test - prevents state sharing."""
    return create_bundle(tmp_path)
```

### Factory Fixtures

**For customizable test data:**

```python
@pytest.fixture
def make_bundle():
    """Factory for creating custom bundles.

    Returns:
        Callable: Function to create bundles with custom parameters
    """
    def _make_bundle(bundle_type="skill", num_files=1, content="test"):
        files = [
            DocumentFile(
                relative_path=f"file{i}.md",
                content=content,
                file_path=f"/test/file{i}.md"
            )
            for i in range(num_files)
        ]
        return DocumentBundle(
            bundle_id=f"test-{bundle_type}",
            bundle_type=bundle_type,
            bundle_strategy="individual",
            files=files,
            project_path="/test"
        )
    return _make_bundle

# Usage in tests
def test_with_custom_bundle(make_bundle):
    """Test with custom bundle configuration."""
    # Create bundle with 3 files
    bundle = make_bundle(bundle_type="command", num_files=3)

    # Create bundle with specific content
    bundle = make_bundle(content="# Custom content")
```

---

## Test Data Management

### Strategy 1: Inline Data

**For simple, one-off test data:**

```python
def test_parses_valid_frontmatter():
    """Test parsing of valid YAML frontmatter."""
    content = """---
title: Test Document
description: Sample
---
# Content here
"""
    result = parse_frontmatter(content)
    assert result["title"] == "Test Document"
```

**When to use:**
- Simple data
- One-time use
- Easy to understand inline

### Strategy 2: Fixture Data

**For reusable test data:**

```python
@pytest.fixture
def sample_conversation():
    """Sample conversation for testing."""
    return Conversation(
        session_id="test-123",
        turns=[
            Turn(role="user", content="Hello"),
            Turn(role="assistant", content="Hi there"),
        ],
        metadata={"tool": "claude-code"}
    )

def test_analyzes_conversation(sample_conversation):
    """Test conversation analysis."""
    result = analyze(sample_conversation)
    assert result is not None
```

**When to use:**
- Reused across multiple tests
- Complex data structures
- Shared test state

### Strategy 3: tmp_path for Files

**For file-based testing:**

```python
def test_reads_config_file(tmp_path):
    """Test reading configuration from file."""
    # Create test file
    config_file = tmp_path / "config.yaml"
    config_file.write_text("""
providers:
  bedrock:
    region: us-east-1
""")

    # Test with file
    config = load_config(config_file)
    assert config.providers["bedrock"].region == "us-east-1"
```

**When to use:**
- Testing file operations
- Need actual files
- Testing path handling

**Benefits:**
- Automatic cleanup
- Isolated per test
- Real file operations

### Strategy 4: Parametrize for Variations

**For testing multiple inputs:**

```python
@pytest.mark.parametrize("provider,expected_tokenizer", [
    ("anthropic", "anthropic tokenizer"),
    ("openai", "openai tokenizer"),
    ("llama", "llama tokenizer"),
    ("unknown", "default tokenizer"),
])
def test_tokenizer_selection(provider, expected_tokenizer):
    """Test tokenizer selection for different providers."""
    result = select_tokenizer(provider)
    assert result == expected_tokenizer
```

**When to use:**
- Same test logic, different inputs
- Testing boundaries
- Multiple similar scenarios

**Benefits:**
- Less code duplication
- Clear test cases
- Easy to add cases

### Strategy 5: Static Fixtures

**For unchanging test data:**

```
tests/fixtures/
├── sample_bedrock_response.json
├── sample_config.yaml
└── sample_conversation.jsonl
```

```python
@pytest.fixture
def sample_bedrock_response():
    """Load sample Bedrock API response."""
    path = Path(__file__).parent / "fixtures" / "sample_bedrock_response.json"
    return json.loads(path.read_text())

def test_parses_bedrock_response(sample_bedrock_response):
    """Test parsing of Bedrock API response."""
    result = parse_response(sample_bedrock_response)
    assert result is not None
```

**When to use:**
- Large test data
- Real examples
- API responses

---

## Patterns from Drift Codebase

### Pattern 1: DocumentBundle Creation

**Standard pattern for validator tests:**

```python
@pytest.fixture
def bundle(self, tmp_path):
    """Create DocumentBundle with test file."""
    # Create test file
    test_file = tmp_path / "test.md"
    test_file.write_text("# Test\nContent")

    # Create DocumentBundle
    return DocumentBundle(
        bundle_id="test-bundle",
        bundle_type="skill",
        bundle_strategy="individual",
        files=[
            DocumentFile(
                relative_path="test.md",
                content="# Test\nContent",
                file_path=str(test_file),
            )
        ],
        project_path=tmp_path,
    )
```

### Pattern 2: Validator Testing Template

**Standard structure for validator tests:**

```python
class TestMyValidator:
    """Tests for MyValidator."""

    @pytest.fixture
    def validator(self):
        """Create validator instance."""
        return MyValidator()

    @pytest.fixture
    def bundle(self, tmp_path):
        """Create test bundle."""
        # ... create bundle ...
        return bundle

    def test_validation_type(self, validator):
        """Test validation_type property."""
        assert validator.validation_type == "expected:type"

    def test_passes_when_valid(self, validator, bundle):
        """Test validation passes with valid input."""
        rule = ValidationRule(param=value)
        result = validator.validate(rule, bundle)
        assert result is None  # None = pass

    def test_fails_when_invalid(self, validator, bundle):
        """Test validation fails with invalid input."""
        rule = ValidationRule(param=bad_value)
        result = validator.validate(rule, bundle)
        assert result is not None
        assert "expected error" in result.observed_issue

    def test_handles_edge_case(self, validator, bundle):
        """Test validator handles edge case."""
        # ... test edge case ...
```

### Pattern 3: Mock Provider

**For testing LLM interactions:**

```python
def test_analyzes_with_mock_provider(monkeypatch):
    """Test analysis with mocked LLM provider."""
    # Create mock
    mock_client = Mock()
    mock_client.count_tokens.return_value = 500

    mock_anthropic = Mock()
    mock_anthropic.Anthropic.return_value = mock_client

    # Patch import
    monkeypatch.setitem(sys.modules, "anthropic", mock_anthropic)

    # Test with mock
    result = analyze_content("test content")
    assert result is not None
    mock_client.count_tokens.assert_called_once()
```

### Pattern 4: CLI Testing

**Using custom CliRunner:**

```python
from tests.test_utils import CliRunner

def test_cli_command():
    """Test CLI command execution."""
    runner = CliRunner()
    result = runner.invoke(
        main,
        ["--no-llm", "--format", "json"]
    )

    assert result.exit_code == 0
    assert "output" in result.stdout
```

---

## Anti-Patterns to Avoid

### ❌ Tests Sharing State

```python
# BAD - Shared state
class TestValidator:
    validator = Validator()  # Shared across tests!

    def test_one(self):
        self.validator.state = "modified"

    def test_two(self):
        # Depends on test_one's state!
        assert self.validator.state == "modified"
```

```python
# GOOD - Isolated state
class TestValidator:
    @pytest.fixture
    def validator(self):
        """New instance per test."""
        return Validator()

    def test_one(self, validator):
        validator.state = "modified"
        assert validator.state == "modified"

    def test_two(self, validator):
        # Fresh instance, no dependencies
        assert validator.state == "initial"
```

### ❌ Test Order Dependencies

```python
# BAD - Tests depend on order
def test_step1():
    global result
    result = compute()

def test_step2():
    # Fails if test_step1 doesn't run first!
    assert result == expected
```

```python
# GOOD - Independent tests
def test_computes_correctly():
    result = compute()
    assert result == expected

def test_uses_computed_result():
    result = compute()  # Compute in this test
    output = use_result(result)
    assert output is not None
```

### ❌ Over-Complex Tests

```python
# BAD - Testing too many things
def test_everything():
    # Parse frontmatter
    frontmatter = parse(content)
    # Validate against schema
    valid = validate(frontmatter)
    # Format output
    output = format(valid)
    # Write to file
    write(output)
    # Read back
    result = read()
    # ... too much!
```

```python
# GOOD - Focused tests
def test_parses_frontmatter():
    frontmatter = parse(content)
    assert frontmatter["title"] == "Test"

def test_validates_against_schema():
    valid = validate(frontmatter, schema)
    assert valid is True

def test_formats_output():
    output = format(valid_data)
    assert "title" in output
```

### ❌ Brittle Assertions

```python
# BAD - Fragile string matching
def test_error_message():
    result = validator.validate(rule, bundle)
    assert result.observed_issue == "File test.md line 45 exceeds maximum of 100 lines (found 150)"
```

```python
# GOOD - Flexible assertions
def test_error_message():
    result = validator.validate(rule, bundle)
    assert "test.md" in result.observed_issue
    assert "exceeds maximum" in result.observed_issue
    assert "100" in result.observed_issue
    assert "150" in result.observed_issue
```

---

## Organization Checklist

When organizing tests, verify:

- [ ] Tests in correct directory (unit/integration/e2e)
- [ ] File named `test_<module>.py`
- [ ] Test class named `Test<Component>`
- [ ] Fixtures before test methods
- [ ] Tests grouped logically (happy/failure/edge/error)
- [ ] Clear test method names
- [ ] Appropriate fixture scopes
- [ ] No shared state between tests
- [ ] No test order dependencies
- [ ] Tests are independent and isolated
- [ ] Each test has clear, focused assertions
- [ ] Test docstrings explain what/why

---

## Quick Reference

### File Structure
```
tests/unit/test_<component>.py
```

### Class Structure
```python
class Test<Component>:
    @pytest.fixture
    def component(self):
        return Component()

    def test_<behavior>_<condition>(self, component):
        result = component.method()
        assert result == expected
```

### Naming
- Files: `test_<module>.py`
- Classes: `Test<Component>`
- Methods: `test_<behavior>_<condition>`
- Fixtures: descriptive noun

### Fixtures
- Project: `tests/conftest.py`
- Module: Top of `test_*.py`
- Class: Inside `Test*` class
- Scope: function (default), module, session
