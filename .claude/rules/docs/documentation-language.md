---
name: documentation-language
description: Objective language requirements for documentation
path: "{docs/**/*,*.md,*.rst}"
---

# Documentation Language Standards

## Prohibited Claims

**MUST NOT**: Make false claims about user behavior without data

**MUST NOT**: Use phrases like:
- "most users", "many users"
- "typically", "commonly", "usually"
- ANY claim about what users do without hard data

## Prohibited Subjective Adjectives

**MUST NOT**: Use subjective language such as:
- easily, simply, just
- obviously, clearly
- powerful, elegant, beautiful
- amazing, best, better, great, excellent
- effortlessly, seamlessly, straightforward

## Required Content Standards

**MUST**: Objective language only

**MUST**: Complete examples (no undefined variables or missing context)

**MUST**: Version-aware documentation (specify versions when relevant)

**MUST**: Include source citations for recommendations

**Valid sources**: Python official docs, library official docs, PEPs, project's own docs

## TODOs

**MUST NOT**: Include TODOs in code
