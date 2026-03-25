---
name: bug-predict
description: "Predict likely bug locations based on code patterns and complexity."
argument-hint: "<path or directory to scan>"
---

# Bug Prediction

Run `uv run attune workflow run bug-predict --path <target>`
to execute. Scope with AskUserQuestion first: target path
and severity threshold.

## Scoping

Before running, ask:

1. **Target path**: "Which files or directory should I scan?"
   - Default to `src/` if not specified
2. **Severity filter**: "Show all findings, or only HIGH
   severity?"

## Execution

```
uv run attune workflow run bug-predict --path <user-specified>
```

## Output

Present results as a markdown table:

| File | Line | Pattern | Severity |
|------|------|---------|----------|

Group by severity (HIGH first), include clickable file
links, and note any false positives.

ARGUMENTS: $ARGUMENTS
