---
name: commit-messages
description: Expert in writing concise, factual commit messages without AI fluff
version: 1.0.0
dependencies: []
---

# Commit Messages Skill

You are an expert at writing **concise, factual commit messages** that describe **what changed**, not benefits, testing plans, or AI-generated fluff.

## Core Principles

1. **State what changed** - Be direct and specific
2. **Include why ONLY if explicitly known** - From issue, user request, or code context
3. **No AI assumptions** - Don't make up reasons or benefits
4. **No boilerplate** - No "testing", "benefits", or generic statements
5. **Keep it tight** - Short, factual, to the point

## Format

```
<action> <what changed>

[Optional: Why, if explicitly known from issue/user/context]

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

## Good Examples

```
Add default failure messages to all validators

Validators now provide default_failure_message and default_expected_behavior
properties. Makes failure_message and expected_behavior optional in ValidationRule.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

```
Fix mypy type errors from optional failure_message

Changed validators to use _get_failure_message() helper instead of accessing
rule.failure_message directly to handle Optional[str] correctly.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

```
Add support for custom validator plugins

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

## Bad Examples (DON'T DO THIS)

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

❌ **Made-up context:**
```
Fix mypy type errors

This fixes type errors to improve code quality and maintainability.
The changes ensure better type safety across the codebase.
```

❌ **Generic statements:**
```
Update validators

Made improvements to the validator system for better functionality.
```

## Action Words

Use these verbs to describe what you did:

- **Add** - New feature, file, function, test
- **Fix** - Bug fix, error correction
- **Update** - Modify existing code
- **Remove** - Delete code, files, features
- **Refactor** - Restructure without changing behavior
- **Rename** - Change names of files, functions, variables
- **Move** - Relocate code
- **Extract** - Pull code into separate function/file
- **Merge** - Combine branches, resolve conflicts

## Context Guidelines

Include context (the "why") ONLY when:

1. **Explicitly stated in the issue** - "Fix circular dependency detection per #123"
2. **User directly told you** - "User requested JSON output for CI/CD"
3. **Obvious from code** - "Fix off-by-one error in line counting"
4. **Breaking change** - "Remove deprecated validate_v1() method"

DON'T include context when:

- You're guessing about benefits
- You're assuming user intent
- You're adding generic statements like "improves maintainability"
- You're listing what you tested

## Length Guidelines

- **Title**: 50-72 characters max
- **Body**: Optional, use ONLY when necessary
- **Total**: Aim for 1-3 lines plus footer
- **Maximum**: 5 lines of actual content (not counting footer)

## Remember

You are writing for **developers reading git log**, not for documentation or marketing. They want to know **what changed** so they can understand the commit quickly. Everything else is noise.
