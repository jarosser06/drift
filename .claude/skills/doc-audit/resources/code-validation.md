# Code Example Validation Guide

This guide covers how to validate code examples in Drift documentation against the actual implementation.

## Import Path Validation

### Drift Package Structure

```
drift/
├── cli/              # CLI commands and entrypoint
├── core/             # Core analysis logic
├── config/           # Configuration handling
├── providers/        # LLM provider implementations
├── validation/       # Validation rules
├── utils/            # Utility functions
└── agent_tools/      # Agent-specific tools
```

### Common Import Patterns

**Valid Imports:**
```python
# Core functionality
from drift.core.analyzer import Analyzer
from drift.core.types import AnalysisResult

# Configuration
from drift.config.loader import load_config
from drift.config.models import DriftConfig

# Providers
from drift.providers.anthropic import AnthropicProvider
from drift.providers.bedrock import BedrockProvider

# Validation
from drift.validation.validators.core import MarkdownValidator
```

### Validation Process

1. **Use serena MCP to verify imports**:
   ```
   find_symbol(name_path_pattern="Analyzer", relative_path="src/drift/core")
   ```

2. **Check module structure**:
   ```
   get_symbols_overview(relative_path="src/drift/core/analyzer.py")
   ```

3. **Verify class/function exists**:
   ```
   search_for_pattern(substring_pattern="class Analyzer", relative_path="src/drift/core")
   ```

## CLI Command Validation

### Available Commands

Check these examples in documentation:

**Basic Usage:**
```bash
drift                    # Analyze latest conversation
drift --no-llm          # Programmatic validation only (no LLM calls)
drift --days 7          # Analyze last 7 days
drift --format json     # JSON output instead of markdown
drift --cwd /path       # Analyze different directory
```

### Validation Steps

1. Read CLI implementation:
   ```
   find_symbol(name_path_pattern="main", relative_path="src/drift/cli/main.py")
   ```

2. Check argument parser configuration

3. Verify all flags exist in implementation

4. Test examples match actual behavior

## Configuration Examples

### .drift.yaml Structure

Valid configuration structure:
```yaml
providers:
  - type: anthropic
    model: claude-sonnet-4
  - type: bedrock
    model: anthropic.claude-sonnet-4

validation:
  conversation_analysis:
    - rule: task_completion
      enabled: true
    - rule: error_handling
      enabled: true

  project_validation:
    - rule: documentation_exists
      enabled: true
```

### Validation Steps

1. Check schema in config/models.py
2. Verify rule names match validators
3. Validate provider types
4. Check model names are current

## API Method Validation

### Analyzer Class

Check these common examples:

```python
from drift.core.analyzer import Analyzer

# Initialize analyzer
analyzer = Analyzer()

# Analyze conversations
result = analyzer.analyze()
result = analyzer.analyze(days=7)
result = analyzer.analyze(no_llm=True)
```

### Validation Process

1. Find Analyzer class:
   ```
   find_symbol(name_path_pattern="Analyzer", relative_path="src/drift/core", include_body=True, depth=1)
   ```

2. Verify method signatures

3. Check parameter types match

4. Ensure return types are correct

## Provider Examples

### Anthropic Provider

```python
from drift.providers.anthropic import AnthropicProvider

provider = AnthropicProvider(
    api_key="your-api-key",
    model="claude-sonnet-4"
)
```

### Bedrock Provider

```python
from drift.providers.bedrock import BedrockProvider

provider = BedrockProvider(
    model="anthropic.claude-sonnet-4",
    region="us-west-2"
)
```

### Validation

1. Check provider implementation files
2. Verify constructor parameters
3. Check model name formats
4. Validate configuration options

## Validation Rule Examples

### Rule Configuration

```yaml
validation:
  conversation_analysis:
    - rule: task_completion
      params:
        threshold: 0.8
```

### Validation Steps

1. Find validators directory structure
2. Check rule names match file names
3. Verify parameter names
4. Validate parameter types

## Common Validation Errors

### Import Errors
- ❌ `from drift.analyzer import Analyzer` (wrong path)
- ✅ `from drift.core.analyzer import Analyzer` (correct)

### CLI Flag Errors
- ❌ `drift --fast` (doesn't exist)
- ✅ `drift --no-llm` (correct)

### Configuration Errors
- ❌ `provider: claude` (wrong provider type)
- ✅ `provider: anthropic` (correct)

### Method Signature Errors
- ❌ `analyzer.run()` (method doesn't exist)
- ✅ `analyzer.analyze()` (correct)

## Validation Checklist

- [ ] All imports use correct paths
- [ ] CLI commands match actual implementation
- [ ] Configuration examples use valid schema
- [ ] API methods exist with correct signatures
- [ ] Provider examples use correct configuration
- [ ] Validation rules match actual validators
- [ ] Parameter types are accurate
- [ ] Return types are documented correctly
- [ ] Examples are complete and runnable
- [ ] No references to deprecated APIs
