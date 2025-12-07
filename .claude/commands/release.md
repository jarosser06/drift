---
description: Assist with creating a new release of ai-drift package
skills:
  - release
---

Create a new release of the ai-drift package.

**CRITICAL**: You MUST activate ALL skills listed in frontmatter using the Skill tool before proceeding.

**MANDATORY REQUIREMENTS**:
- You MUST use `./scripts/bump-version.sh` to update version in pyproject.toml - DO NOT EDIT MANUALLY
- You MUST use `./scripts/update-changelog.sh` to update CHANGELOG.md - DO NOT EDIT MANUALLY

Steps:
1. **REQUIRED**: Activate skill: `Skill(release)`
2. Follow release skill guidance to create new release
