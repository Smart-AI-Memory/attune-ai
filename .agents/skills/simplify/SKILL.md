---
name: simplify
description: Run code simplification on a target path
---
# simplify

Run the SimplifyCodeWorkflow on a target path to find and
reduce unnecessary complexity.

## Context (pre-computed)

```bash
git diff --name-only HEAD~1 2>/dev/null || echo "No recent commits"
```

## Instructions

Use `AskUserQuestion` to scope:

- Which path to simplify? (recently changed files,
  specific module, or full src/)
- Minimum complexity threshold? (default: 5)

Then run:

```bash
uv run attune workflow run simplify-code --path <target>
```

Present results as a table of hotspots with file, function,
complexity score, and suggested simplification.
