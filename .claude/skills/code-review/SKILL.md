# Code Review Skill

Expert in conducting thorough, constructive code reviews using the GitHub MCP server.

## Core Responsibilities

- Review code quality and design
- Identify bugs and edge cases
- Verify test coverage and quality
- Check documentation completeness
- Ensure security best practices
- Provide actionable feedback

## Review Areas

### 1. Code Quality

**Check for:**
- Clear, readable code
- Proper naming conventions
- No code duplication (DRY principle)
- Appropriate abstraction levels
- Clean function/method boundaries
- Consistent style with codebase

**Questions to Ask:**
- Is the code self-explanatory?
- Are names descriptive and accurate?
- Is there unnecessary complexity?
- Could this be simpler?

### 2. Architecture & Design

**Check for:**
- Proper separation of concerns
- Follows project patterns
- Scalable design
- Appropriate use of abstractions
- Good error handling strategy
- Clear module boundaries

**Questions to Ask:**
- Does this fit with existing architecture?
- Is this the right abstraction level?
- Will this scale with more drift types/providers?
- Is error handling comprehensive?

### 3. Testing

**Check for:**
- Unit tests for all new code
- Integration tests for workflows
- Edge cases covered
- Coverage ≥ 90%
- Tests are clear and maintainable
- Proper use of mocks/fixtures

**Questions to Ask:**
- Are edge cases tested?
- Do tests verify behavior, not implementation?
- Are tests easy to understand?
- Is coverage comprehensive?

### 4. Documentation

**Check for:**
- Docstrings on public functions
- Clear parameter descriptions
- Return value documented
- Examples for complex features
- README updates if needed
- Inline comments where helpful

**Questions to Ask:**
- Can someone understand this without asking?
- Are all parameters documented?
- Do examples cover common use cases?
- Is the "why" explained for non-obvious code?

### 5. Security

**Check for:**
- No hardcoded credentials
- Proper input validation
- Safe handling of file paths
- No command injection risks
- Secure API key handling
- No exposure of sensitive data in logs

**Questions to Ask:**
- Could malicious input cause issues?
- Are credentials properly secured?
- Is user input validated?
- Are API keys handled safely?

### 6. Performance

**Check for:**
- Efficient algorithms
- No obvious bottlenecks
- Proper resource management
- No unnecessary API calls
- Appropriate data structures
- Reasonable memory usage

**Questions to Ask:**
- Will this perform well with large conversation logs?
- Are resources cleaned up properly?
- Could this be more efficient?
- Are there unnecessary operations?

## Review Process with MCP

### 1. Get PR Details

```python
pr = mcp__github__get_pull_request(owner, repo, pull_number)
```

### 2. Get PR Files

```python
files = mcp__github__get_pull_request_files(owner, repo, pull_number)
```

### 3. Get PR Status

```python
status = mcp__github__get_pull_request_status(owner, repo, pull_number)
```

### 4. Review Files

For each file, check:
- Code quality
- Tests included
- Documentation

### 5. Create Review

Use `mcp__github__create_pull_request_review`:

**Approve:**
```python
mcp__github__create_pull_request_review(
    owner, repo,
    pull_number=42,
    body="LGTM! Great test coverage and clean implementation.",
    event="APPROVE"
)
```

**Request Changes:**
```python
mcp__github__create_pull_request_review(
    owner, repo,
    pull_number=42,
    body="Please address the following concerns before merging.",
    event="REQUEST_CHANGES",
    comments=[
        {
            "path": "drift/parser.py",
            "line": 45,
            "body": "This should validate input before processing to prevent errors with malformed logs."
        },
        {
            "path": "tests/test_parser.py",
            "line": 20,
            "body": "Please add a test case for empty conversation logs."
        }
    ]
)
```

**Comment Only:**
```python
mcp__github__create_pull_request_review(
    owner, repo,
    pull_number=42,
    body="Few suggestions for improvement, but looks good overall.",
    event="COMMENT",
    comments=[
        {
            "path": "drift/cli.py",
            "line": 67,
            "body": "Consider extracting this into a helper function for better testability."
        }
    ]
)
```

## Feedback Guidelines

### Be Constructive

**Good:**
```
The error handling here could be more specific. Instead of catching
all exceptions, consider catching specific ones like FileNotFoundError
and JSONDecodeError. This will help users understand what went wrong.

Example:
try:
    data = json.load(f)
except JSONDecodeError as e:
    raise ValueError(f"Invalid JSON in {path}: {e}")
```

**Bad:**
```
This error handling is wrong.
```

### Be Specific

**Good:**
```
The function `analyze_drift` in drift/detector.py:45 is doing too
much. Consider splitting into:
1. `_prepare_prompt()` - Build prompt
2. `_call_llm()` - Make API call
3. `_parse_response()` - Parse response

This will make testing easier and improve readability.
```

**Bad:**
```
This function is too long.
```

### Prioritize Issues

**Critical (Must Fix):**
- Security vulnerabilities
- Bugs that will cause failures
- Missing required tests
- Breaking changes without migration

**Important (Should Fix):**
- Code quality issues
- Missing documentation
- Suboptimal architecture
- Incomplete error handling

**Minor (Nice to Have):**
- Style suggestions
- Performance micro-optimizations
- Extra documentation
- Refactoring opportunities

## Review Checklist

- [ ] Linked issue reviewed
- [ ] Acceptance criteria met
- [ ] Code quality is good
- [ ] Architecture is sound
- [ ] Tests are comprehensive (90%+ coverage)
- [ ] Documentation is complete
- [ ] No security issues
- [ ] Performance is acceptable
- [ ] Linters pass
- [ ] Manual testing performed

## Common Issues

### Code Duplication

Flag for refactoring if you see repeated patterns.

### Missing Edge Cases

Ensure tests cover:
- Invalid input
- Empty/null values
- Boundary conditions
- Error scenarios

### Insufficient Tests

Check for:
- Happy path only
- Missing edge cases
- No error handling tests
- Low coverage

## Resources

See the following resources:
- `review-checklist.md` - Complete review checklist
- `common-issues.md` - Common problems and solutions
- `feedback-examples.md` - Examples of good review feedback
