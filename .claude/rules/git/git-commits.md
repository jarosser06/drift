---
name: git-commits
description: Commit message standards, commit structure, and branch hygiene requirements
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

**MUST**: Maximum 5 lines of actual content

## Footer Requirements

**MUST NOT**: Include any footer (no Claude Code attribution, no Co-Authored-By tags)

## Commit Structure

**MUST**: Commits are logical and atomic

**MUST**: Commit messages are descriptive

## Branch Hygiene

**MUST**: No merge conflicts

**MUST**: Branch is up to date with main

**MUST NOT**: Commit unintended files
