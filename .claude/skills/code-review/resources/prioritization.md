# Issue Prioritization Guide

How to prioritize issues found during code review.

## Critical (Must Fix Before Merge)

**Examples:**
- Security vulnerabilities
- Bugs that cause failures
- Breaking changes without migration path
- Missing required tests
- Data loss scenarios

**Example comment:**
```
🔴 CRITICAL: Security Vulnerability

In drift/api.py:45

API key is being logged in plaintext:
logger.debug(f"Using API key: {api_key}")

This will expose credentials in log files. Remove or redact:
logger.debug("Using API key: [REDACTED]")
```

## Important (Should Fix)

**Examples:**
- Code quality issues
- Incomplete error handling
- Missing documentation
- Suboptimal architecture
- Insufficient test coverage

**Example comment:**
```
⚠️ IMPORTANT: Missing Error Handling

In drift/config.py:78

Config loading doesn't handle YAML errors:
config = yaml.safe_load(f)

Add error handling:
try:
    config = yaml.safe_load(f)
except yaml.YAMLError as e:
    raise ValueError(f"Invalid YAML in {path}: {e}")
```

## Minor (Nice to Have)

**Examples:**
- Style suggestions
- Performance micro-optimizations
- Additional documentation
- Refactoring opportunities

**Example comment:**
```
💡 SUGGESTION: Performance Improvement

In drift/parser.py:120

This list comprehension could use a generator for large logs:

Current:
all_messages = [msg for log in logs for msg in log['messages']]

Suggested:
all_messages = (msg for log in logs for msg in log['messages'])

Only beneficial for logs with >1000 messages.
```
