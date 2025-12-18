# Commit Message Rules

Commit messages must be concise, factual, and describe **what changed**.

## Format
```
<action> <what changed>

[Optional: Why, if explicitly known from issue/user/context]
```

## Rules
1. **Title**: Under 72 characters, start with capitalized verb (Add, Fix, Update, Remove, Refactor).
2. **Body**: Use only when title isn't enough. No fluff, no benefits listing, no made-up context.
3. **Context**: Include "why" ONLY if explicit (issue link, user request).
4. **No Fluff**: Do not say "improves code quality", "cleaner code", etc.

## Accepted Verbs
- **Add**, **Fix**, **Update**, **Remove**, **Refactor**, **Rename**, **Move**, **Extract**, **Merge**.

## Examples
- `Add default failure messages to all validators`
- `Fix mypy type errors from optional failure_message`
- `Add support for custom validator plugins`
