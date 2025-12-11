---
name: github-operations
description: Expert in GitHub workflows including issue management, PR operations, and branch conventions. Use when working with GitHub via MCP.
---

# GitHub Operations Skill

Learn how to work with GitHub via MCP tools for the Drift project.

## How to Determine Repository Information

Before using any GitHub MCP tools, determine the actual repository owner and name from git:

```bash
git remote get-url origin
```

Parse the output to extract owner and repository name:

**Example outputs:**
```
https://github.com/jarosser06/drift.git → owner: jarosser06, repo: drift
git@github.com:jarosser06/drift.git → owner: jarosser06, repo: drift
```

Check git first before any GitHub operations to get accurate repository information.

## How to Use GitHub MCP Tools

### Issue Operations

**Get issue details:**
```python
mcp__github__get_issue(
    owner="jarosser06",
    repo="drift",
    issue_number=42
)
```

Returns full issue details including title, body, labels, assignees, state, comments.

**List issues with filters:**
```python
mcp__github__list_issues(
    owner="jarosser06",
    repo="drift",
    state="open",              # open, closed, all
    assignee="username",       # filter by assignee
    labels=["bug"],            # filter by labels
    sort="created",            # created, updated, comments
    direction="desc"           # asc or desc
)
```

**Create new issue:**
```python
mcp__github__create_issue(
    owner="jarosser06",
    repo="drift",
    title="Add support for custom validators",
    body="## Problem\nUsers need to define custom validators...",
    labels=["enhancement"],
    assignees=["username"]
)
```

**Update existing issue:**
```python
mcp__github__update_issue(
    owner="jarosser06",
    repo="drift",
    issue_number=42,
    title="Updated title",
    body="Updated description",
    state="closed",            # open or closed
    labels=["bug", "priority:high"],
    assignees=["username"]
)
```

**Add comment to issue:**
```python
mcp__github__add_issue_comment(
    owner="jarosser06",
    repo="drift",
    issue_number=42,
    body="Fixed in PR #50"
)
```

### Pull Request Operations

**Create pull request:**
```python
mcp__github__create_pull_request(
    owner="jarosser06",
    repo="drift",
    title="Issue #42: Add custom validator support",
    head="issue-42-custom-validators",    # branch with changes
    base="main",                          # target branch
    body="## Summary\n- Adds CustomValidator class\n- Updates config schema",
    draft=False
)
```

**Get PR details:**
```python
mcp__github__get_pull_request(
    owner="jarosser06",
    repo="drift",
    pull_number=50
)
```

Returns PR metadata, description, status, review state, mergability.

**List pull requests:**
```python
mcp__github__list_pull_requests(
    owner="jarosser06",
    repo="drift",
    state="open",              # open, closed, all
    head="user:branch-name",   # filter by source branch
    base="main",               # filter by target branch
    sort="created",            # created, updated, popularity, long-running
    direction="desc"           # asc or desc
)
```

**Review pull request:**
```python
mcp__github__create_pull_request_review(
    owner="jarosser06",
    repo="drift",
    pull_number=50,
    body="Overall looks good. Please address inline comments.",
    event="REQUEST_CHANGES",   # APPROVE, REQUEST_CHANGES, COMMENT
    comments=[{
        "path": "src/drift/validators.py",
        "line": 45,
        "body": "Add type hint for return value"
    }, {
        "path": "tests/test_validators.py",
        "line": 23,
        "body": "Add test for edge case with empty input"
    }]
)
```

**Merge pull request:**
```python
mcp__github__merge_pull_request(
    owner="jarosser06",
    repo="drift",
    pull_number=50,
    merge_method="squash",     # merge, squash, rebase
    commit_title="Add custom validator support",
    commit_message="Implements CustomValidator class with config schema updates"
)
```

**Get files changed in PR:**
```python
mcp__github__get_pull_request_files(
    owner="jarosser06",
    repo="drift",
    pull_number=50
)
```

Returns list of files with additions, deletions, changes, patch data.

**Get PR CI status:**
```python
mcp__github__get_pull_request_status(
    owner="jarosser06",
    repo="drift",
    pull_number=50
)
```

Returns combined status of all CI checks (tests, linting, etc.).

### Branch Operations

**Create new branch:**
```python
mcp__github__create_branch(
    owner="jarosser06",
    repo="drift",
    branch="issue-42-custom-validators",
    from_branch="main"         # optional, defaults to default branch
)
```

