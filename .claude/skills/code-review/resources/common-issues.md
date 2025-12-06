# Common Code Review Issues

Anti-patterns and common problems to watch for when reviewing Drift code.

## Critical Issues

### 1. Inline Imports

**❌ WRONG:**
```python
def analyze_file(path: str):
    from drift.core.parser import parse_conversation  # NO!
    return parse_conversation(path)
```

**✅ RIGHT:**
```python
from drift.core.parser import parse_conversation

def analyze_file(path: str):
    return parse_conversation(path)
```

**Why it matters:** Violates PEP 8, makes dependencies unclear, impacts performance.

### 2. Missing Error Handling

**❌ WRONG:**
```python
def load_config(path):
    with open(path) as f:
        return json.load(f)  # Can crash on bad JSON or missing file
```

**✅ RIGHT:**
```python
def load_config(path: str) -> dict:
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"Config not found: {path}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {path}: {e}")
```

### 3. Overly Broad Exception Catching

**❌ WRONG:**
```python
try:
    result = process_data(data)
except Exception:  # Too broad!
    return None
```

**✅ RIGHT:**
```python
try:
    result = process_data(data)
except (ValueError, KeyError) as e:
    logger.error(f"Data processing failed: {e}")
    raise
```

## Code Quality Issues

### 4. Code Duplication

**❌ WRONG:**
```python
def analyze_type_a(conv):
    client = boto3.client('bedrock-runtime')
    prompt = build_prompt(conv, 'type_a')
    response = client.invoke_model(...)
    return parse_response(response)

def analyze_type_b(conv):
    client = boto3.client('bedrock-runtime')  # Duplicated!
    prompt = build_prompt(conv, 'type_b')
    response = client.invoke_model(...)
    return parse_response(response)
```

**✅ RIGHT:**
```python
def analyze_drift_type(conv: dict, drift_type: str) -> list:
    client = boto3.client('bedrock-runtime')
    prompt = build_prompt(conv, drift_type)
    response = client.invoke_model(...)
    return parse_response(response)
```

### 5. Poor Function Names

**❌ WRONG:**
```python
def do_it(data):  # What does it do?
def process(x):   # Process what? How?
def handle(conv): # Handle how?
```

**✅ RIGHT:**
```python
def detect_incomplete_work(conversation: dict) -> list[str]:
def parse_conversation_log(log_path: str) -> dict:
def format_drift_output(detections: list) -> str:
```

### 6. Missing Type Hints

**❌ WRONG:**
```python
def analyze(conv, types):  # What types are these?
    return process(conv, types)
```

**✅ RIGHT:**
```python
def analyze(
    conv: dict,
    types: list[str]
) -> dict[str, list[str]]:
    return process(conv, types)
```

## Testing Issues

### 7. Tests That Don't Test Behavior

**❌ WRONG:**
```python
def test_detector():
    detector = DriftDetector()
    assert detector is not None  # Useless test
    assert hasattr(detector, 'detect')  # Tests implementation
```

**✅ RIGHT:**
```python
def test_detector_finds_incomplete_work():
    detector = DriftDetector()
    conversation = load_fixture('conversation_with_incomplete_work.json')

    result = detector.detect('incomplete_work', conversation)

    assert len(result) > 0
    assert 'incomplete' in result[0].lower()
```

### 8. Missing Edge Cases

**❌ INCOMPLETE:**
```python
def test_parse_conversation():
    # Only tests happy path
    conv = {"messages": [{"role": "user", "content": "hi"}]}
    result = parse_conversation(conv)
    assert len(result["messages"]) == 1
```

**✅ COMPLETE:**
```python
def test_parse_conversation_valid():
    conv = {"messages": [{"role": "user", "content": "hi"}]}
    result = parse_conversation(conv)
    assert len(result["messages"]) == 1

def test_parse_conversation_empty():
    conv = {"messages": []}
    result = parse_conversation(conv)
    assert len(result["messages"]) == 0

def test_parse_conversation_invalid_json():
    with pytest.raises(ValueError, match="Invalid JSON"):
        parse_conversation("not json")

def test_parse_conversation_missing_messages_key():
    with pytest.raises(KeyError, match="messages"):
        parse_conversation({"other_key": "value"})
```

## Documentation Issues

### 9. Code Changes Without Documentation Updates

**❌ WRONG:**
```python
# New feature added to analyzer.py
class DriftAnalyzer:
    def __init__(self, config: dict, plugins: list):  # plugins is NEW
        self.config = config
        self.plugins = plugins  # New parameter!
        # But docstring not updated! Missing plugins parameter!
```

**✅ RIGHT:**
```python
# analyzer.py - Code and docstring updated
class DriftAnalyzer:
    def __init__(self, config: dict, plugins: list):
        """Initialize drift analyzer.

        -- config: Configuration dictionary
        -- plugins: List of validation plugins to load  # NEW parameter documented
        """
        self.config = config
        self.plugins = plugins
```

**Why it matters:** Outdated documentation confuses users and wastes time.

### 10. Missing or Poor Docstrings

**❌ WRONG:**
```python
def detect(conv, type):
    """Detect drift."""  # Too vague
```

**✅ RIGHT:**
```python
def detect_drift(
    conversation: dict,
    drift_type: str
) -> list[str]:
    """Detect specific drift type in conversation.

    Performs single-pass LLM analysis to identify instances
    of the specified drift type.

    -- conversation: Parsed conversation log dictionary
    -- drift_type: Type of drift to detect (e.g., 'incomplete_work')

    Returns list of detected drift instances with descriptions.
    Raises ValueError if drift_type is not recognized.
    """
```

## Security Issues

### 10. Logging Sensitive Data

**❌ WRONG:**
```python
logger.info(f"API key: {api_key}")  # Never log secrets!
logger.debug(f"Auth token: {token}")
```

**✅ RIGHT:**
```python
logger.info("API key configured")
logger.debug("Authentication successful")
```

### 11. Unsafe File Operations

**❌ WRONG:**
```python
def load_file(user_input):
    # No validation - path traversal vulnerability!
    with open(user_input) as f:
        return f.read()
```

**✅ RIGHT:**
```python
from pathlib import Path

def load_file(file_path: str) -> str:
    path = Path(file_path).resolve()

    # Validate path is in allowed directory
    if not path.is_relative_to(ALLOWED_DIR):
        raise ValueError(f"Path not allowed: {file_path}")

    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    return path.read_text()
```

## Quick Reference

**Flag for immediate fix:**
- Inline imports
- Hardcoded credentials
- Missing error handling on I/O
- No tests for new code
- Linting errors

**Request changes:**
- Code duplication
- Poor naming
- Missing type hints
- Insufficient test coverage
- Missing docstrings

**Suggest improvements:**
- Refactoring opportunities
- Performance optimizations
- Better abstractions
- Additional tests for edge cases
