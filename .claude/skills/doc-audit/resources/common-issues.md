# Common Documentation Issues for Drift

Drift-specific patterns and issues to check during documentation audits.

## CLI Command Examples

### Common Mistakes

**Issue**: Using non-existent flags
```bash
# ❌ Wrong
drift --fast
drift --verbose
drift --config /path/to/config

# ✅ Correct
drift --no-llm
drift --days 7
drift --format json
```

**Issue**: Wrong option syntax
```bash
# ❌ Wrong
drift -d 7  # Single dash might not work
drift --days=7  # Equals sign might not work

# ✅ Correct
drift --days 7
```

### Validation Checklist

Check CLI examples for:
- [ ] Only documented flags used
- [ ] Correct flag syntax
- [ ] Valid values for options
- [ ] Examples match actual help output

## Configuration File Examples

### .drift.yaml Structure Issues

**Issue**: Invalid provider types
```yaml
# ❌ Wrong
providers:
  - type: claude  # Should be 'anthropic'
  - type: openai  # Not supported

# ✅ Correct
providers:
  - type: anthropic
    model: claude-sonnet-4
  - type: bedrock
    model: anthropic.claude-sonnet-4
```

**Issue**: Invalid rule names
```yaml
# ❌ Wrong - rule names must match actual validators
validation:
  conversation_analysis:
    - rule: quality_check  # Doesn't exist
    - rule: code_review    # Doesn't exist

# ✅ Correct - actual rule names
validation:
  conversation_analysis:
    - rule: task_completion
    - rule: error_handling
```

**Issue**: Wrong configuration structure
```yaml
# ❌ Wrong - flat structure
providers: anthropic
validation: enabled

# ✅ Correct - proper nesting
providers:
  - type: anthropic
validation:
  conversation_analysis:
    - rule: task_completion
```

### Validation Steps

1. Check config/models.py for valid structure
2. Verify provider types in providers/ directory
3. Check validation rule names in validation/validators/
4. Validate YAML syntax

## Import Path Issues

### Common Wrong Patterns

**Issue**: Importing from wrong module
```python
# ❌ Wrong
from drift import Analyzer
from drift.analyzer import Analyzer
from drift.analysis import Analyzer

# ✅ Correct
from drift.core.analyzer import Analyzer
```

**Issue**: Non-existent imports
```python
# ❌ Wrong - these don't exist
from drift.cli import CLI
from drift.config import Config
from drift.validation import Validator

# ✅ Correct - actual imports
from drift.core.analyzer import Analyzer
from drift.config.loader import load_config
from drift.validation.validators.core import MarkdownValidator
```

**Issue**: Incorrect submodule imports
```python
# ❌ Wrong
from drift.providers import Provider  # Base class not directly importable

# ✅ Correct
from drift.providers.anthropic import AnthropicProvider
from drift.providers.bedrock import BedrockProvider
```

### Validation Process

Use serena MCP to verify:
```
find_symbol(name_path_pattern="Analyzer", relative_path="src/drift")
get_symbols_overview(relative_path="src/drift/core/analyzer.py")
```

## API Usage Issues

### Analyzer Class

**Issue**: Wrong method names
```python
# ❌ Wrong
analyzer.run()
analyzer.execute()
analyzer.check()

# ✅ Correct
analyzer.analyze()
```

**Issue**: Wrong parameter names
```python
# ❌ Wrong
analyzer.analyze(num_days=7)
analyzer.analyze(skip_llm=True)

# ✅ Correct
analyzer.analyze(days=7)
analyzer.analyze(no_llm=True)
```

**Issue**: Missing initialization
```python
# ❌ Wrong - missing imports or context
result = analyze()

# ✅ Correct - complete example
from drift.core.analyzer import Analyzer

analyzer = Analyzer()
result = analyzer.analyze()
```

## Provider Setup Issues

### Anthropic Provider

**Issue**: Wrong environment variable names
```python
# ❌ Wrong
os.environ["CLAUDE_API_KEY"]
os.environ["ANTHROPIC_KEY"]

# ✅ Correct
os.environ["ANTHROPIC_API_KEY"]
```

