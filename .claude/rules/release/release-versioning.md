---
name: release-versioning
description: SemVer, tagging, and changelog rules
---

# Release Versioning Standards

## Version Format

**MUST**: Use SemVer version format: `MAJOR.MINOR.PATCH`

**MUST**: Use tag format: `v{version}` (e.g., `v0.2.0`)

## Mandatory Scripts

**MUST**: Run bump-version script for version updates

**MUST**: Update changelog with script

## PyPI Constraints

**MUST**: Remember that PyPI does not allow replacing versions

## Changelog Content Rules

**MUST**: Only include changes to actual package code

**MUST NOT**: Include in changelog:
- .drift.yaml changes
- .claude/ directory changes
- docs/ changes
- README.md changes
- CLAUDE.md changes

**MUST**: Include in changelog:
- New features
- Bug fixes
- Breaking changes
- CLI changes
