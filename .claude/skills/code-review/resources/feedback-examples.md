# Code Review Feedback Examples

Examples of constructive, specific code review feedback.

## Good vs Bad Feedback

### Example 1: Error Handling

**❌ Bad:**
```
This error handling is wrong.
```

**✅ Good:**
```
The error handling here could be more specific. Instead of catching all exceptions,
consider catching specific ones like FileNotFoundError and JSONDecodeError.
This will help users understand what went wrong.

Example:
try:
    data = json.load(f)
except FileNotFoundError:
    raise FileNotFoundError(f"Config file not found: {path}")
except json.JSONDecodeError as e:
    raise ValueError(f"Invalid JSON in {path}: {e}")
```

### Example 2: Code Duplication

**❌ Bad:**
```
DRY - don't repeat yourself.
```

**✅ Good:**
```
I notice similar logic in `analyze_incomplete_work()` and `analyze_incorrect_tool()`.
Consider extracting the shared pattern into a helper:

def _analyze_drift_type(conversation: dict, drift_type: str, prompt: str) -> list[str]:
    """Shared analysis logic for drift detection."""
    response = self.llm_client.invoke(prompt)
    return self._parse_drift_response(response, drift_type)

This will make it easier to maintain and test the common logic.
```

### Example 3: Missing Tests

**❌ Bad:**
```
Need more tests.
```

**✅ Good:**
```
The new `parse_conversation()` function needs test coverage for edge cases:

1. Empty conversation: `{"messages": []}`
2. Missing "messages" key: `{"other": "data"}`
3. Invalid message format: `{"messages": ["not a dict"]}`

Please add tests to `tests/unit/test_parser.py` covering these scenarios.
Coverage should be 90%+ for this module.
```

### Example 4: Performance

**❌ Bad:**
```
This is slow.
```

**✅ Good:**
```
In `drift/detector.py:67`, the code loops through all messages for each drift type.
For large conversations (1000+ messages), this could be slow.

Consider processing all drift types in a single pass:

# Instead of:
for drift_type in types:
    for message in messages:
        check_drift(message, drift_type)

# Try:
for message in messages:
    for drift_type in types:
        check_drift(message, drift_type)

This reduces the number of message iterations from O(n*m) to O(n).
```

## Feedback by Priority

### Critical (Must Fix)

**Security Issue:**
```
🚨 Security: This code logs API keys to the console (drift/cli.py:45).

Remove this line:
    logger.debug(f"Using API key: {api_key}")

Replace with:
    logger.debug("API key configured")

API keys should never appear in logs.
```

**Broken Functionality:**
```
⚠️ This change breaks backward compatibility.

The function signature changed from:
    def analyze(log_path: str) -> dict
to:
    def analyze(log_path: str, config: dict) -> dict

But existing callers in:
- cli.py:78
- batch_processor.py:45

...don't pass the config parameter. Either:
1. Make config optional: `config: Optional[dict] = None`
2. Update all call sites in this PR
```

### Important (Should Fix)

**Code Quality:**
```
The `DriftDetector` class in `drift/core/detector.py` is doing too much.
It handles:
1. LLM client management
2. Prompt building
3. Response parsing
4. Result formatting

Consider splitting into:
- `LLMClient` - Manages Bedrock interactions
- `PromptBuilder` - Constructs prompts
- `DriftDetector` - Orchestrates detection
- `ResultFormatter` - Formats output

This will improve testability and maintainability.
```

**Missing Documentation:**
```
The new `multi_pass_analysis()` function needs a docstring explaining:
- What it does (multi-pass vs single-pass)
- Parameters (conversation, drift_types, config)
- Return value structure
- Example usage

Docstrings help future maintainers understand the code without reading implementation.
```

### Minor (Nice to Have)

**Style Improvement:**
```
Consider using a more descriptive variable name here (drift/parser.py:34):

# Current:
data = json.load(f)

# Suggestion:
conversation_data = json.load(f)

This makes it clearer what data we're loading, especially in longer functions.
```

**Refactoring Opportunity:**
```
Optional: This conditional in `format_output()` could be simplified:

# Current:
if drift_instances is not None and len(drift_instances) > 0:
    format_detections(drift_instances)

# Simpler:
if drift_instances:
    format_detections(drift_instances)

Python treats empty lists as falsy, so the explicit checks aren't needed.
```

## Positive Feedback Examples

Don't just point out problems - acknowledge good work:

**Good Test Coverage:**
```
✅ Excellent test coverage! The new tests cover:
- Happy path
- Empty input
- Invalid format
- Error conditions

Coverage is 94% for this module. Nice work!
```

**Clean Implementation:**
```
✅ Love the clean separation of concerns here. The `parse_conversation()` function
does exactly one thing and does it well. Easy to test and understand.
```

**Good Documentation:**
```
✅ Great docstring! Clear explanation of parameters and return value, with
an example. This will help future developers.
```

## Approval Examples

### Approve with Minor Suggestions

```
LGTM! Great implementation with solid test coverage.

A few minor suggestions (not blocking):
- Consider extracting the retry logic to a helper (drift/detector.py:89-102)
- The variable name `temp` on line 67 could be more descriptive

Otherwise this is ready to merge. Nice work! ✅
```

### Request Changes

```
Please address the following before merging:

**Must fix:**
1. Add error handling for missing config file (config.py:34)
2. Remove inline imports (detector.py:23, 67)
3. Increase test coverage to 90%+ (currently 78%)

**Should fix:**
4. Add docstring to `analyze_multi_pass()` (detector.py:89)
5. Extract duplicated code in analyze_* functions

**Nice to have:**
6. Consider renaming `proc()` to something more descriptive

Looking forward to the updates!
```

### Approve Simple Change

```
LGTM! Simple, focused fix with tests. Ready to merge. ✅
```

## Tips for Good Feedback

1. **Be specific** - Reference file names and line numbers
2. **Explain why** - Don't just say what's wrong, explain why it matters
3. **Provide examples** - Show what better code looks like
4. **Prioritize** - Distinguish critical from nice-to-have
5. **Be constructive** - Frame as suggestions, not demands
6. **Acknowledge good work** - Point out what's done well
7. **Ask questions** - "Is there a reason you chose X over Y?"
8. **Focus on code, not person** - "This function" not "You"
