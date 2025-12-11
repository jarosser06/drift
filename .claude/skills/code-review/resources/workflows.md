# Code Review Workflows

Detailed workflows for conducting code reviews using GitHub MCP.

## Complete PR Review Workflow

```python
# 1. Get PR information
pr = mcp__github__get_pull_request(owner, repo, pull_number=42)
print(f"Reviewing: {pr['title']}")

# 2. Get changed files
files = mcp__github__get_pull_request_files(owner, repo, pull_number=42)
print(f"Changed files: {len(files)}")

# 3. Check CI status
status = mcp__github__get_pull_request_status(owner, repo, pull_number=42)
if status['state'] != 'success':
    print("⚠️ CI checks failing")

# 4. Review each file
issues = []
for file in files:
    # Review code
    # Identify issues
    # Add to issues list
    pass

# 5. Prioritize issues
critical = [i for i in issues if i['severity'] == 'critical']
important = [i for i in issues if i['severity'] == 'important']
minor = [i for i in issues if i['severity'] == 'minor']

# 6. Determine review decision
if critical:
    event = "REQUEST_CHANGES"
elif important:
    event = "REQUEST_CHANGES"
else:
    event = "APPROVE"

# 7. Submit review
mcp__github__create_pull_request_review(
    owner, repo,
    pull_number=42,
    body=generate_review_summary(critical, important, minor),
    event=event,
    comments=[format_comment(i) for i in issues]
)
```

## Quick Review Workflow

For small PRs (< 5 files, < 100 lines):

```python
# 1. Get PR and files
pr = mcp__github__get_pull_request(owner, repo, pull_number)
files = mcp__github__get_pull_request_files(owner, repo, pull_number)

# 2. Quick checks
- Tests included?
- Linters passing?
- Docs updated?

# 3. Quick review
- Read the diff
- Check for obvious issues
- Verify tests

# 4. Approve or comment
mcp__github__create_pull_request_review(
    owner, repo, pull_number,
    body="LGTM! Quick and clean fix.",
    event="APPROVE"
)
```

## How to Submit Reviews via MCP

### Approve PR

```python
mcp__github__create_pull_request_review(
    owner="jarosser06",
    repo="drift",
    pull_number=42,
    body="""Great work! Code quality is excellent, tests are comprehensive,
and documentation is thorough.

Key strengths:
- Clean, readable code
- 95% test coverage with edge cases
- Well-documented API changes
- Follows project patterns

Ready to merge.""",
    event="APPROVE"
)
```

### Request Changes

```python
mcp__github__create_pull_request_review(
    owner="jarosser06",
    repo="drift",
    pull_number=42,
    body="""Thanks for the PR! The implementation looks solid overall, but
there are a few issues that need attention before merging.

Summary:
- 1 critical security issue (see inline comments)
- 2 important test gaps
- 1 documentation update needed

Please address these and re-request review.""",
    event="REQUEST_CHANGES",
    comments=[
        {
            "path": "src/drift/api.py",
            "line": 45,
            "body": """🔴 CRITICAL: API key exposed in logs

Current code logs API key in plaintext:
```python
logger.debug(f"Using API key: {api_key}")
```

Fix:
```python
logger.debug("Using API key: [REDACTED]")
```"""
        },
        {
            "path": "tests/test_detector.py",
            "line": 23,
            "body": """⚠️ Missing edge case test

Please add test for empty conversation:
```python
def test_detect_empty_conversation():
    result = detector.detect({"messages": []})
    assert result == []
```"""
        },
        {
            "path": "src/drift/validators.py",
            "line": 78,
            "body": """⚠️ Missing docstring

Please add docstring to CustomValidator class documenting:
- Purpose
- Parameters
- Return type
- Example usage"""
        }
    ]
)
```

### Comment Without Blocking

```python
mcp__github__create_pull_request_review(
    owner="jarosser06",
    repo="drift",
    pull_number=42,
    body="""Looks good overall! A few suggestions for improvement,
but nothing blocking.""",
    event="COMMENT",
    comments=[
        {
            "path": "src/drift/cli.py",
            "line": 67,
            "body": """💡 SUGGESTION: Extract helper function

Consider extracting this into `_parse_drift_types()` for testability:
```python
def _parse_drift_types(args):
    if args.drift_type:
        return args.drift_type
    return config.get('drift_types', DEFAULT_TYPES)
```"""
        }
    ]
)
```
