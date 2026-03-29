---
name: bug-predict
description: "Predict likely bug locations from code patterns and complexity. Triggers on: predict bugs, find bugs, risky code, code risk, what might break, likely bugs."
---
# Bug Prediction

Scan code for patterns that predict likely bug locations.

## Scoping

Before running, ask:

1. **Target path**: "Which files or directory should I
   scan?" Default to `src/` if not specified.
2. **Severity filter**: "Show all findings, or only HIGH
   severity?"

## Execution

Call the `bug_predict` MCP tool with the scoped path:

```
bug_predict(path="<user-specified path>")
```

Or via CLI:

```bash
uv run attune workflow run bug-predict --path <target>
```

## Output

Present results as a markdown table grouped by severity
(HIGH first):

| File | Line | Pattern | Severity |
|------|------|---------|----------|

Include clickable file links and note any false
positives (see scanner-patterns for known false
positives like `subprocess_exec` matching
`dangerous_eval`).

## Detected Patterns

| Pattern | Severity | Description |
|---------|----------|-------------|
| `dangerous_eval` | HIGH | Use of eval() or exec() |
| `broad_exception` | MEDIUM | Bare except: or except Exception: |
| `incomplete_code` | LOW | TODO/FIXME comments |
