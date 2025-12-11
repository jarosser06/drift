---
name: python-docs
description: Expert in writing PEP 257 compliant docstrings using Google-style format with custom parameter separator. Use when writing or updating Python documentation.
---

# Python Documentation Skill

Learn how to write clear, consistent Python documentation for Drift.

## How to Write Function Docstrings

Use this template for functions:

```python
def function_name(param1: str, param2: int = 0) -> bool:
    """Brief one-line description.

    Longer description if needed. Explain what the function does,
    not how it does it. Focus on the interface and behavior.

    -- param1: Description of param1
    -- param2: Description of param2 (default: 0)

    Returns description of return value.
    Raises ValueError if param1 is invalid.
    """
```

### Key Points

- First line: Brief summary ending with a period
- Blank line before extended description (if needed)
- Use `-- param:` format (custom Drift convention)
- Describe returns and exceptions
- Present tense ("Returns" not "Will return")

## How to Write Module Docstrings

Place at the very top of each module:

```python
"""Module for parsing conversation logs.

This module provides functionality to parse and validate
conversation logs from various AI agent tools.
"""

import json  # Imports come after docstring
```

### Pattern

- First line: What the module is for
- Extended description: Key functionality provided
- No need to list every function

## How to Write Class Docstrings

Document classes with their purpose and key parameters:

```python
class DriftDetector:
    """Detects drift patterns in conversation logs.

    Analyzes conversation logs using LLM-based analysis to identify
    gaps between AI behavior and user intent.

    -- provider: LLM provider to use (bedrock, anthropic, etc.)
    -- model_id: Specific model identifier
    -- config: Configuration dictionary for drift detection
    """

    def __init__(
        self,
        provider: str,
        model_id: str,
        config: dict
    ):
        """Initialize drift detector."""
        self.provider = provider
        self.model_id = model_id
        self.config = config
```

### Constructor Pattern

- Class docstring: Describe the class purpose and attributes
- `__init__` docstring: Usually just "Initialize <class name>"
- Attribute details go in class docstring, not `__init__`

## How to Document CLI Commands

Use clear help text for Click commands:

```python
@click.command()
@click.argument('log_path', type=click.Path(exists=True))
@click.option(
    '--drift-type',
    multiple=True,
    help='Drift type to detect (can specify multiple)'
)
def analyze(log_path: str, drift_type: tuple[str, ...]) -> None:
    """Analyze conversation log for drift patterns.

    Performs multi-pass analysis on the conversation log,
    checking for specified drift types.

    Examples:
        drift analyze logs/conversation.json --drift-type incomplete_work
        drift analyze logs/ --drift-type incomplete_work --drift-type specification_adherence
    """
```

### CLI Help Text Guidelines

- Command docstring: Explains what command does
- Option help: Brief, one-line description
- Include examples showing actual usage
- Use realistic file paths and option values

## Good vs Bad Examples

### Good Docstring

```python
def parse_log(path: str) -> dict:
    """Parse conversation log from JSON file.

    Reads JSON file and validates it contains required conversation
    structure (messages, metadata, timestamps).

    -- path: Path to JSON log file

    Returns parsed conversation as dictionary.
    Raises FileNotFoundError if path doesn't exist.
    Raises ValueError if JSON is invalid or missing required fields.
    """
```

### Bad Docstring

```python
def parse_log(path: str) -> dict:
    """This amazing function simply parses a log file.

    Just pass in a path and it will magically return
    a dict. TODO: Add validation.

    Implementation uses json.load() and checks for keys.
    """
```

**Problems with bad example:**
- Subjective language ("amazing", "simply", "magically")
- Vague ("just pass in a path")
- Contains TODO (use issue tracker instead)
- Includes implementation details (json.load)
- Not helpful for users

## How to Document Optional Parameters

```python
def detect_drift(
    conversation: dict,
    drift_type: str,
    config: Optional[dict] = None
) -> list[str]:
    """Detect specific drift type in conversation.

    -- conversation: Parsed conversation log dictionary
    -- drift_type: Type of drift to detect (incomplete_work, etc.)
    -- config: Optional configuration overrides. If None, uses defaults.

    Returns list of detected drift instances with descriptions.
    """
```

## How to Document Exceptions

Be specific about what exceptions can be raised and when:

```python
def load_config(path: str) -> dict:
    """Load configuration from YAML file.

    -- path: Path to YAML configuration file

    Returns parsed configuration dictionary.
    Raises FileNotFoundError if config file doesn't exist.
    Raises yaml.YAMLError if file contains invalid YAML.
    Raises ValueError if config is missing required fields.
    """
```

## How to Document Return Types

### Simple Returns

```python
def count_messages(conversation: dict) -> int:
    """Count messages in conversation.

    -- conversation: Conversation dictionary

    Returns number of messages.
    """
```

