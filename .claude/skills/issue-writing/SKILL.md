---
name: issue-writing
description: Expert in creating well-structured GitHub issues with clear problem statements, specific acceptance criteria, and actionable technical context using GitHub MCP. Specializes in feature requests, bug reports, and refactoring tasks with proper labels and issue tracking. Use when creating issues before implementation, reporting bugs, or structuring project work.
---

# Issue Writing Skill

Learn how to create well-structured, actionable GitHub issues using the GitHub MCP server.

## Issue Templates

### Standard Template

```markdown
## Problem Statement

[Describe the problem or need from user perspective]
[Include current workarounds if any]
[Explain impact and who is affected]

## Proposed Solution

[Describe the solution approach]
[Include command examples or usage patterns]
[List what the tool should do]

## Acceptance Criteria

- [ ] [Specific testable criterion 1]
- [ ] [Specific testable criterion 2]
- [ ] [Specific testable criterion 3]
- [ ] Unit tests added with 90%+ coverage
- [ ] Integration tests cover end-to-end flow
- [ ] README updated with usage examples
- [ ] Error messages guide users on common issues

## Technical Notes

[Implementation approach if known]
[Edge cases to handle]
[Backward compatibility requirements]
[Error handling requirements]

## Related Issues

[Only include if there are actual related issues with issue numbers]
```

### Bug Report Template

```markdown
## Problem Statement

[Describe the bug and its impact]

Steps to reproduce:
1. [Step 1]
2. [Step 2]
3. [Observed error]

Expected: [Expected behavior]
Actual: [Actual behavior]

Impact: [Who is affected and how]

## Proposed Solution

[How to fix the bug]
[What changes are needed]

## Acceptance Criteria

- [ ] Bug fixed
- [ ] Root cause addressed
- [ ] Tests prevent regression
- [ ] Error messages improved if relevant

## Technical Notes

[Where the error occurs]
[Root cause if known]
[Edge cases to test]

## Related Issues

[Only include if there are actual related issues with issue numbers]
```

## How to Write Effective Issues

### How to Structure an Issue

A well-structured issue includes:
1. **Problem Statement** - What problem needs solving
2. **Proposed Solution** - How to address it
3. **Acceptance Criteria** - How to know when it's done
4. **Technical Notes** - Important constraints or considerations
5. **Related Issues** - Links to related work

**Example:**
```markdown
## Problem Statement

The CLI currently only supports analyzing a single drift type per run.
Users need to analyze multiple drift types in one execution to avoid
running the tool multiple times on the same conversation log.

## Proposed Solution

Add support for specifying multiple --drift-type arguments. The tool
should perform multi-pass analysis, running each drift type detection
separately and combining results in the output.

## Acceptance Criteria

- [ ] CLI accepts multiple --drift-type arguments
- [ ] Each drift type runs in separate LLM call
- [ ] Results are combined in single output
- [ ] Tests cover multi-type analysis
- [ ] Documentation updated with examples

## Technical Notes

- Maintain separate LLM calls per drift type (don't combine in single prompt)
- Consider rate limiting for multiple API calls
- Output format should clearly separate results by type
- Config merge should work with multiple types

## Related Issues

- Relates to #15 (configuration improvements)
- Blocks #22 (batch processing feature)
```

## How to Write Problem Statements

### Focus on User Impact

**Good - explains the problem:**
```markdown
## Problem Statement

The CLI currently only supports analyzing a single drift type per run.
Users must run the tool multiple times on the same log to check for
different drift patterns, which is slow and inefficient.

This impacts workflows where users want comprehensive analysis
(e.g., CI/CD pipelines checking all drift types).
```

**Avoid implementation details:**
```markdown
## Problem Statement

The drift_type variable is a string instead of a list, and the
detector.analyze() method only accepts one type at a time.
```

**Why it's better:** Users care about the problem (slow, inefficient), not the implementation detail (string vs list).

### Provide Context

