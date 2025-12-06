---
name: code-review
description: Expert in conducting thorough code reviews for quality, security, and best practices. Use when reviewing code or PRs.
skills:
  - python-basics
---

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
- **CRITICAL: All imports at top of file (NO inline imports)**
- Proper import organization (stdlib → third-party → local)

**Questions to Ask:**
- Is the code self-explanatory?
- Are names descriptive and accurate?
- Is there unnecessary complexity?
- Could this be simpler?
- Are there any inline imports that need to be moved to the top?

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
- Inline comments where helpful
- **CRITICAL: Documentation updated for any code changes**
  - New attributes/parameters documented in docstrings
  - Configuration changes documented where appropriate
  - Breaking changes clearly documented
  - CLI changes reflected in help text

**Questions to Ask:**
- Can someone understand this without asking?
- Are all parameters documented?
- Do examples cover common use cases?
- Is the "why" explained for non-obvious code?
- **Do documentation updates match code changes?**
- Are all new public APIs documented?
- Are configuration changes documented?
- Are breaking changes clearly called out?

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

## Recommendations Must Be Research-Backed

**CRITICAL REQUIREMENT:** Any recommendations you make MUST be researched using authoritative sources.

### Research Requirements

**Before making ANY recommendation:**
1. Use the `mcp__context7` tools to look up best practices from official documentation
2. Verify recommendations against Python official docs, library official docs, or established standards
3. Include source citations in your feedback

**Example Research Process:**
```python
# To recommend a library or pattern, first research it:
library_id = mcp__context7__resolve_library_id(libraryName="pytest")
docs = mcp__context7__get_library_docs(
    context7CompatibleLibraryID=library_id["libraries"][0]["id"],
    topic="fixtures",
    mode="code"
)
```

### Valid Sources for Recommendations

**✅ Acceptable:**
- Python official documentation (python.org)
- Library official documentation (via Context7 MCP)
- PEP documents (Python Enhancement Proposals)
- Project's own documentation and patterns

**❌ Not Acceptable:**
- Personal opinions without research
- Assumptions about best practices
- Recommendations based on other projects without verification
- "Common knowledge" that isn't documented

### Recommendation Guidelines

**DO:**
- Research each recommendation thoroughly
- Cite specific documentation sections
- Verify the recommendation applies to the project's Python version
- Check if the pattern already exists in the codebase
- Limit recommendations to well-researched, high-impact suggestions

**DON'T:**
- Make recommendations without research
- Suggest libraries without checking their documentation
- Recommend patterns you're unsure about
- Provide excessive recommendations (quality over quantity)
- Suggest "best practices" without authoritative sources

**Example - Good Recommendation:**
```
Consider using `pytest.fixture(scope="session")` for the database connection.
According to pytest documentation [via Context7], session-scoped fixtures are
initialized once per test session, which will improve test performance.

Source: pytest official docs - Fixture scopes
```

**Example - Bad Recommendation:**
```
You should probably use a session fixture here, it's faster.
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
- Breaking changes

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
- [ ] **Documentation is complete and matches code changes**
  - [ ] Docstrings added/updated for changed functions
  - [ ] Configuration changes documented where appropriate
  - [ ] CLI help text updated if needed
  - [ ] Breaking changes clearly documented
- [ ] **Any recommendations are research-backed with citations**
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

### 📖 [Review Checklist](resources/checklist.md)
Comprehensive code review checklist covering quality, testing, security, and more.

**Use when:** Performing a code review to ensure nothing is missed.

### 📖 [Common Issues](resources/common-issues.md)
Anti-patterns and common problems to watch for in Drift code.

**Use when:** Looking for specific problems or learning what to avoid.

### 📖 [Feedback Examples](resources/feedback-examples.md)
Examples of constructive, specific code review feedback.

**Use when:** Writing review comments or learning how to give better feedback.
