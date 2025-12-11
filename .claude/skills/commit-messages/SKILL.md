---
name: commit-messages
description: Expert in writing concise, factual git commit messages for Drift project without AI fluff. Use when committing code changes, creating releases, or reviewing commit history before PRs.
version: 1.0.0
dependencies: []
---

# Commit Messages Skill

Learn how to write concise, factual commit messages that describe **what changed**, not benefits or AI-generated fluff.

## How to Write Commit Messages

Use this format:

```
<action> <what changed>

[Optional: Why, if explicitly known from issue/user/context]
```

### Examples

**Good commit messages:**

```
Add default failure messages to all validators

Validators now provide default_failure_message and default_expected_behavior
properties. Makes failure_message and expected_behavior optional in ValidationRule.
```

```
Fix mypy type errors from optional failure_message

Changed validators to use _get_failure_message() helper instead of accessing
rule.failure_message directly to handle Optional[str] correctly.
```

```
Add support for custom validator plugins
```

**What makes these good:**
- States what changed clearly
- Includes technical details when helpful
- Why is explicit (known from code context)
- No fluff or assumptions

## What NOT to Do

❌ **Too much fluff:**
```
Add default failure messages to validators

This commit adds default failure message support to all validators,
improving the developer experience by making custom messages optional.
This will help users get started faster and reduce boilerplate.

Benefits:
- Less configuration required
- Better developer experience
- Consistent error messages

Testing:
- Added 42 new tests
- All tests passing
- Coverage increased
```

**Problems:**
- Lists benefits (speculation)
- Testing details (irrelevant to commit message)
- Repetitive statements
- Way too long

❌ **Made-up context:**
```
Fix mypy type errors

This fixes type errors to improve code quality and maintainability.
The changes ensure better type safety across the codebase.
```

**Problems:**
- "Improve code quality" - generic, assumed benefit
- "Better type safety" - vague, not specific
- Doesn't explain what errors or how fixed

❌ **Too vague:**
```
Update validators

Made improvements to the validator system for better functionality.
```

**Problems:**
- "Update" without specifics
- "Improvements" and "better functionality" say nothing
- Reader has no idea what changed

## Action Words to Use

Start commits with these verbs:

- **Add** - New feature, file, function, test
- **Fix** - Bug fix, error correction
- **Update** - Modify existing code
- **Remove** - Delete code, files, features
- **Refactor** - Restructure without changing behavior
- **Rename** - Change names of files, functions, variables
- **Move** - Relocate code
- **Extract** - Pull code into separate function/file
- **Merge** - Combine branches, resolve conflicts

### Examples

```
Add JSON output format for CI/CD integration
Fix circular dependency detection in validator graph
Update frontmatter schema to allow optional fields
Remove deprecated validate_v1() method
Refactor DocumentBundle to use dataclass
Rename ValidationPhase to AnalysisPhase
Move validation logic to validators module
Extract file reading into FileLoader class
```

## When to Include Context (The "Why")

Include why ONLY when:

### 1. Explicitly stated in the issue

```
Fix circular dependency detection per #123

Issue reported that validator dependencies weren't checked for cycles.
```

### 2. User directly told you

```
Add JSON output format

User requested JSON output for CI/CD pipeline integration.
```

### 3. Obvious from the code

```
Fix off-by-one error in line counting

Line numbers were 1-indexed in output but 0-indexed internally.
```

### 4. Breaking change explanation

```
Remove deprecated validate_v1() method

Deprecated in v0.4.0, removed in v0.6.0 per deprecation policy.
```

## When NOT to Include Context

Don't include context when:

❌ You're guessing about benefits:
```
Add default messages  # Don't add: "to improve developer experience"
```

❌ You're assuming user intent:
```
Fix type errors  # Don't add: "to improve maintainability"
```

❌ You're adding generic statements:
```
Update validators  # Don't add: "for better code quality"
```

❌ You're listing what you tested:
```
Add feature  # Don't add: "Added 10 tests, all passing"
```

## How to Keep Commits Concise

### Keep Title Short

**Good titles (under 72 characters):**
```
Add default validator failure messages
Fix mypy errors in optional message handling
Update schema validator to support nested objects
```

**Too long:**
```
Add support for default failure messages to all validators in the validation system  # 88 chars!
```

**How to shorten:**
```
Add default failure messages to validators  # 46 chars
```

### Keep Body Minimal

Use body only when title isn't enough to explain **what** changed.

**When body helps:**
```
Add config validation on startup

Validates .drift_rules.yaml schema before running analysis.
Catches configuration errors early with clear messages.
```

**When body is unnecessary:**
```
Fix typo in README  # No body needed - title says it all
```

### Avoid Listing Changes

❌ **Don't do this:**
```
Update validation system

Changes:
- Added default messages
- Fixed type errors
- Updated tests
- Improved documentation
```

✅ **Make separate commits:**
```
Commit 1: Add default validator failure messages
Commit 2: Fix mypy errors in optional message handling
Commit 3: Update validator documentation
```

## Real-World Examples from Drift

### Adding Features

```
Add rule_validation for Claude Code rules

Validates .claude/rules/*.md files following same pattern as
skill_validation, agent_validation, command_validation.
```

### Fixing Bugs

```
Fix circular dependency detection for nested deps

Wasn't detecting cycles through transitive dependencies.
Now traverses full dependency graph.
```

### Refactoring

```
Extract phase validation into PhaseValidator class

Moves phase validation logic from Analyzer to dedicated validator.
No behavior changes.
```

### Configuration Changes

```
Update .drift_rules.yaml schema to v2

Adds support for optional phase parameters and resource_patterns.
Backward compatible with v1 schema.
```

## Common Scenarios

### After fixing linting errors

```
Fix flake8 errors in validators module
```

Not:
```
Fix linting errors to improve code quality and maintain standards  # Too much!
```

### After code review feedback

```
Rename analyze() to run_analysis() per review

Makes purpose clearer when called from CLI.
```

Not:
```
Refactor code based on review feedback to improve clarity  # Vague!
```

### After adding tests

```
Add tests for BlockLineCountValidator edge cases
```

Not:
```
Add comprehensive test coverage with 15 new tests covering edge cases  # Details irrelevant!
```

### When implementing from issue

```
Add argument-hint support to commands per #45

Enables tab-completion hints for command parameters.
```

## Quick Reference

**Template:**
```
<action> <specific change>

[Optional 1-2 lines explaining what/why if not obvious from title]
```

**Good:**
- Specific and factual
- 50-72 char title
- Optional 1-3 line body
- Known context only

**Bad:**
- Generic or vague
- Lists benefits
- Lists testing
- Makes assumptions
- Too long (>5 lines)

**Remember:** You're writing for developers reading `git log`. They want to know **what changed** quickly. Everything else is noise.
