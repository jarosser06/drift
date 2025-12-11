---
name: git-commits
description: Commit message format and requirements
---

# Git Commit Message Standards

## Format

**MUST**: Use format: `<action> <what changed>` with optional why

**MUST**: State what changed - be direct and specific

## When to Include Why

**MUST**: Include why ONLY if explicitly known

**MUST NOT**: Make AI assumptions about intent

**MUST NOT**: Add boilerplate or filler content

## Length Requirements

**MUST**: Keep it tight

**MUST**: Title: 50-72 characters maximum

**MUST**: Body: Optional, use ONLY when necessary

**MUST**: Maximum 5 lines of actual content (not counting footer)

## Commit Structure

**MUST**: Commits are logical and atomic

**MUST**: Commit messages are descriptive

## Branch Hygiene

**MUST**: No merge conflicts

**MUST**: Branch is up to date with main

**MUST NOT**: Commit unintended files

## Rationale

Concise, factual commit messages improve git history readability. Atomic commits make it easier to understand changes, review code, and revert if needed. Avoiding speculation keeps the history accurate and trustworthy.
