---
name: pr-writing
description: Expert in creating well-structured pull requests with clear summaries and test plans. Use when writing or structuring PRs.
---

# PR Writing Skill

Learn how to create well-structured, reviewable pull requests using the GitHub MCP server.

## How to Write PR Descriptions

### How to Structure Your PR

A well-structured PR includes:
1. **Summary** - What changed and why
2. **Test Plan** - How you verified it works
3. **Changes** - What files were affected
4. **Related Issues** - Links to relevant issues

**Example structure:**
```markdown
## Summary
- Added multi-drift-type analysis support
- Implemented sequential processing for each type
- Combined results in unified output format

## Test Plan
- [x] Unit tests added (10 new tests)
- [x] Coverage at 92%
- [x] Manual testing with multiple drift types
- [x] All linters passing

## Changes
### Added
- `drift/multi_analyzer.py` - Multi-pass analysis logic
- Tests in `tests/integration/test_multi_pass.py`

### Modified
- `drift/cli.py:45-67` - CLI multi-type support
- `README.md` - Usage examples updated

## Related Issues
Closes #42
```

### How to Write Effective Summaries

**Use bullet points (3-5 bullets):**
```markdown
## Summary
- Added multi-drift-type analysis support to CLI
- Implemented sequential processing for each drift type
- Combined results in unified output format
```

Focus on WHAT changed and WHY, not HOW:

**Good:**
```markdown
- Added caching to reduce API calls
- Improved error messages for config validation
- Fixed race condition in parallel processing
```

**Avoid:**
```markdown
- Changed line 45 in cli.py to add a new variable called cache_dict
- Updated the error handling function to print better messages
- Added a lock object to the ProcessPool initialization
```

### How to Write Test Plans

Checklist format works best:

**Good example:**
```markdown
## Test Plan
- [x] Unit tests added (12 new tests)
- [x] Coverage increased from 88% to 93%
- [x] Manual testing with 5 different config formats
- [x] Tested with both Bedrock and Anthropic API
- [x] All linters passing (./lint.sh)
```

**Avoid vague statements:**
```markdown
## Test Plan
- Tests added
- Everything works
```

### How to Document Changes

Organize by category (Added/Modified/Removed):

**Good example:**
```markdown
## Changes

### Added
- `drift/multi_analyzer.py` - Multi-pass analysis engine
- `tests/integration/test_multi_pass.py` - Integration tests
- `.drift.yaml` example with multi-type config

### Modified
- `drift/cli.py:45-67` - CLI argument parsing for multi-type
- `drift/detector.py:120-145` - Detection logic refactoring
- `README.md` - Usage examples and configuration docs

### Removed
- `drift/legacy_analyzer.py` - Deprecated single-pass analyzer
```

**Avoid unorganized lists:**
```markdown
## Changes
- cli.py
- detector.py
- multi_analyzer.py
- README.md
```

## How to Create PRs with MCP

### Basic PR Creation

```python
mcp__github__create_pull_request(
    owner="jarosser06",
    repo="drift",
    title="Issue #42: Add multi-drift-type support",
    head="issue-42-add-multi-type",
    base="main",
    body="""## Summary

- Added multi-drift-type analysis support to CLI
- Implemented sequential processing for each drift type
- Combined results in unified output format

## Test Plan

- [x] Unit tests added (10 new tests)
- [x] Coverage at 92%
- [x] Manual testing with multiple types
- [x] All linters passing

## Changes

### Added
- `drift/multi_analyzer.py` - Multi-pass analysis
- Tests in `tests/integration/test_multi_pass.py`

### Modified
- `drift/cli.py:45-67` - Multi-type support
- `README.md` - Usage examples

## Related Issues

Closes #42

""",
    draft=False
)
```

### How to Create Draft PRs

Use `draft=True` for work-in-progress PRs:

```python
mcp__github__create_pull_request(
    owner="jarosser06",
    repo="drift",
    title="WIP: Issue #42: Add multi-drift-type support",
    head="issue-42-add-multi-type",
    base="main",
    body="## Summary\n\nWork in progress...",
    draft=True
)
```

Convert to ready when done via GitHub UI or update the PR.

## How to Write Good PR Titles

**Format:** `Issue #<number>: <Descriptive title>`

**Good examples:**
- `Issue #42: Add multi-drift-type analysis support`
- `Issue #15: Fix config parser KeyError on missing sections`
- `Issue #8: Improve CLI output formatting`
- `Issue #23: Refactor detector to use plugin architecture`

**What makes these good:**
- References the issue number
- Describes what changed, not how
- Clear and specific
- Concise (under 72 characters)

**Bad examples:**
- `Update cli.py` - No context about what or why
- `Fix bug` - Which bug? What was fixed?
- `Add feature` - Which feature?
- `Issue #42` - Missing description
- `Implemented a new multi-pass analysis system with sequential processing` - Too long and detailed

