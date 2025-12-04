---
name: github-operations
description: Expert in GitHub workflows including issue management, PR operations, and branch conventions. Use when working with GitHub via MCP.
---

# GitHub Operations Skill

Expert in GitHub workflows and operations using the GitHub MCP server for Drift project.

## Core Responsibilities

- Manage issues and pull requests via MCP tools
- Follow branch naming conventions
- Maintain clean Git history
- Follow contribution workflows

## IMPORTANT: Always Determine Repository Information First

**Before using any GitHub MCP tools**, you MUST determine the actual repository owner and name from git:

```bash
git remote get-url origin
```

Parse the output to extract the owner and repository name. For example:
- `https://github.com/jarosser06/drift.git` → owner: `jarosser06`, repo: `drift`
- `git@github.com:jarosser06/drift.git` → owner: `jarosser06`, repo: `drift`

Never assume or hardcode repository information. Always check git first.

## Branch Naming Convention

Format: `issue-<number>-<short-description>`

Examples:
- `issue-42-add-bedrock-support`
- `issue-15-fix-config-parsing`
- `issue-8-improve-cli-output`

Rules:
- All lowercase
- Hyphen separated
- Descriptive but concise
- Always reference issue number

## GitHub MCP Tools

### Issue Operations

**Get Issue Details:**
```
mcp__github__get_issue(owner, repo, issue_number)
```

**List Issues:**
```
mcp__github__list_issues(
    owner, repo,
    state="open",        # open, closed, all
    assignee="username", # filter by assignee
    labels=["bug"],      # filter by labels
)
```

**Create Issue:**
```
mcp__github__create_issue(
    owner, repo,
    title="Issue title",
    body="Issue description",
    labels=["enhancement"],
    assignees=["username"]
)
```

**Update Issue:**
```
mcp__github__update_issue(
    owner, repo,
    issue_number=42,
    title="Updated title",
    body="Updated description",
    state="open",        # or "closed"
    labels=["bug", "priority:high"],
    assignees=["username"]
)
```

**Add Comment:**
```
mcp__github__add_issue_comment(
    owner, repo,
    issue_number=42,
    body="Comment text"
)
```

### Pull Request Operations

**Create PR:**
```
mcp__github__create_pull_request(
    owner, repo,
    title="PR title",
    head="feature-branch",    # branch with changes
    base="main",              # target branch
    body="PR description",
    draft=False
)
```

**Get PR Details:**
```
mcp__github__get_pull_request(owner, repo, pull_number)
```

**List PRs:**
```
mcp__github__list_pull_requests(
    owner, repo,
    state="open",           # open, closed, all
    head="user:branch",     # filter by branch
    base="main",            # filter by base
    sort="created",         # created, updated, popularity
    direction="desc"        # asc or desc
)
```

**Review PR:**
```
mcp__github__create_pull_request_review(
    owner, repo,
    pull_number=42,
    body="Review comments",
    event="APPROVE",        # APPROVE, REQUEST_CHANGES, COMMENT
    comments=[{
        "path": "file.py",
        "line": 10,
        "body": "Suggestion here"
    }]
)
```

**Merge PR:**
```
mcp__github__merge_pull_request(
    owner, repo,
    pull_number=42,
    merge_method="squash",  # merge, squash, rebase
    commit_title="Title",
    commit_message="Message"
)
```

**Get PR Files:**
```
mcp__github__get_pull_request_files(owner, repo, pull_number)
```

**Get PR Status:**
```
mcp__github__get_pull_request_status(owner, repo, pull_number)
```

### Branch Operations

**Create Branch:**
```
mcp__github__create_branch(
    owner, repo,
    branch="issue-42-new-feature",
    from_branch="main"      # optional, defaults to default branch
)
```

### Repository Operations

**Get File Contents:**
```
mcp__github__get_file_contents(
    owner, repo,
    path="path/to/file.py",
    branch="main"           # optional
)
```

**Create/Update File:**
```
mcp__github__create_or_update_file(
    owner, repo,
    path="path/to/file.py",
    content="file content",
    message="Commit message",
    branch="main",
    sha="file-sha"          # required for updates
)
```

**Push Multiple Files:**
```
mcp__github__push_files(
    owner, repo,
    branch="main",
    files=[
        {"path": "file1.py", "content": "..."},
        {"path": "file2.py", "content": "..."}
    ],
    message="Commit message"
)
```

### Search Operations

**Search Repositories:**
```
mcp__github__search_repositories(
    query="drift language:python",
    page=1,
    perPage=30
)
```

**Search Code:**
```
mcp__github__search_code(
    q="parse_conversation repo:owner/drift",
    per_page=30
)
```

**Search Issues:**
```
mcp__github__search_issues(
    q="is:open label:bug repo:owner/drift",
    sort="created",
    order="desc"
)
```

## Git Workflow

### Standard Workflow

1. **Update main**
   ```bash
   git checkout main
   git pull origin main
   ```

2. **Create feature branch**
   ```bash
   git checkout -b issue-42-add-feature
   ```

   Or use MCP:
   ```
   mcp__github__create_branch(owner, repo, "issue-42-add-feature", "main")
   ```

3. **Make changes and commit**
   ```bash
   git add .
   git commit -m "Add feature X

   - Implement core functionality
   - Add tests with 90% coverage
   - Update documentation

   🤖 Generated with Claude Code
   Co-Authored-By: Claude <noreply@anthropic.com>"
   ```

4. **Push branch**
   ```bash
   git push -u origin issue-42-add-feature
   ```

5. **Create PR via MCP**
   ```
   mcp__github__create_pull_request(
       owner, repo,
       title="Issue #42: Add feature",
       head="issue-42-add-feature",
       base="main",
       body="PR description"
   )
   ```

### Commit Message Format

```
<Short summary (50 chars or less)>

<Detailed description if needed>
- Bullet points for main changes
- Reference issue numbers

🤖 Generated with Claude Code

Co-Authored-By: Claude <noreply@anthropic.com>
```

## Common Workflows

### Assign Issue to Self

```
# Get current user info first if needed, then:
mcp__github__update_issue(
    owner, repo,
    issue_number=42,
    assignees=["your-username"]
)
```

### Close Issue with Comment

```
# Add closing comment
mcp__github__add_issue_comment(
    owner, repo,
    issue_number=42,
    body="Fixed in PR #50"
)

# Close the issue
mcp__github__update_issue(
    owner, repo,
    issue_number=42,
    state="closed"
)
```

### Request PR Changes

```
mcp__github__create_pull_request_review(
    owner, repo,
    pull_number=50,
    body="Please address the following concerns before merging.",
    event="REQUEST_CHANGES",
    comments=[{
        "path": "drift/parser.py",
        "line": 45,
        "body": "This should validate input before processing"
    }]
)
```

## Labels and Organization

### Common Labels
- `bug` - Something isn't working
- `enhancement` - New feature or request
- `documentation` - Documentation improvements
- `good first issue` - Good for newcomers
- `priority:high` - High priority
- `priority:low` - Low priority

### Using Labels

```
mcp__github__update_issue(
    owner, repo,
    issue_number=42,
    labels=["bug", "priority:high"]
)
```