**Good - includes context:**
```markdown
## Problem Statement

Users report config parsing fails with KeyError when .drift.yaml
is missing the drift_types section. This happens in:
- Fresh project setups without full config
- Minimal config files for testing
- Projects using only CLI args, not config

Expected behavior: drift_types should be optional with sensible defaults.
```

**Avoid vague descriptions:**
```markdown
## Problem Statement

Config parsing doesn't work correctly.
```

### Use Examples

**Good - concrete example:**
```markdown
## Problem Statement

The output format is inconsistent. When analyzing multiple logs:

Current behavior:
```
Log 1: drift detected
Log 2: no issues
Log 3: error
```

This makes it hard to parse programmatically or integrate with CI/CD.
```

## How to Write Proposed Solutions

### Describe the Approach

**Good - clear solution:**
```markdown
## Proposed Solution

Add support for multiple --drift-type arguments:

```bash
drift analyze log.json --drift-type incomplete_work --drift-type spec_adherence
```

The tool should:
1. Parse multiple --drift-type flags
2. Run separate LLM analysis for each type
3. Combine results in unified output format
4. Show clear separation by type in output
```

**Avoid over-specifying:**
```markdown
## Proposed Solution

Change cli.py line 45 to use drift_types as a list instead of string.
Add a for loop in detector.py around line 120 to iterate over types.
Update the DriftDetector.__init__() to accept List[str].
```

**Why it's better:** Suggests approach without dictating exact implementation. Leaves flexibility for better solutions discovered during implementation.

### Consider Alternatives

When multiple approaches exist, mention them:

```markdown
## Proposed Solution

Add caching to reduce duplicate API calls.

Options:
1. **In-memory cache** - Simple, works for single runs
2. **File-based cache** - Persists across runs, good for CI/CD
3. **Redis cache** - Distributed, best for multi-instance deployments

Recommend starting with #2 (file-based) as it balances simplicity and usefulness.
```

## How to Write Acceptance Criteria

### Make Them Testable

**Good - specific and testable:**
```markdown
## Acceptance Criteria

- [ ] CLI accepts multiple --drift-type arguments
- [ ] Each drift type runs in separate LLM call
- [ ] Results combined in single JSON output
- [ ] Exit code is 1 if any drift type detects issues
- [ ] Tests cover multi-type analysis with 90%+ coverage
- [ ] README shows multi-type usage example
```

**Avoid vague criteria:**
```markdown
## Acceptance Criteria

- [ ] Feature works correctly
- [ ] Code is tested
- [ ] Documentation updated
```

### Focus on Outcomes

**Good - outcome-focused:**
```markdown
## Acceptance Criteria

- [ ] Users can specify cache directory via --cache-dir flag
- [ ] Cached results are used when log file hasn't changed
- [ ] Cache can be cleared with --clear-cache flag
- [ ] Cache hit/miss stats shown in debug output
```

**Avoid implementation details:**
```markdown
## Acceptance Criteria

- [ ] Add cache_dir parameter to Config class
- [ ] Implement _get_cache_key() method
- [ ] Add pickle serialization for results
- [ ] Create cache/ directory in project root
```

### Include Quality Checks

Always include testing and documentation:

```markdown
## Acceptance Criteria

- [ ] <Feature criteria 1>
- [ ] <Feature criteria 2>
- [ ] Unit tests added with 90%+ coverage
- [ ] Integration tests cover end-to-end flow
- [ ] README updated with usage examples
- [ ] Error messages guide users on common issues
```

## How to Write Technical Notes

### Highlight Constraints

**Good - important constraints:**
```markdown
## Technical Notes

- Maintain backward compatibility - existing single --drift-type usage must still work
- Rate limiting: Add 1-second delay between API calls to avoid throttling
- Config validation: Validate drift types against supported list before analysis
- Error handling: If one type fails, continue with others and report partial results
```

### Suggest Approaches

