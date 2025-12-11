---
name: repo-detection
description: Repository information detection requirements
---

# Repository Detection Standards

## Repository Information

**MUST**: Always determine repository information first

**MUST NOT**: Assume or hardcode repository information

**MUST**: Always check git first with `git remote get-url origin`

## Rationale

Hardcoded repository information breaks when code is forked or moved. Dynamic detection ensures tools work correctly across different repository contexts. This prevents bugs and reduces maintenance burden.
