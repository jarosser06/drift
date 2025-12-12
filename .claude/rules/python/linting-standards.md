---
name: linting-standards
description: Linter configuration and zero-tolerance policy
path: "**/*.py"
---

# Linting Standards

## Flake8 Configuration

**MUST**: Maximum line length: 100 characters

**MUST**: Ignore rules: E203, W503

## Black Configuration

**MUST**: Line length: 100 characters

## isort Configuration

**MUST**: Use profile: black

## mypy Configuration

**MUST**: Use strict mode where possible

## Zero Tolerance Policy

**MUST**: Zero linting errors in main branch

**MUST**: All code must pass linting before:
- Creating commits
- Creating PRs
- Merging to main