## Pre-PR Workflow

### Step-by-Step Checklist

**Step 1: Run quality checks**
```bash
# Ensure all linters pass
./lint.sh

# Ensure all tests pass with coverage
./test.sh --coverage
```

**Step 2: Review your own changes**
```bash
# See full diff against main
git diff main...HEAD

# Or use GitHub's compare view
```

Look for:
- Debug code or print statements
- Commented-out code blocks
- Unrelated changes
- Missing docstrings
- TODO comments

**Step 3: Update branch with main**
```bash
# Fetch latest main
git fetch origin

# Rebase on main
git rebase origin/main

# Or merge if you prefer
git merge origin/main
```

**Step 4: Push branch to remote**
```bash
git push -u origin issue-42-add-feature

# If you rebased and already pushed
git push --force-with-lease origin issue-42-add-feature
```

**Step 5: Create PR via MCP**
```python
mcp__github__create_pull_request(
    owner="jarosser06",
    repo="drift",
    title="Issue #42: Add multi-drift-type support",
    head="issue-42-add-feature",
    base="main",
    body="<PR description>"
)
```

## How to Make PRs Reviewable

### Keep PRs Focused

**Good - focused PR:**
```markdown
## Summary
- Add caching support to reduce API calls
- Implements LRU cache with configurable size
- Add cache stats to debug output
```

Single feature, related changes.

**Bad - unfocused PR:**
```markdown
## Summary
- Add caching support
- Fix typo in README
- Refactor config loading
- Update CI workflow
- Add new validator
```

Multiple unrelated changes make review difficult.

### Break Up Large Changes

If your PR has 20+ files or 1000+ lines changed, consider breaking it up:

**Example breakdown:**
1. PR 1: "Add caching infrastructure"
   - Cache interface and base implementation
   - Configuration schema updates
   - Tests for cache module

2. PR 2: "Integrate caching in detector"
   - Add caching to detector calls
   - Update existing tests
   - Performance benchmarks

3. PR 3: "Add cache configuration"
   - CLI flags for cache control
   - Config file support
   - Documentation updates

### Provide Context in PR Description

**Good context:**
```markdown
## Summary
- Fixed race condition in parallel processing

## Background
Previously, multiple workers could access the shared result dict
simultaneously without synchronization, causing occasional data loss.
This happened about 1 in 50 runs when using --parallel flag.

## Solution
- Added threading.Lock around result updates
- Verified fix with 1000 test runs
```

**Bad - no context:**
```markdown
## Summary
- Fixed bug in parallel processing
```

### Highlight Important Files

If your PR has many files, call out the key ones:

```markdown
## Changes

### Key Files to Review
1. `drift/multi_analyzer.py` - Core logic for multi-pass analysis
2. `tests/integration/test_multi_pass.py` - Integration test coverage

### Supporting Changes
- `drift/cli.py:45-67` - CLI integration
- `README.md` - Documentation updates
```

## Resources

### 📖 [PR Template](resources/template.md)
Complete pull request templates for features, bug fixes, and refactoring.

**Use when:** Creating a new pull request and need structure.

### 📖 [Good PR Examples](resources/good-examples.md)
Real examples of excellent pull requests with annotations.

**Use when:** Learning what makes a good PR or validating your PR before creating it.

## Common PR Workflows

### Creating PR After Feature Work

```python
# 1. Ensure quality
# Run ./lint.sh and ./test.sh --coverage

# 2. Update branch
# git fetch && git rebase origin/main

# 3. Push
# git push -u origin issue-42-add-feature

# 4. Create PR
pr = mcp__github__create_pull_request(
    owner="jarosser06",
    repo="drift",
    title="Issue #42: Add custom validator support",
    head="issue-42-add-feature",
    base="main",
    body="""## Summary
- Added CustomValidator base class
- Implemented plugin loading system
- Updated config schema

## Test Plan
- [x] Unit tests (12 new)
- [x] Integration tests (3 new)
- [x] Coverage at 95%
- [x] Manual testing with example validators

## Changes

### Added
- `drift/validators/custom.py` - CustomValidator class
- `tests/unit/test_custom_validator.py` - Tests

### Modified
- `drift/config.py:120-145` - Schema updates
- `README.md` - Plugin documentation

## Related Issues
Closes #42
"""
)

print(f"PR created: {pr['html_url']}")
```

### Updating PR Description

```python
# Get current PR
pr = mcp__github__get_pull_request(owner, repo, pull_number=50)

# Update with new description
mcp__github__create_or_update_file(
    owner=owner,
    repo=repo,
    path=".github/pull_request_template.md",
    content="Updated PR description...",
    message="Update PR description",
    branch=pr["head"]["ref"]
)
```
