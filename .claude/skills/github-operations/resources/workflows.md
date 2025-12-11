# GitHub Workflows

Common GitHub workflows using MCP tools.

## Working on New Feature

```python
# 1. Get issue details
issue = mcp__github__get_issue(owner, repo, issue_number=42)

# 2. Assign to yourself
mcp__github__update_issue(owner, repo, issue_number=42, assignees=["your-username"])

# 3. Create branch via MCP
mcp__github__create_branch(owner, repo, branch="issue-42-custom-validators", from_branch="main")

# 4. Work locally
# git fetch origin
# git checkout issue-42-custom-validators
# ... make changes ...
# git commit and push

# 5. Create PR
pr = mcp__github__create_pull_request(
    owner, repo,
    title="Issue #42: Add custom validator support",
    head="issue-42-custom-validators",
    base="main",
    body="## Summary\n..."
)

# 6. After review and CI passes, merge
mcp__github__merge_pull_request(owner, repo, pull_number=pr["number"], merge_method="squash")
```

## Reviewing PR

```python
# 1. Get PR details
pr = mcp__github__get_pull_request(owner, repo, pull_number=50)

# 2. Check changed files
files = mcp__github__get_pull_request_files(owner, repo, pull_number=50)

# 3. Check CI status
status = mcp__github__get_pull_request_status(owner, repo, pull_number=50)

# 4. Leave review
mcp__github__create_pull_request_review(
    owner, repo,
    pull_number=50,
    body="Review comments here",
    event="APPROVE",  # or REQUEST_CHANGES or COMMENT
    comments=[...]
)
```

## Bulk Issue Management

```python
# List all open bugs
bugs = mcp__github__list_issues(
    owner, repo,
    state="open",
    labels=["bug"]
)

# Prioritize them
for issue in bugs:
    # Add priority label based on criteria
    if is_critical(issue):
        mcp__github__update_issue(
            owner, repo,
            issue_number=issue["number"],
            labels=issue["labels"] + ["priority:high"]
        )
```