### Complex Returns

```python
def analyze_drift(conversation: dict) -> dict:
    """Analyze conversation for all drift types.

    -- conversation: Conversation dictionary

    Returns analysis results with structure:
        {
            'drift_types': ['incomplete_work', 'specification_adherence'],
            'instances': [{'type': 'incomplete_work', 'description': '...'}],
            'summary': {'total': 5, 'by_type': {...}}
        }
    """
```

## How to Use Examples in Docstrings

When functionality is complex, include examples:

```python
def filter_messages(
    messages: list[dict],
    role: Optional[str] = None,
    after: Optional[datetime] = None
) -> list[dict]:
    """Filter messages by role and/or timestamp.

    -- messages: List of message dictionaries
    -- role: Optional role to filter by ('user', 'assistant', 'system')
    -- after: Optional datetime; only return messages after this time

    Returns filtered list of messages.

    Examples:
        # Get only user messages
        user_msgs = filter_messages(messages, role='user')

        # Get messages from last hour
        recent = filter_messages(messages, after=datetime.now() - timedelta(hours=1))

        # Combine filters
        recent_user = filter_messages(messages, role='user', after=cutoff_time)
    """
```

## How to Update Documentation When Code Changes

### 1. Changed Function Signature

```python
# Before
def analyze(path: str) -> dict:
    """Analyze conversation log.

    -- path: Path to log file

    Returns analysis results.
    """

# After adding parameter
def analyze(path: str, model: str = "claude-v2") -> dict:
    """Analyze conversation log.

    -- path: Path to log file
    -- model: Model ID to use for analysis (default: claude-v2)

    Returns analysis results.
    """
```

### 2. Changed Behavior

```python
# Before
def detect_drift(conversation: dict) -> list[str]:
    """Detect all drift types in conversation.

    Returns list of drift type names found.
    """

# After changing what's returned
def detect_drift(conversation: dict) -> list[dict]:
    """Detect all drift types in conversation.

    Returns list of drift instances with detailed information.
    Each instance includes type, description, and severity.
    """
```

### 3. New Exceptions

```python
# Before
def load_file(path: str) -> str:
    """Load file contents.

    -- path: File path

    Returns file contents as string.
    Raises FileNotFoundError if file doesn't exist.
    """

# After adding validation
def load_file(path: str) -> str:
    """Load file contents.

    -- path: File path

    Returns file contents as string.
    Raises FileNotFoundError if file doesn't exist.
    Raises ValueError if file is empty or exceeds size limit.
    """
```

## How to Document Dataclasses

```python
from dataclasses import dataclass

@dataclass
class DriftResult:
    """Result of drift detection analysis.

    -- drift_type: Type of drift detected
    -- description: Human-readable description
    -- severity: Severity level (low, medium, high)
    -- location: Location in conversation where drift occurred
    """
    drift_type: str
    description: str
    severity: str
    location: dict
```

## README and Documentation Guidelines

### How to Structure README

1. **Brief description**: One paragraph explaining what the project does
2. **Quick start**: Installation and basic usage
3. **Key features**: Bulleted list
4. **Examples**: 2-3 common use cases
5. **Links**: Point to detailed docs

```markdown
# Drift

TDD framework for AI workflows - define standards, validate programmatically.

## Installation

```bash
pip install ai-drift
```

## Quick Start

```bash
# Validate project structure
drift --no-llm

# Analyze conversations
drift --days 7
```

## Features

- Programmatic validation of agent/skill/command structure
- Conversation log analysis
- Multi-provider support (Anthropic, AWS Bedrock, Claude Code CLI)
```

### When to Update README

- New user-facing features added
- CLI commands change
- Installation process changes
- Breaking changes that affect usage
- New examples worth highlighting

### What NOT to Put in README

- Internal implementation details
- Every configuration option (link to docs instead)
- Changelog (use CHANGELOG.md)
- Long explanations (link to full docs)

## Common Patterns

### Optional Config with Defaults

```python
def analyze(
    data: dict,
    config: Optional[dict] = None
) -> dict:
    """Analyze data with optional configuration.

    -- data: Data to analyze
    -- config: Optional configuration. If None, uses default configuration
        from get_default_config().

    Returns analysis results.
    """
```

### Multiple Return Types

```python
def get_result(as_dict: bool = False) -> Union[Result, dict]:
    """Get analysis result.

    -- as_dict: If True, returns dict; if False, returns Result object

    Returns Result object by default, or dict if as_dict=True.
    """
```

### Generator Functions

```python
def iter_messages(log_path: str) -> Iterator[dict]:
    """Iterate over messages in log file.

    Yields messages one at a time without loading entire file into memory.
    Useful for processing large log files.

    -- log_path: Path to conversation log file

    Yields message dictionaries.
    Raises FileNotFoundError if log file doesn't exist.
    """
```
