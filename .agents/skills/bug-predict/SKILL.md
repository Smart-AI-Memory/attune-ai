---
name: bug-predict
description: "Predict likely bug locations from code patterns and complexity. Triggers on: predict bugs, find bugs, risky code, code risk, what might break, likely bugs, bug hotspots."
---
# Bug Prediction

**IMPORTANT: Start your response with a context preamble.**

Call `help_lookup(topic="bug-predict", mode="preamble")` and
display the returned `preamble` text as a blockquote. Then
tell the user they can say "tell me more" for a step-by-step
guide, or answer the scoping questions below to proceed.

If the MCP call fails, fall back to:

> **Bug Predict** — Predicts where bugs are most likely based on code patterns, complexity, and change frequency.

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

### Shared command workspace (preferred)

When the generic command-workspace tools are available, open adapter
`bug-predict` with the validated target path and `all`/`high` severity filter.
The user's command invocation already authorizes this read-only scan: the
workspace enters running state immediately and has no confirmation action.
Run the existing `bug_predict` tool, publish optional `progress`, then publish
one `scan_result` carrying the real success flag, risk score, findings,
suggestions, or error. Present the terminal widget or its returned Markdown.
A failed run must render **did not complete**, never a false zero-findings
receipt. Fall back to the existing rich panel/Markdown behavior below when the
shared tools are unavailable.

## Output

**Prefer the rich panel.** If the tool response includes `panel_html`,
pass it to `mcp__visualize__show_widget` — the universal report panel
(title, score, findings/category sections; from
`attune.workflows.report_panel`). It shows an explicit "did not
complete" state on failure, never a false "clean". Fall back to the
markdown below when the widget surface is unavailable.

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