**Issue**: Wrong model names
```yaml
# ❌ Wrong - outdated or incorrect
model: claude-3-sonnet
model: claude-v4

# ✅ Correct - current model names
model: claude-sonnet-4
model: claude-opus-4
```

### Bedrock Provider

**Issue**: Wrong credential setup
```python
# ❌ Wrong - Anthropic API credentials won't work
provider = BedrockProvider(api_key="...")

# ✅ Correct - uses AWS credentials
provider = BedrockProvider(
    model="anthropic.claude-sonnet-4",
    region="us-west-2"
)
# Requires: AWS credentials configured via aws configure
```

**Issue**: Wrong model format
```yaml
# ❌ Wrong
model: claude-sonnet-4  # Missing provider prefix

# ✅ Correct
model: anthropic.claude-sonnet-4
```

## Validation Rule Issues

### Rule Names

**Issue**: Using display names instead of actual rule identifiers
```yaml
# ❌ Wrong
validation:
  conversation_analysis:
    - rule: "Task Completion"  # Display name
    - rule: "Error Handling"   # Display name

# ✅ Correct
validation:
  conversation_analysis:
    - rule: task_completion  # Actual identifier
    - rule: error_handling   # Actual identifier
```

### Rule Configuration

**Issue**: Invalid parameters
```yaml
# ❌ Wrong - parameter doesn't exist
validation:
  conversation_analysis:
    - rule: task_completion
      params:
        strictness: high  # Not a valid parameter

# ✅ Correct - valid parameters only
validation:
  conversation_analysis:
    - rule: task_completion
      enabled: true
```

## Output Format Issues

### JSON Output

**Issue**: Wrong format expectations
```python
# ❌ Wrong - doesn't return JSON string
result = analyzer.analyze(format="json")
print(result)  # This is still an object

# ✅ Correct - need to specify format in CLI
# Command line: drift --format json
```

### Markdown Output

**Issue**: Assuming Markdown methods exist
```python
# ❌ Wrong
markdown_result = analyzer.to_markdown()

# ✅ Correct - format handled by CLI
# Use: drift --format markdown (or default)
```

## Testing Examples

### Missing Test Setup

**Issue**: Examples without test context
```python
# ❌ Wrong - where did analyzer come from?
def test_analysis():
    result = analyzer.analyze()
    assert result is not None

# ✅ Correct - complete test example
def test_analysis():
    from drift.core.analyzer import Analyzer

    analyzer = Analyzer()
    result = analyzer.analyze(no_llm=True)
    assert result is not None
```

## Documentation Structure Issues

### Missing Prerequisites

**Issue**: Examples without setup instructions
```rst
Run the following command:

.. code-block:: bash

   drift --days 7
```

**Fix**: Include prerequisites
```rst
Prerequisites:
- Drift installed: ``pip install ai-drift``
- Valid .drift.yaml configuration
- ANTHROPIC_API_KEY environment variable (for LLM analysis)

Run the following command:

.. code-block:: bash

   drift --days 7
```

### Incomplete Examples

**Issue**: Snippets without context
```python
# ❌ Wrong - where is config?
config.validate()
```

**Fix**: Complete, runnable example
```python
# ✅ Correct
from drift.config.loader import load_config

config = load_config(".drift.yaml")
# Use config...
```

## Drift-Specific Checklist

- [ ] CLI commands use only valid flags
- [ ] .drift.yaml structure matches schema
- [ ] Provider types are 'anthropic' or 'bedrock'
- [ ] Rule names match actual validator identifiers
- [ ] Import paths use correct module structure
- [ ] Analyzer methods use correct names
- [ ] Environment variables use correct names
- [ ] Model names are current (claude-sonnet-4, not claude-3-sonnet)
- [ ] Examples include necessary imports
- [ ] Prerequisites are documented
- [ ] AWS vs Anthropic credentials are clear
- [ ] Output format handling is accurate
