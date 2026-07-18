---
name: deep-review
description: Multi-pass deep code review — security, quality, and test gaps
---
# deep-review

Multi-pass code review that runs security, quality, and
test gap analysis on a target. Uses subagents to keep
context clean.

## Context (pre-computed)

```bash
git diff --name-only main...HEAD 2>/dev/null || git diff --name-only HEAD~3 2>/dev/null
```

## Instructions

Use `AskUserQuestion` to scope:

- Which path or files to review?
- Focus: security, quality, test gaps, or all three?

Then run three passes using the Task tool with subagents:

### Pass 1: Security

```bash
uv run attune workflow run security-audit --path <target>
```

### Pass 2: Quality

```bash
uv run attune workflow run code-review --path <target>
```

### Pass 3: Test Gaps

Analyze which functions in the target lack test coverage
by cross-referencing source files with test files.

### Output

Consolidate findings into a single summary table:

| File | Issue | Severity | Category |
|------|-------|----------|----------|

Group by severity (high → medium → low). End with
actionable recommendations.
