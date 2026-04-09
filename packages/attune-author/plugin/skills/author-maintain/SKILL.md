---
name: author-maintain
description: "Detect and regenerate all stale feature templates in one pass. Use after refactors or before releases. Triggers on: regenerate all, update stale, maintain help, refresh templates."
argument-hint: "[--dry-run]"
---

# Author Maintain

Detect and regenerate every stale feature template in one
pass. Useful after large refactors or as a release-prep
step.

## When to use

- Before a release — get all docs back in sync
- After a large refactor that touched many features
- Scheduled maintenance (weekly, monthly)

## Scoping

Use `AskUserQuestion` to confirm scope:

```yaml
question: "How should I run maintenance?"
header: "Maintain"
options:
  - label: "Dry run (preview only)"
    description: "Show what's stale without writing files"
  - label: "Regenerate all stale"
    description: "Refresh every stale feature"
  - label: "Filter by feature"
    description: "Only regenerate specific features"
```

## Execution

1. Call the MCP tool `author_maintain` with the chosen
   options.
2. For dry runs, show the stale list without acting.
3. For real runs, show the regenerated count and any
   failures.
4. If failures occurred, suggest investigating with
   `author-generate <feature>` to see the error in
   isolation.

## Output

Dry run:
```text
Stale features (3):
  - auth
  - cli
  - utils
```

Real run:
```text
Regenerated: 3
Failed: (none)
```
