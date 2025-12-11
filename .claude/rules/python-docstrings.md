---
name: python-docstrings
description: PEP 257 docstring format requirements
path: "**/*.py"
---

# Python Docstring Requirements

## Format

**MUST**: Use Google-style docstrings.

**MUST**: Use custom parameter separator: `-- param1: Description`

**MUST**: Document all public modules, classes, and functions.

## Content Requirements

**MUST**: Be concise and factual.

**MUST**: Use present tense.

**MUST**: Document parameters and return values.

## Prohibited Content

**MUST NOT**: Use subjective language such as:
- easily, simply, just
- obviously, clearly
- powerful, elegant, beautiful
- amazing, best, better, great, excellent
- effortlessly, seamlessly, straightforward

**MUST NOT**: Include TODOs in docstrings.

**MUST NOT**: Include implementation details (focus on WHAT, not HOW).

**MUST NOT**: Use future tense.

## Rationale

Clear, objective documentation helps users understand code behavior without reading implementation details. The custom parameter separator maintains consistency across the Drift project while following Google-style conventions.
