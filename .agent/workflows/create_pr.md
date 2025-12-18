---
description: Create a Pull Request with quality validation (tests, linting)
---

# PR Creation Workflow

## Step 1: Run Validation
// turbo
```bash
./test.sh
./lint.sh
```

## Step 2: Check Results
If validation fails, STOP and fix issues. Do not proceed to PR creation.

## Step 3: Draft PR Description

### Required Structure
Every PR description MUST include:

**Summary** (3-5 bullet points):
- What changed and why
- Focus on WHAT and WHY, not HOW

**Changes** (categorized):
- Added: New files/features
- Modified: Changed files (with line ranges if significant)
- Removed: Deleted files/features

**Related Issues**:
- Link to issue (e.g., "Closes #42")

### Example Format
```markdown
## Summary
- Added multi-drift-type analysis support
- Implemented sequential processing for each type
- Combined results in unified output format

## Changes
### Added
- `drift/multi_analyzer.py` - Multi-pass analysis
- Tests in `tests/integration/test_multi_pass.py`

### Modified
- `drift/cli.py:45-67` - Multi-type CLI support
- `README.md` - Updated usage examples

## Related Issues
Closes #42
```

### Title Format
- **With Issue**: `Issue #<number>: <Descriptive title>`
- **Without Issue**: `<Descriptive title>`
- **Length**: Under 72 characters
- **Content**: Describe WHAT changed, not how

## Step 4: Get User Approval

**CRITICAL**: Present the draft PR title and description to the user for review and approval.
- Use the `notify_user` tool to show the draft
- Wait for user confirmation
- Make any requested changes before proceeding

DO NOT proceed to Step 5 without explicit user approval.

## Step 5: Create PR

After receiving user approval, create the PR using GitHub CLI.

```bash
gh pr create --title "<approved title>" --body "<approved description>"
```
