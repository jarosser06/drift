# Git Workflow Patterns

Standard git workflows for the Drift project.

## Standard Development Workflow

**Step 1: Update main branch**
```bash
git checkout main
git pull origin main
```

**Step 2: Create feature branch**

Locally:
```bash
git checkout -b issue-42-custom-validators
```

Or via MCP (creates on GitHub):
```python
mcp__github__create_branch(
    owner="jarosser06",
    repo="drift",
    branch="issue-42-custom-validators",
    from_branch="main"
)
```

Then fetch locally:
```bash
git fetch origin
git checkout issue-42-custom-validators
```

**Step 3: Make changes and commit**
```bash
# Make your code changes
git add .
git commit -m "Add custom validator support

- Implement CustomValidator base class
- Add config schema validation
- Update documentation

```

**Step 4: Push branch**
```bash
git push -u origin issue-42-custom-validators
```

**Step 5: Create pull request**
```python
mcp__github__create_pull_request(
    owner="jarosser06",
    repo="drift",
    title="Issue #42: Add custom validator support",
    head="issue-42-custom-validators",
    base="main",
    body="## Summary\n- Adds CustomValidator class\n- Updates config schema\n\n## Test Plan\n- [x] Unit tests pass\n- [x] Coverage ≥ 90%"
)
```

## How to Assign Issue to Yourself

```python
# First, determine your username (or get from git config)
# Then update the issue:
mcp__github__update_issue(
    owner="jarosser06",
    repo="drift",
    issue_number=42,
    assignees=["your-username"]
)
```

## How to Close Issue with Comment

```python
# Add closing comment
mcp__github__add_issue_comment(
    owner="jarosser06",
    repo="drift",
    issue_number=42,
    body="Fixed in PR #50. Custom validators are now supported."
)

# Close the issue
mcp__github__update_issue(
    owner="jarosser06",
    repo="drift",
    issue_number=42,
    state="closed"
)
```

## How to Request PR Changes

```python
mcp__github__create_pull_request_review(
    owner="jarosser06",
    repo="drift",
    pull_number=50,
    body="Please address the following concerns before merging.",
    event="REQUEST_CHANGES",
    comments=[
        {
            "path": "src/drift/validators.py",
            "line": 45,
            "body": "Add input validation here to prevent empty validator names"
        },
        {
            "path": "tests/test_validators.py",
            "line": 12,
            "body": "Add test case for edge case with None input"
        }
    ]
)
```

## How to Approve and Merge PR

**Step 1: Review and approve**
```python
mcp__github__create_pull_request_review(
    owner="jarosser06",
    repo="drift",
    pull_number=50,
    body="LGTM! Tests pass, coverage is good, code looks clean.",
    event="APPROVE"
)
```

**Step 2: Check CI status**
```python
status = mcp__github__get_pull_request_status(
    owner="jarosser06",
    repo="drift",
    pull_number=50
)
# Verify all checks passed
```

**Step 3: Merge**
```python
mcp__github__merge_pull_request(
    owner="jarosser06",
    repo="drift",
    pull_number=50,
    merge_method="squash",
    commit_title="Add custom validator support",
    commit_message="Implements CustomValidator class with full test coverage"
)
```