Creates branch on GitHub. You'll still need to fetch and checkout locally:

```bash
git fetch origin
git checkout issue-42-custom-validators
```

### Repository Operations

**Get file contents:**
```python
mcp__github__get_file_contents(
    owner="jarosser06",
    repo="drift",
    path="src/drift/config.py",
    branch="main"              # optional, defaults to default branch
)
```

Returns file content, SHA, and metadata.

**Create or update single file:**
```python
mcp__github__create_or_update_file(
    owner="jarosser06",
    repo="drift",
    path="src/drift/new_module.py",
    content="# New module\n\ndef new_function():\n    pass",
    message="Add new module for custom validators",
    branch="issue-42-custom-validators",
    sha="abc123..."            # required for updates, get from get_file_contents
)
```

**Push multiple files in single commit:**
```python
mcp__github__push_files(
    owner="jarosser06",
    repo="drift",
    branch="issue-42-custom-validators",
    files=[
        {
            "path": "src/drift/validators.py",
            "content": "# Updated validator code..."
        },
        {
            "path": "tests/test_validators.py",
            "content": "# New tests..."
        }
    ],
    message="Add custom validator with tests"
)
```

Use this for multi-file changes in a single commit.

### Search Operations

**Search repositories:**
```python
mcp__github__search_repositories(
    query="drift language:python stars:>10",
    page=1,
    perPage=30
)
```

**Search code across GitHub:**
```python
mcp__github__search_code(
    q="parse_conversation language:python",
    per_page=30,
    page=1
)
```

**Search issues and PRs:**
```python
mcp__github__search_issues(
    q="is:open label:bug repo:jarosser06/drift",
    sort="created",
    order="desc"
)
```

Search syntax supports many filters: `is:issue`, `is:pr`, `label:bug`, `author:username`, etc.

## How to Follow Git Workflows

See [Git Workflows](resources/git-workflows.md) for detailed guides on:
- Standard development workflow (5 steps)
- Assigning issues to yourself
- Closing issues with comments
- Requesting PR changes
- Approving and merging PRs

## How to Organize with Labels

### Common Label Patterns

**Issue type labels:**
- `bug` - Something isn't working correctly
- `enhancement` - New feature or improvement request
- `documentation` - Documentation improvements or fixes
- `refactoring` - Code restructuring without behavior change

**Priority labels:**
- `priority:high` - Needs immediate attention
- `priority:medium` - Important but not urgent
- `priority:low` - Nice to have, can wait

**Status labels:**
- `good first issue` - Good for newcomers to the project
- `help wanted` - Extra attention needed
- `in progress` - Currently being worked on
- `blocked` - Blocked by dependencies or decisions

### How to Apply Labels

**When creating issue:**
```python
mcp__github__create_issue(
    owner="jarosser06",
    repo="drift",
    title="Add support for custom validators",
    body="...",
    labels=["enhancement", "priority:high"]
)
```

**Update labels on existing issue:**
```python
mcp__github__update_issue(
    owner="jarosser06",
    repo="drift",
    issue_number=42,
    labels=["enhancement", "priority:high", "in progress"]
)
```

**Filter issues by labels:**
```python
mcp__github__list_issues(
    owner="jarosser06",
    repo="drift",
    state="open",
    labels=["bug", "priority:high"]
)
```

### How to Search by Labels

Use GitHub search syntax:
```python
mcp__github__search_issues(
    q="is:open label:bug label:priority:high repo:jarosser06/drift",
    sort="created",
    order="desc"
)
```

Supports complex queries:
- `is:issue` or `is:pr` - Filter by type
- `label:bug` - Has label
- `no:label` - No labels
- `author:username` - Created by user
- `assignee:username` - Assigned to user
- `is:open` or `is:closed` - Filter by state

## Example Workflows

See [Workflows](resources/workflows.md) for common GitHub workflows:
- Working on new feature (end-to-end)
- Reviewing PR
- Bulk issue management

## Resources

### 📖 [Workflows](resources/workflows.md)
Common GitHub workflows using MCP tools.

**Use when:** Need examples for standard GitHub operations via MCP.

### 📖 [Git Workflows](resources/git-workflows.md)
Standard git development workflows with MCP integration.

**Use when:** Following standard development workflow or managing PRs and issues.
