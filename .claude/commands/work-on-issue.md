---
description: Complete workflow for implementing a GitHub issue
skills:
  - github-operations
  - python-docs
  - testing
---

Implement a complete workflow for a GitHub issue from start to finish.

**Workflow:**

1. **Fetch Issue Details**
   - Use `mcp__github__get_issue` to get full issue details
   - Understand requirements and acceptance criteria

2. **Assign Issue**
   - Assign the issue to the current user
   - Use `mcp__github__update_issue` with assignees parameter

3. **Create Branch**
   - Create feature branch: `git checkout -b issue-<number>-<short-description>`
   - Branch naming: lowercase, hyphenated, descriptive

4. **Implementation**
   - **MANDATORY:** Use the Task tool with subagent_type='developer' to implement the feature/fix
   - The developer agent will follow Python documentation standards and write clean code
   - DO NOT implement the code yourself - delegate to the developer agent

5. **Documentation Updates** (if applicable)
   - **MANDATORY:** Update `docs/` directory if changes involve:
     - New features or functionality
     - Changes to existing features or behavior
     - New validators, rules, or configuration options
     - Changes to CLI commands or usage
   - Common documentation files to update:
     - `docs/validators.md` - For validator changes
     - `docs/README.md` - For documentation build/structure changes
     - Project README.md - For user-facing feature changes
   - Use the Task tool with subagent_type='documentation' for doc updates
   - DO NOT skip this step if changes are user-facing or add/modify functionality

6. **Testing**
   - **MANDATORY:** Use the Task tool with subagent_type='qa' to create comprehensive tests
   - The qa agent will ensure 90%+ code coverage
   - DO NOT write tests yourself - delegate to the qa agent

7. **Validation**
   - Run `./lint.sh` to ensure code quality
   - Run `./test.sh --coverage` to verify coverage meets 90%+ requirement
   - Validate all requirements are met

8. **Present Summary**
   - Provide detailed summary of changes made
   - List all files created and modified
   - Show quality metrics (coverage, test counts)
   - Highlight documentation updates (if any)
   - Give user opportunity to review before committing
   - DO NOT automatically commit - wait for user to review and commit manually

**Usage:**
```
/work-on-issue <issue_number>
```

**Example:**
```
/work-on-issue 42
```

**IMPORTANT:** The assistant MUST activate the `github-operations`, `python-docs`, and `testing` skills before proceeding. DO NOT use the `gh` CLI command directly - always use the GitHub MCP server tools (mcp__github__*).

The assistant will:
1. Activate the required skills listed in the frontmatter
2. Fetch and understand the issue requirements using `mcp__github__get_issue`
3. Create a feature branch with proper naming
4. **MUST use Task tool with subagent_type='developer'** for implementation - do NOT implement code directly
5. **MUST update docs/ if changes are user-facing** - use Task tool with subagent_type='documentation' for doc updates
6. **MUST use Task tool with subagent_type='qa'** for testing - do NOT write tests directly
7. Validate quality with ./lint.sh and ./test.sh
8. Present summary of changes for user review (including documentation updates)
9. **DO NOT commit automatically** - user will review and commit when ready

This workflow ensures specialized agents handle their domains of expertise from issue assignment to implementation, and that all user-facing changes are properly documented before giving the user full control over when to commit changes.