**Good - helpful suggestions:**
```markdown
## Technical Notes

Potential implementation approaches:
1. Modify cli.py to accept multiple --drift-type flags (use action='append')
2. Create MultiPassAnalyzer class to orchestrate multiple detectors
3. Update output format to separate results by type (add "drift_type" field)

Consider:
- Using asyncio for parallel API calls (if rate limits allow)
- Caching to avoid re-analyzing same log multiple times
```

### Point Out Edge Cases

```markdown
## Technical Notes

Edge cases to handle:
- Empty drift_types list (should error or use defaults?)
- Duplicate drift types specified (de-duplicate or error?)
- Invalid drift type names (validate against supported list)
- Partial failures (one type succeeds, one fails)
```

### Link to Relevant Code

```markdown
## Technical Notes

Relevant code sections:
- `drift/cli.py:45-67` - Current single drift type parsing
- `drift/detector.py:120-145` - DriftDetector.analyze() method
- `drift/config.py:78-95` - Config drift_types validation

See #15 for related config improvements discussion.
```

## How to Create Issues with MCP

### Basic Issue Creation

```python
mcp__github__create_issue(
    owner="jarosser06",
    repo="drift",
    title="Add multi-drift-type analysis support",
    body="""## Problem Statement

The CLI currently only supports analyzing a single drift type per run.
Users need to analyze multiple drift types in one execution to avoid
running the tool multiple times on the same conversation log.

## Proposed Solution

Add support for specifying multiple --drift-type arguments. The tool
should perform multi-pass analysis, running each drift type detection
separately and combining results in the output.

## Acceptance Criteria

- [ ] CLI accepts multiple --drift-type arguments
- [ ] Each drift type runs in separate LLM call
- [ ] Results are combined in single output
- [ ] Tests cover multi-type analysis
- [ ] Documentation updated with examples

## Technical Notes

- Maintain separate LLM calls per drift type (don't combine in single prompt)
- Consider rate limiting for multiple API calls
- Output format should clearly separate results by type

## Related Issues

- Relates to #15 (configuration improvements)
- Blocks #22 (batch processing feature)
""",
    labels=["enhancement"],
    assignees=[]
)
```

### Issue with Labels and Assignment

```python
issue = mcp__github__create_issue(
    owner="jarosser06",
    repo="drift",
    title="Fix config parser crash on missing drift_types",
    body="""## Problem Statement

Config parser crashes with KeyError when .drift.yaml is missing
the drift_types section, even though this should be optional.

## Proposed Solution

Add proper defaults and validation for config parsing.

## Acceptance Criteria

- [ ] Parser handles missing drift_types gracefully
- [ ] Uses built-in defaults when not specified
- [ ] Tests cover missing and invalid configs

## Technical Notes

- Error occurs in config.py:load_project_config()
- Should use built-in DRIFT_TYPES constant as default
""",
    labels=["bug", "priority:high"],
    assignees=["your-username"]
)

print(f"Issue created: {issue['html_url']}")
```

## Examples by Issue Type

See [Issue Examples](resources/issue-examples.md) for complete examples:
- Feature request
- Bug report
- Refactoring task

## How to Choose Labels

**By type:** `bug`, `enhancement`, `documentation`, `refactoring`, `question`

**By priority:** `priority:high`, `priority:medium`, `priority:low`

**By area:** `cli`, `config`, `providers`, `testing`

**Example:**
```python
mcp__github__create_issue(
    owner, repo,
    title="Add caching support",
    body="...",
    labels=["enhancement", "performance", "priority:medium"]
)
```

## Common Issue Workflows

See [Issue Examples](resources/issue-examples.md) for workflows on:
- Creating issue for new feature (4 steps)
- Creating bug report (3 steps)

## Resources

### 📖 [Templates](resources/templates.md)
Issue templates for standard and bug reports.

**Use when:** Creating a new issue and need structure.

### 📖 [Issue Examples](resources/issue-examples.md)
Complete examples by issue type with workflows.

**Use when:** Need reference examples or workflow guidance.
